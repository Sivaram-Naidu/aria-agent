import re

# ─────────────────────────────────────────────
# Lightweight, zero-latency name extraction.
# Best-effort heuristic — not a substitute for the model
# just asking naturally, but lets us stop re-asking once
# we're fairly confident we already know the name.
# ─────────────────────────────────────────────
_NAME_PATTERNS = [
    re.compile(r"\bmy name(?:'s| is) ([A-Za-z][A-Za-z'-]{1,20})", re.IGNORECASE),
    # Capitalized capture group is deliberate — it's what filters out
    # "i'm fine" / "i'm tired" etc. without needing a full IGNORECASE match.
    re.compile(r"\b[Ii]'?m ([A-Z][A-Za-z'-]{1,20})\b"),
    re.compile(r"\b[Ii] am ([A-Z][A-Za-z'-]{1,20})\b"),
    re.compile(r"\bcall me ([A-Za-z][A-Za-z'-]{1,20})\b", re.IGNORECASE),
]

# Words that commonly follow "I'm" / "I am" but are not names —
# without this filter, "I'm fine" would be parsed as a name "Fine".
_NOT_NAMES = {
    "fine", "good", "okay", "ok", "great", "sad", "happy", "tired",
    "not", "just", "still", "sorry", "here", "back", "done", "busy",
    "trying", "feeling", "kind", "sure", "afraid", "scared", "worried",
    "excited", "nervous", "stressed", "exhausted", "bored", "confused",
}


def extract_name(text: str) -> str | None:
    """Pulls a self-introduced name out of free text, if one is present."""
    for pattern in _NAME_PATTERNS:
        match = pattern.search(text)
        if match:
            candidate = match.group(1).strip().rstrip(".,!?'\"")
            if candidate.lower() not in _NOT_NAMES:
                return candidate.capitalize()
    return None


# ─────────────────────────────────────────────
# Conversation history helpers shared by support_mode / friend_mode
# ─────────────────────────────────────────────
def build_history(messages: list, window: int) -> list[dict]:
    """Converts the last `window` LangChain messages into Groq chat format."""
    history = []
    for msg in messages[-window:]:
        if hasattr(msg, "type"):
            role = "user" if msg.type == "human" else "assistant"
            history.append({"role": role, "content": msg.content})
    return history


def recent_ai_replies(messages: list, count: int = 3) -> list[str]:
    """Returns ARIA's last `count` replies, used to steer her away from
    repeating her own phrasing/structure turn over turn."""
    replies = [msg.content for msg in messages if getattr(msg, "type", "") == "ai"]
    return replies[-count:]
