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
