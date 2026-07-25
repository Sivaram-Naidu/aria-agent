import os
from groq import Groq
from aria.core.state import ARIAState
from aria.core.persona import build_system_prompt
from aria.utils.helpers import extract_name, build_history, recent_ai_replies

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = os.getenv("ARIA_MODEL", "llama-3.3-70b-versatile")

# Emotion classification and summarization are cheap structured tasks —
# they don't need the full persona model. Defaults to MODEL so behavior
# is unchanged unless this env var is explicitly set (e.g. to a faster
# Groq model like "llama-3.1-8b-instant") to cut per-turn latency.
CLASSIFIER_MODEL = os.getenv("ARIA_CLASSIFIER_MODEL", MODEL)

# How many raw messages are always sent verbatim to the reply model
HISTORY_WINDOW = 8

# Only re-summarize once at least this many messages have aged out of
# the live window since the last summary — keeps the extra summarization
# call rare (roughly every 4 exchanges) instead of running every turn
SUMMARY_BATCH_SIZE = 8


# ─────────────────────────────────────────────
# NODE 1: Analyze Input
# Detects emotion + intent, advances turn_count, best-effort name capture
# ─────────────────────────────────────────────
def analyze_input(state: ARIAState) -> ARIAState:
    user_input = state["user_input"]

    response = client.chat.completions.create(
        model=CLASSIFIER_MODEL,
        messages=[
            {
                "role": "system",
                "content": """You are an emotion analyzer. Given a user message, respond ONLY in this exact format with no extra text:
EMOTION: <one of: HAPPY, SAD, ANGRY, ANXIOUS, EXCITED, NEUTRAL>
INTENT: <one short phrase describing what the user wants, max 8 words>

Example:
EMOTION: SAD
INTENT: wants comfort after a bad day"""
            },
            {"role": "user", "content": user_input}
        ],
        max_tokens=50,
        temperature=0
    )

    raw = response.choices[0].message.content.strip()

    # Parse the response
    emotion = "NEUTRAL"
    intent = "general conversation"

    for line in raw.splitlines():
        if line.startswith("EMOTION:"):
            detected = line.replace("EMOTION:", "").strip().upper()
            valid = {"HAPPY", "SAD", "ANGRY", "ANXIOUS", "EXCITED", "NEUTRAL"}
            emotion = detected if detected in valid else "NEUTRAL"
        elif line.startswith("INTENT:"):
            intent = line.replace("INTENT:", "").strip()

    # Determine mode for conditional routing
    support_emotions = {"SAD", "ANGRY", "ANXIOUS"}
    mode = "support" if emotion in support_emotions else "friend"

    # Best-effort name capture — only overwrites once we're still unsure
    user_name = state.get("user_name", "")
    if not user_name:
        detected_name = extract_name(user_input)
        if detected_name:
            user_name = detected_name

    return {
        **state,
        "emotion": emotion,
        "mode": mode,
        "intent": intent,
        "turn_count": state.get("turn_count", 0) + 1,
        "user_name": user_name,
    }


# ─────────────────────────────────────────────
# NODE 2: Build Context
# Folds messages that have aged out of the live history window into a
# rolling summary, so long conversations don't lose earlier context.
# ─────────────────────────────────────────────
def build_context(state: ARIAState) -> ARIAState:
    messages = state.get("messages", [])
    summary = state.get("conversation_summary", "")
    summarized_through = state.get("summarized_through", 0)

    aged_out = len(messages) - HISTORY_WINDOW
    new_to_summarize = aged_out - summarized_through

    if new_to_summarize >= SUMMARY_BATCH_SIZE:
        to_fold = messages[summarized_through:aged_out]
        try:
            transcript = "\n".join(
                f"{'User' if getattr(m, 'type', '') == 'human' else 'ARIA'}: {m.content}"
                for m in to_fold
            )
            prior = f"Previous summary: {summary}\n\n" if summary else ""
            summary_response = client.chat.completions.create(
                model=CLASSIFIER_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "Summarize the conversation excerpt in 2-3 concise "
                                   "sentences. Focus on facts worth remembering — names, "
                                   "preferences, ongoing topics, emotional throughlines. "
                                   "Merge with the previous summary if one is given."
                    },
                    {"role": "user", "content": f"{prior}{transcript}"}
                ],
                max_tokens=120,
                temperature=0.3
            )
            summary = summary_response.choices[0].message.content.strip()
            summarized_through = aged_out
        except Exception:
            # Summarization is a nice-to-have — never let it break the turn
            pass

    return {**state, "conversation_summary": summary, "summarized_through": summarized_through}


# ─────────────────────────────────────────────
# NODE 3A: Support Mode
# For SAD, ANGRY, ANXIOUS emotions
# ─────────────────────────────────────────────
def support_mode(state: ARIAState) -> ARIAState:
    emotion = state["emotion"]
    user_input = state["user_input"]
    messages = state.get("messages", [])

    tone_map = {
        "SAD": "Be very gentle, warm and validating. Acknowledge their pain without toxic positivity. Don't rush to fix things.",
        "ANGRY": "Be calm and non-defensive. Acknowledge their frustration fully. Don't argue or dismiss.",
        "ANXIOUS": "Be grounding and reassuring. Use a calm steady tone. Help them feel safe."
    }
    tone = tone_map.get(emotion, "Be empathetic and supportive.")

    system_prompt = build_system_prompt(
        user_name=state.get("user_name", ""),
        turn_count=state.get("turn_count", 1),
        recent_aria_replies=recent_ai_replies(messages),
        conversation_summary=state.get("conversation_summary", ""),
    )
    system_prompt += (
        f"\n\n## Current Mode: SUPPORT\nTone instruction: {tone}\n"
        f"User's detected emotion: {emotion}\nWhat they seem to want: {state.get('intent', '')}"
    )

    history = build_history(messages, HISTORY_WINDOW)

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            *history,
            {"role": "user", "content": user_input}
        ],
        max_tokens=300,
        temperature=0.7  # slightly lower — more careful responses
    )

    aria_response = response.choices[0].message.content.strip()
    return {**state, "aria_response": aria_response}


# ─────────────────────────────────────────────
# NODE 3B: Friend Mode
# For HAPPY, EXCITED, NEUTRAL emotions
# ─────────────────────────────────────────────
def friend_mode(state: ARIAState) -> ARIAState:
    emotion = state["emotion"]
    user_input = state["user_input"]
    messages = state.get("messages", [])

    tone_map = {
        "HAPPY": "Match their happiness! Be warm, fun and enthusiastic.",
        "EXCITED": "Be equally excited and energetic! Hype them up genuinely.",
        "NEUTRAL": "Be friendly, curious and engaging. Keep it light and real."
    }
    tone = tone_map.get(emotion, "Be friendly and natural.")

    system_prompt = build_system_prompt(
        user_name=state.get("user_name", ""),
        turn_count=state.get("turn_count", 1),
        recent_aria_replies=recent_ai_replies(messages),
        conversation_summary=state.get("conversation_summary", ""),
    )
    system_prompt += (
        f"\n\n## Current Mode: FRIEND\nTone instruction: {tone}\n"
        f"User's detected emotion: {emotion}\nWhat they seem to want: {state.get('intent', '')}"
    )

    history = build_history(messages, HISTORY_WINDOW)

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            *history,
            {"role": "user", "content": user_input}
        ],
        max_tokens=300,
        temperature=0.92  # higher — more playful and spontaneous
    )

    aria_response = response.choices[0].message.content.strip()
    return {**state, "aria_response": aria_response}


# ─────────────────────────────────────────────
# NODE 4: Format Response
# Final cleanup before output
# ─────────────────────────────────────────────
def format_response(state: ARIAState) -> ARIAState:
    response = state.get("aria_response", "")

    # Clean up any accidental artifacts
    response = response.strip()
    if response.startswith("ARIA:"):
        response = response[5:].strip()

    return {**state, "aria_response": response}


# ─────────────────────────────────────────────
# CONDITIONAL EDGE FUNCTION
# Routes to support_mode or friend_mode
# ─────────────────────────────────────────────
def route_by_emotion(state: ARIAState) -> str:
    mode = state.get("mode", "friend")
    return mode  # returns "support" or "friend"
