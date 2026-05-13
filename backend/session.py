import uuid
from typing import Dict
from aria.core.agent import build_aria_graph

# ─────────────────────────────────────────────
# In-memory session store
# Each user gets their own LangGraph thread
# ─────────────────────────────────────────────

# Holds one compiled graph per server (shared, stateless)
_aria_graph = None

def get_graph():
    global _aria_graph
    if _aria_graph is None:
        _aria_graph = build_aria_graph()
    return _aria_graph


# Maps session_id → LangGraph thread config
_sessions: Dict[str, dict] = {}


def create_session() -> str:
    """
    Creates a new unique session for a user.
    Returns the session_id.
    """
    session_id = str(uuid.uuid4())
    _sessions[session_id] = {
        "config": {
            "configurable": {
                "thread_id": session_id
            }
        }
    }
    return session_id


def get_session_config(session_id: str) -> dict | None:
    """
    Returns the LangGraph config for a session.
    Returns None if session doesn't exist.
    """
    session = _sessions.get(session_id)
    if session:
        return session["config"]
    return None


def session_exists(session_id: str) -> bool:
    return session_id in _sessions


def delete_session(session_id: str):
    """Clean up a session when user leaves."""
    if session_id in _sessions:
        del _sessions[session_id]


def get_active_sessions() -> int:
    return len(_sessions)
