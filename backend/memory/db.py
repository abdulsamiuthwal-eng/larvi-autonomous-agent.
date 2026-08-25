"""
Larvi — SQLite Persistent Database
Stores conversation history, multi-chat sessions, and working memory
permanently across page reloads and browser sessions.
"""
import sqlite3
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).resolve().parent.parent / "larvi.db"


def get_db_connection():
    """Create a SQLite database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database tables if they do not exist."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                working_memory_json TEXT DEFAULT '{}'
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                agent_used TEXT DEFAULT 'Larvi',
                intent TEXT DEFAULT '',
                tool_calls_json TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
            )
        """)
        conn.commit()


def save_or_update_session(session_id: str, title: Optional[str] = None, working_memory: Optional[dict] = None):
    """Create or update a conversation session record."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, working_memory_json FROM sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()

        now = datetime.utcnow().isoformat()
        if not row:
            session_title = title or "New Conversation"
            wm_json = json.dumps(working_memory or {})
            cursor.execute(
                "INSERT INTO sessions (id, title, created_at, updated_at, working_memory_json) VALUES (?, ?, ?, ?, ?)",
                (session_id, session_title, now, now, wm_json)
            )
        else:
            new_title = title if title is not None else row["title"]
            wm_json = json.dumps(working_memory) if working_memory is not None else row["working_memory_json"]
            cursor.execute(
                "UPDATE sessions SET title = ?, updated_at = ?, working_memory_json = ? WHERE id = ?",
                (new_title, now, wm_json, session_id)
            )
        conn.commit()


def save_message(session_id: str, role: str, content: str, agent_used: str = "Larvi", intent: str = "", tool_calls: Optional[list] = None):
    """Store a message in the conversation history."""
    init_db()
    # If first user message, update title
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) as count FROM messages WHERE session_id = ?", (session_id,))
        count = cursor.fetchone()["count"]

        save_or_update_session(session_id)
        if count == 0 and role == "user":
            # Generate clean short title from first prompt
            clean_title = content.strip().replace("\n", " ")
            if len(clean_title) > 36:
                clean_title = clean_title[:33] + "..."
            cursor.execute("UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?", (clean_title, datetime.utcnow().isoformat(), session_id))

        tc_json = json.dumps(tool_calls or [])
        cursor.execute(
            "INSERT INTO messages (session_id, role, content, agent_used, intent, tool_calls_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (session_id, role, content, agent_used, intent, tc_json, datetime.utcnow().isoformat())
        )
        conn.commit()


def get_all_sessions() -> list[dict]:
    """Retrieve all chat sessions ordered by latest update."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, created_at, updated_at, working_memory_json FROM sessions ORDER BY updated_at DESC")
        rows = cursor.fetchall()
        result = []
        for r in rows:
            result.append({
                "id": r["id"],
                "title": r["title"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
                "working_memory": json.loads(r["working_memory_json"] or "{}"),
            })
        return result


def get_session_messages(session_id: str) -> list[dict]:
    """Retrieve all messages for a given session."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, role, content, agent_used, intent, tool_calls_json, created_at FROM messages WHERE session_id = ? ORDER BY id ASC", (session_id,))
        rows = cursor.fetchall()
        messages = []
        for r in rows:
            messages.append({
                "id": r["id"],
                "role": r["role"],
                "content": r["content"],
                "agent_used": r["agent_used"],
                "intent": r["intent"],
                "tool_calls": json.loads(r["tool_calls_json"] or "[]"),
                "created_at": r["created_at"],
            })
        return messages


def delete_session(session_id: str) -> bool:
    """Delete a conversation session and all its messages."""
    init_db()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()
        return cursor.rowcount > 0
