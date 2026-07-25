from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class ARIAState(TypedDict):
    # Full conversation history (LangGraph manages this with add_messages)
    messages: Annotated[list, add_messages]
    
    # Detected emotion from current user input
    emotion: str
    
    # Emotional category for conditional routing
    # "support" → SAD, ANGRY, ANXIOUS
    # "friend"  → HAPPY, EXCITED, NEUTRAL
    mode: str
    
    # Raw user input (stored separately for emotion analysis)
    user_input: str

    # ARIA's final response
    aria_response: str

    # Short phrase describing what the user wants (from analyze_input)
    intent: str

    # How many turns into this conversation we are — drives onboarding
    # (asking name / hobbies) deterministically instead of the model
    # guessing from a truncated message window
    turn_count: int

    # User's name, once known — best-effort extracted in analyze_input
    user_name: str

    # Rolling summary of everything older than the live history window,
    # so long conversations don't lose context once messages get trimmed
    conversation_summary: str

    # How many messages are already folded into conversation_summary —
    # lets build_context only re-summarize newly-aged-out messages
    summarized_through: int
