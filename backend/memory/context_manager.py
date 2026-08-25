"""
Larvi — Context & Memory Manager
Manages per-session conversation history and working memory.
Enables follow-up question resolution (e.g., "move IT to 5 PM").
"""
import time
from typing import Any, Optional
from dataclasses import dataclass, field
from contextvars import ContextVar

# Thread-safe & async-safe ContextVar to track active user session across tool executions
current_session_id: ContextVar[Optional[str]] = ContextVar("current_session_id", default=None)


@dataclass
class WorkingMemory:
    """
    Stores extracted entities from the current conversation context.
    This is Larvi's short-term memory for resolving follow-up references.
    """
    # People mentioned
    active_person: Optional[str] = None

    # Email context
    last_email_id: Optional[str] = None
    last_email_subject: Optional[str] = None
    last_email_from: Optional[str] = None

    # Calendar context
    last_event_id: Optional[str] = None
    last_event_title: Optional[str] = None
    last_event_date: Optional[str] = None
    last_event_start: Optional[str] = None
    last_event_end: Optional[str] = None

    # Pending confirmation
    pending_action: Optional[dict] = None  # Action awaiting user confirmation

    def update_from_email(self, email: dict) -> None:
        """Update working memory after an email is read/found."""
        self.last_email_id = email.get("id")
        self.last_email_subject = email.get("subject")
        self.last_email_from = email.get("from")

    def update_from_event(self, event: dict) -> None:
        """Update working memory after a calendar event is found/created."""
        self.last_event_id = event.get("id")
        self.last_event_title = event.get("title")
        self.last_event_date = event.get("start", "")[:10] if event.get("start") else None
        self.last_event_start = event.get("start", "")[11:16] if event.get("start") else None
        self.last_event_end = event.get("end", "")[11:16] if event.get("end") else None

    def to_dict(self) -> dict:
        """Serialize working memory to dict for API responses."""
        return {k: v for k, v in self.__dict__.items() if v is not None}

    def get_context_summary(self) -> str:
        """Generate a text summary of current working memory for LLM context injection."""
        parts = []
        if self.active_person:
            parts.append(f"Active person in conversation: {self.active_person}")
        if self.last_email_subject:
            parts.append(
                f"Last email referenced: '{self.last_email_subject}' "
                f"from {self.last_email_from} (ID: {self.last_email_id})"
            )
        if self.last_event_title:
            parts.append(
                f"Last calendar event referenced: '{self.last_event_title}' "
                f"on {self.last_event_date} at {self.last_event_start} "
                f"(ID: {self.last_event_id})"
            )
        if self.pending_action:
            parts.append(f"Pending confirmation for action: {self.pending_action.get('type', 'unknown')}")
        if not parts:
            return ""
        return "WORKING MEMORY (use this to resolve references like 'it', 'that meeting', 'the email'):\n" + "\n".join(parts)


@dataclass
class Session:
    """Represents a single user conversation session."""
    session_id: str
    messages: list[dict] = field(default_factory=list)
    working_memory: WorkingMemory = field(default_factory=WorkingMemory)
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)

    def add_message(self, role: str, content: str) -> None:
        """Append a message to conversation history."""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": time.time(),
        })
        self.last_active = time.time()

    def get_history_for_llm(self, max_messages: int = 20) -> list[dict]:
        """Return recent messages formatted for LangChain message history."""
        recent = self.messages[-max_messages:]
        return [{"role": m["role"], "content": m["content"]} for m in recent]


class SessionManager:
    """
    In-memory session store for all active conversations.
    Handles session creation, retrieval, and cleanup.
    """

    def __init__(self, session_ttl_seconds: int = 3600):
        self._sessions: dict[str, Session] = {}
        self.session_ttl = session_ttl_seconds

    def get_or_create(self, session_id: str) -> Session:
        """Get existing session or create a new one."""
        self._cleanup_expired()
        if session_id not in self._sessions:
            self._sessions[session_id] = Session(session_id=session_id)
        return self._sessions[session_id]

    def get(self, session_id: str) -> Optional[Session]:
        """Get an existing session. Returns None if not found."""
        return self._sessions.get(session_id)

    def delete(self, session_id: str) -> None:
        """Remove a session."""
        self._sessions.pop(session_id, None)

    def _cleanup_expired(self) -> None:
        """Remove sessions that have been inactive past TTL."""
        now = time.time()
        expired = [
            sid for sid, s in self._sessions.items()
            if now - s.last_active > self.session_ttl
        ]
        for sid in expired:
            del self._sessions[sid]

    def get_all_sessions(self) -> dict:
        """Debug: return info about all active sessions."""
        return {
            sid: {
                "message_count": len(s.messages),
                "last_active": s.last_active,
                "working_memory": s.working_memory.to_dict(),
            }
            for sid, s in self._sessions.items()
        }


# ── Singleton Instance ────────────────────────────────────────────────────────
# Import this in agents and main.py
session_manager = SessionManager()
