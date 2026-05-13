import os
from groq import Groq
from aria.core.state import ARIAState
from aria.core.persona import ARIA_SYSTEM_PROMPT

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = os.getenv("ARIA_MODEL", "llama-3.3-70b-versatile")

# ─────────────────────────────────────────────
# NODE 1: Analyze Input
# Merged call — detects emotion + intent together
# ─────────────────────────────────────────────
def analyze_input(state: ARIAState) -> ARIAState:
    user_input = state["user_input"]
    
    response = client.chat.completions.create(
        model=MODEL,
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
    
    return {
        **state,
        "emotion": emotion,
        "mode": mode,
        "intent": intent  
    }


# ─────────────────────────────────────────────
# NODE 2: Build Context
# Prepares conversation history for the LLM
# ─────────────────────────────────────────────
def build_context(state: ARIAState) -> ARIAState:
    # LangGraph's MemorySaver already handles messages
    # This node is where we'd add extra context in future phases
    # For now it just passes state through cleanly
    return state


# ─────────────────────────────────────────────
# NODE 3A: Support Mode
# For SAD, ANGRY, ANXIOUS emotions
# ─────────────────────────────────────────────
def support_mode(state: ARIAState) -> ARIAState:
    emotion = state["emotion"]
    user_input = state["user_input"]
    messages = state.get("messages", [])

    # Build tone instruction based on specific emotion
    tone_map = {
        "SAD": "Be very gentle, warm and validating. Acknowledge their pain without toxic positivity. Don't rush to fix things.",
        "ANGRY": "Be calm and non-defensive. Acknowledge their frustration fully. Don't argue or dismiss.",
        "ANXIOUS": "Be grounding and reassuring. Use a calm steady tone. Help them feel safe."
    }
    tone = tone_map.get(emotion, "Be empathetic and supportive.")

    # Build message history for context
    history = []
    for msg in messages[-6:]:  # last 3 exchanges
        if hasattr(msg, 'type'):
            role = "user" if msg.type == "human" else "assistant"
            history.append({"role": role, "content": msg.content})

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": f"{ARIA_SYSTEM_PROMPT}\n\n## Current Mode: SUPPORT\nTone instruction: {tone}\nUser's detected emotion: {emotion}"
            },
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

    history = []
    for msg in messages[-6:]:
        if hasattr(msg, 'type'):
            role = "user" if msg.type == "human" else "assistant"
            history.append({"role": role, "content": msg.content})

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": f"{ARIA_SYSTEM_PROMPT}\n\n## Current Mode: FRIEND\nTone instruction: {tone}\nUser's detected emotion: {emotion}"
            },
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
