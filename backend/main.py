import os
import sys

# ── Make sure aria/ package is importable from backend/ ──
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

load_dotenv()

from backend.session import (
    create_session,
    get_session_config,
    session_exists,
    delete_session,
    get_active_sessions,
    get_graph
)

# ─────────────────────────────────────────────
# FastAPI app
# ─────────────────────────────────────────────
app = FastAPI(
    title="ARIA Backend",
    description="Emotion-aware AI companion powered by LangGraph + Groq",
    version="1.0.0"
)

# ── CORS — allows browser to talk to this server ──
# In production replace "*" with your Netlify URL
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000",
                   "https://aria-talks.netlify.app"
                   ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# Request / Response Models
# ─────────────────────────────────────────────
class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    response: str
    emotion: str
    mode: str
    session_id: str


class SessionResponse(BaseModel):
    session_id: str
    message: str


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@app.get("/health")
def health_check():
    """
    Render uses this to check if server is alive.
    Also useful to wake the server up before first chat.
    """
    return {
        "status": "alive",
        "active_sessions": get_active_sessions()
    }


@app.post("/session/new", response_model=SessionResponse)
def new_session():
    """
    Called when a new user opens the browser.
    Creates a fresh LangGraph memory thread for them.
    """
    session_id = create_session()
    return SessionResponse(
        session_id=session_id,
        message="Session created. ARIA is ready."
    )


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Main chat endpoint.
    Receives user message + session_id,
    runs it through ARIA's LangGraph agent,
    returns ARIA's response + emotion + mode.
    """

    # Validate session
    if not session_exists(request.session_id):
        raise HTTPException(
            status_code=404,
            detail="Session not found. Please refresh and start a new session."
        )

    if not request.message.strip():
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty."
        )

    # Get this user's LangGraph config
    config = get_session_config(request.session_id)
    aria   = get_graph()

    try:
        result = aria.invoke(
            {
                "user_input": request.message,
                "messages": [HumanMessage(content=request.message)],
                "emotion": "NEUTRAL",
                "mode": "friend",
                "aria_response": ""
            },
            config=config
        )

        return ChatResponse(
            response=result.get("aria_response", ""),
            emotion=result.get("emotion", "NEUTRAL"),
            mode=result.get("mode", "friend"),
            session_id=request.session_id
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"ARIA encountered an error: {str(e)}"
        )


@app.delete("/session/{session_id}")
def end_session(session_id: str):
    """
    Called when user closes the browser tab.
    Cleans up their session from memory.
    """
    if not session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found.")
    delete_session(session_id)
    return {"message": "Session ended. Goodbye!"}
