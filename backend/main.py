"""
Larvi — FastAPI Application Server (Multi-User & Session-Aware)
Main entry point for the Larvi backend API.
Handles chat, multi-user authentication, and health endpoints.
"""
import sys
import os
from pathlib import Path

# Ensure backend directory is in Python path for Vercel / serverless runtime
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import uuid
import json
import asyncio
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel

from config import settings
from agents.master_agent import run_master_agent
from memory.context_manager import session_manager, current_session_id
from memory.db import (
    init_db,
    save_or_update_session,
    save_message,
    get_all_sessions,
    get_session_messages,
    delete_session,
    clear_all_db_data,
    get_db_stats,
)
from auth.google_oauth import (
    run_oauth_flow,
    get_auth_status,
    is_authenticated,
    get_or_create_credentials,
    get_authorization_url,
    exchange_code_for_credentials,
)
from services.gmail_service import list_recent_emails
from services.gcal_service import get_upcoming_events

# Initialize SQLite database
init_db()

# ── App Init ──────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Larvi — Autonomous Email & Calendar AI Agent",
    description="Multi-agent AI system for Gmail and Google Calendar management.",
    version="1.0.0",
    docs_url="/docs",
)

# Validate config on startup (prints warnings if keys missing)
settings.validate()

# CORS — allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "https://larvi-autonomous-agent.vercel.app",
        "https://*.vercel.app",
        "null",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response Models ─────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    response: str
    agent_used: str
    intent: str
    workflow_steps: list
    tool_calls: list
    requires_confirmation: bool
    working_memory: dict


class ConfirmRequest(BaseModel):
    session_id: str
    confirmed: bool
    action_data: Optional[dict] = None


# ── Health Check ──────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check(session_id: Optional[str] = None):
    """System health check endpoint."""
    auth_status = get_auth_status(session_id)
    return {
        "status": "ok",
        "service": "Larvi AI Agent",
        "version": "1.0.0",
        "gemini_configured": bool(
            settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "your_gemini_api_key_here"
        ),
        "google_auth": auth_status,
    }


# ── Multi-User Authentication Endpoints ───────────────────────────────────────

@app.get("/auth/status")
async def auth_status(session_id: Optional[str] = None):
    """Check Google OAuth connection status for a specific user session."""
    return get_auth_status(session_id)


@app.get("/auth/login")
async def auth_login(session_id: Optional[str] = None, request: Request = None):
    """
    Start Web OAuth flow for this session.
    Redirects the user's browser directly to the Google consent screen.
    """
    sid = session_id or str(uuid.uuid4())
    # Use fixed redirect URI from env var if set (production/Vercel),
    # otherwise derive from request (local dev)
    if settings.GOOGLE_REDIRECT_URI and "localhost" not in settings.GOOGLE_REDIRECT_URI:
        redirect_uri = settings.GOOGLE_REDIRECT_URI
    else:
        base_url = str(request.base_url).rstrip("/")
        redirect_uri = f"{base_url}/auth/callback"

    try:
        auth_url, _ = get_authorization_url(session_id=sid, redirect_uri=redirect_uri)
        return RedirectResponse(url=auth_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate auth URL: {str(e)}")


@app.get("/auth/callback")
async def auth_callback(code: str, state: Optional[str] = None, request: Request = None):
    """
    Google OAuth redirect handler.
    Exchanges auth code for tokens and binds them to the user session (state).
    Redirects back to frontend with auth=success.
    """
    session_id = state or str(uuid.uuid4())
    # Must use the SAME redirect_uri as used during authorization
    if settings.GOOGLE_REDIRECT_URI and "localhost" not in settings.GOOGLE_REDIRECT_URI:
        redirect_uri = settings.GOOGLE_REDIRECT_URI
    else:
        base_url = str(request.base_url).rstrip("/")
        redirect_uri = f"{base_url}/auth/callback"

    try:
        exchange_code_for_credentials(code=code, redirect_uri=redirect_uri, session_id=session_id)
        # Redirect back to frontend
        frontend_url = f"{settings.FRONTEND_URL}/?auth=success&session_id={session_id}"
        return RedirectResponse(url=frontend_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAuth callback failed: {str(e)}")


@app.get("/auth/init")
async def auth_init(request: Request):
    """Fallback: Redirects to /auth/login for web OAuth."""
    base_url = str(request.base_url).rstrip("/")
    return RedirectResponse(url=f"{base_url}/auth/login")


# ── Main Chat Endpoint ────────────────────────────────────────────────────────

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main Larvi chat endpoint.
    Receives a natural language message and returns the agent's response.
    """
    # Validate API key
    if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "your_gemini_api_key_here":
        raise HTTPException(
            status_code=503,
            detail="Gemini API key not configured. Add GEMINI_API_KEY to your .env file."
        )

    # Get or create session
    session_id = request.session_id or str(uuid.uuid4())
    session = session_manager.get_or_create(session_id)

    # Store user message in history & SQLite DB
    session.add_message("user", request.message)
    save_message(session_id, "user", request.message)

    # Bind session_id to ContextVar for downstream tools & services
    token = current_session_id.set(session_id)

    try:
        result = await asyncio.to_thread(
            run_master_agent,
            user_input=request.message,
            session=session,
        )
    finally:
        current_session_id.reset(token)

    # Store agent response in history & SQLite DB
    session.add_message("assistant", result["response"])
    save_message(
        session_id=session_id,
        role="assistant",
        content=result["response"],
        agent_used=result.get("agent_used", "Larvi"),
        intent=result.get("intent", ""),
        tool_calls=result.get("tool_calls", []),
    )
    save_or_update_session(session_id, working_memory=result.get("working_memory", {}))

    return ChatResponse(
        session_id=session_id,
        response=result["response"],
        agent_used=result.get("agent_used", "Larvi"),
        intent=result.get("intent", "unknown"),
        workflow_steps=result.get("workflow_steps", []),
        tool_calls=result.get("tool_calls", []),
        requires_confirmation=result.get("requires_confirmation", False),
        working_memory=result.get("working_memory", {}),
    )


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Streaming version of chat endpoint using Server-Sent Events.
    Sends workflow step updates as they happen, then the final response.
    """
    session_id = request.session_id or str(uuid.uuid4())
    session = session_manager.get_or_create(session_id)
    session.add_message("user", request.message)
    save_message(session_id, "user", request.message)

    async def event_generator():
        # Send typing indicator
        yield f"data: {json.dumps({'type': 'typing', 'session_id': session_id})}\n\n"
        await asyncio.sleep(0.1)

        # Bind session_id to ContextVar for downstream tools & services
        token = current_session_id.set(session_id)

        try:
            result = await asyncio.to_thread(
                run_master_agent,
                user_input=request.message,
                session=session,
            )
        finally:
            current_session_id.reset(token)

        session.add_message("assistant", result["response"])
        save_message(
            session_id=session_id,
            role="assistant",
            content=result["response"],
            agent_used=result.get("agent_used", "Larvi"),
            intent=result.get("intent", ""),
            tool_calls=result.get("tool_calls", []),
        )
        save_or_update_session(session_id, working_memory=result.get("working_memory", {}))

        # Stream workflow steps
        for step in result.get("workflow_steps", []):
            yield f"data: {json.dumps({'type': 'workflow_step', 'step': step})}\n\n"
            await asyncio.sleep(0.05)

        # Stream tool calls
        for tc in result.get("tool_calls", []):
            yield f"data: {json.dumps({'type': 'tool_call', 'tool_call': tc})}\n\n"
            await asyncio.sleep(0.04)

        # Stream response tokens (smooth word-by-word streaming)
        full_text = result["response"]
        words = full_text.split(" ")
        for i in range(0, len(words), 2):
            chunk = " ".join(words[i : i + 2])
            if i + 2 < len(words):
                chunk += " "
            yield f"data: {json.dumps({'type': 'token', 'token': chunk})}\n\n"
            await asyncio.sleep(0.018)

        # Final response
        final_payload = {
            "type": "final",
            "session_id": session_id,
            "response": result["response"],
            "agent_used": result.get("agent_used", "Larvi"),
            "intent": result.get("intent", ""),
            "requires_confirmation": result.get("requires_confirmation", False),
            "working_memory": result.get("working_memory", {}),
        }
        yield f"data: {json.dumps(final_payload)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── Session & Chat History Management ─────────────────────────────────────────

@app.get("/sessions")
async def list_sessions():
    """List all saved chat conversations for sidebar history."""
    return get_all_sessions()


@app.get("/sessions/{session_id}")
async def get_session_history(session_id: str):
    """Retrieve full conversation message history for a specific session."""
    session = session_manager.get_or_create(session_id)
    messages = get_session_messages(session_id)
    return {
        "session_id": session_id,
        "messages": messages,
        "working_memory": session.working_memory.to_dict(),
    }


@app.post("/sessions")
async def create_new_session():
    """Create a new chat conversation session."""
    new_id = str(uuid.uuid4())
    save_or_update_session(new_id, title="New Conversation")
    session_manager.get_or_create(new_id)
    return {"session_id": new_id, "title": "New Conversation"}


@app.delete("/sessions/{session_id}")
async def remove_session(session_id: str):
    """Delete a conversation session and all its messages."""
    delete_session(session_id)
    session_manager.delete(session_id)
    return {"status": "deleted", "session_id": session_id}


@app.get("/session/{session_id}/memory")
async def get_session_memory(session_id: str):
    """Get the current working memory state for a session."""
    session = session_manager.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    return {
        "session_id": session_id,
        "message_count": len(session.messages),
        "working_memory": session.working_memory.to_dict(),
        "history": session.get_history_for_llm(max_messages=10),
    }


@app.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """Clear a conversation session and its memory."""
    delete_session(session_id)
    session_manager.delete(session_id)
    return {"status": "cleared", "session_id": session_id}


@app.get("/emails/list")
async def get_recent_emails_endpoint(session_id: Optional[str] = None):
    """Retrieve recent emails from Gmail for the inbox dashboard."""
    try:
        emails = list_recent_emails(max_results=10, session_id=session_id)
        return {"status": "success", "count": len(emails), "emails": emails}
    except Exception as e:
        return {"status": "error", "message": str(e), "emails": []}


@app.get("/calendar/list")
async def get_recent_events_endpoint(session_id: Optional[str] = None):
    """Retrieve upcoming calendar events for the schedule dashboard."""
    try:
        events = get_upcoming_events(days_ahead=7, session_id=session_id)
        return {"status": "success", "count": len(events), "events": events}
    except Exception as e:
        return {"status": "error", "message": str(e), "events": []}


@app.get("/settings/stats")
async def get_settings_stats(session_id: Optional[str] = None):
    """Get system stats, database metrics, and authentication state."""
    db_stats = get_db_stats()
    auth_status = get_auth_status(session_id)
    return {
        "status": "ok",
        "service": "Larvi AI Agent",
        "version": "1.0.0",
        "ai_model": "Gemini 2.5/3.5 Fallback Cascade",
        "db_stats": db_stats,
        "auth": auth_status,
    }


@app.post("/settings/clear-all")
async def clear_all_data_endpoint():
    """Clear all chat sessions, messages, and working memory from database."""
    clear_all_db_data()
    session_manager.sessions.clear()
    return {"status": "cleared", "message": "All conversations and memories deleted."}


@app.post("/auth/logout")
async def logout_endpoint(session_id: Optional[str] = None):
    """Disconnect Google account and clear session token."""
    from auth.google_oauth import _session_credentials, _session_userinfo, _get_token_path
    if session_id:
        _session_credentials.pop(session_id, None)
        _session_userinfo.pop(session_id, None)
        token_path = _get_token_path(session_id)
        if token_path.exists():
            try:
                token_path.unlink()
            except Exception:
                pass
    return {"status": "logged_out", "message": "Google account disconnected successfully."}


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG,
        log_level="info",
    )
