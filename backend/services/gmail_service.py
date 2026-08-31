"""
Larvi — Gmail Service
Authenticated Gmail API client wrapper.
All tools in email_tools.py call methods from this service.
"""
import base64
import email as email_lib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from auth.google_oauth import get_or_create_credentials
from memory.context_manager import current_session_id


def _get_gmail_client(session_id: Optional[str] = None):
    """Build and return an authenticated Gmail API client for the active session."""
    sid = session_id or current_session_id.get()
    creds = get_or_create_credentials(sid)
    if creds is None:
        raise PermissionError(
            "Not authenticated with Google. Please connect your Google account in Larvi first."
        )
    return build("gmail", "v1", credentials=creds)


def search_emails_raw(query: str, max_results: int = 10) -> list[dict]:
    """
    Search Gmail with a query string (supports all Gmail operators).
    Returns list of message metadata dicts.
    """
    service = _get_gmail_client()
    try:
        result = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_results)
            .execute()
        )
        messages = result.get("messages", [])
        return messages
    except HttpError as e:
        raise RuntimeError(f"Gmail API search error: {e}")


def get_email_detail(message_id: str) -> dict:
    """
    Fetch full email content by message ID.
    Returns structured dict with headers, body, and metadata.
    """
    service = _get_gmail_client()
    try:
        msg = (
            service.users()
            .messages()
            .get(userId="me", id=message_id, format="full")
            .execute()
        )
        return _parse_message(msg)
    except HttpError as e:
        raise RuntimeError(f"Gmail API read error: {e}")


from concurrent.futures import ThreadPoolExecutor


def _fetch_message_summary(service, msg_id: str) -> Optional[dict]:
    """Lightweight metadata fetch for high-speed inbox list rendering."""
    try:
        msg = (
            service.users()
            .messages()
            .get(
                userId="me",
                id=msg_id,
                format="metadata",
                metadataHeaders=["Subject", "From", "To", "Date"],
            )
            .execute()
        )
        payload = msg.get("payload", {})
        headers = {h["name"]: h["value"] for h in payload.get("headers", [])}
        return {
            "id": msg.get("id"),
            "thread_id": msg.get("threadId"),
            "subject": headers.get("Subject", "(No Subject)"),
            "from": headers.get("From", "Unknown"),
            "to": headers.get("To", ""),
            "date": headers.get("Date", ""),
            "snippet": msg.get("snippet", ""),
            "body": msg.get("snippet", ""),
        }
    except Exception:
        return None


def list_recent_emails(count: int = 10) -> list[dict]:
    """Fetch the N most recent emails from inbox with high-speed parallel metadata retrieval."""
    service = _get_gmail_client()
    try:
        result = (
            service.users()
            .messages()
            .list(userId="me", labelIds=["INBOX"], maxResults=count)
            .execute()
        )
        messages = result.get("messages", [])
        if not messages:
            return []

        emails = []
        with ThreadPoolExecutor(max_workers=min(len(messages), 8)) as executor:
            futures = [executor.submit(_fetch_message_summary, service, m["id"]) for m in messages]
            for f in futures:
                res = f.result()
                if res:
                    emails.append(res)
        return emails
    except HttpError as e:
        raise RuntimeError(f"Gmail API list error: {e}")


def create_draft_raw(to: str, subject: str, body: str, thread_id: Optional[str] = None) -> dict:
    """Create a Gmail draft and return draft metadata."""
    service = _get_gmail_client()
    message = _build_message(to=to, subject=subject, body=body)
    draft_body = {"message": {"raw": message}}
    if thread_id:
        draft_body["message"]["threadId"] = thread_id
    try:
        draft = (
            service.users().drafts().create(userId="me", body=draft_body).execute()
        )
        return {"draft_id": draft["id"], "status": "draft_created", "to": to, "subject": subject}
    except HttpError as e:
        raise RuntimeError(f"Gmail API draft error: {e}")


def send_email_raw(to: str, subject: str, body: str) -> dict:
    """Send an email via Gmail API. Returns send confirmation."""
    service = _get_gmail_client()
    raw_message = _build_message(to=to, subject=subject, body=body)
    try:
        sent = (
            service.users()
            .messages()
            .send(userId="me", body={"raw": raw_message})
            .execute()
        )
        return {"message_id": sent["id"], "status": "sent", "to": to, "subject": subject}
    except HttpError as e:
        raise RuntimeError(f"Gmail API send error: {e}")


def reply_to_email_raw(message_id: str, body: str) -> dict:
    """Reply to an existing email thread."""
    service = _get_gmail_client()
    # Get the original message to extract thread ID and headers
    original = (
        service.users()
        .messages()
        .get(userId="me", id=message_id, format="metadata",
             metadataHeaders=["Subject", "From", "To", "Message-ID"])
        .execute()
    )
    headers = {h["name"]: h["value"] for h in original.get("payload", {}).get("headers", [])}
    thread_id = original.get("threadId")
    to = headers.get("From", "")
    subject = headers.get("Subject", "")
    if not subject.startswith("Re:"):
        subject = f"Re: {subject}"

    raw_message = _build_message(to=to, subject=subject, body=body, thread_id=thread_id)
    try:
        sent = (
            service.users()
            .messages()
            .send(userId="me", body={"raw": raw_message, "threadId": thread_id})
            .execute()
        )
        return {"message_id": sent["id"], "status": "reply_sent", "to": to, "subject": subject}
    except HttpError as e:
        raise RuntimeError(f"Gmail API reply error: {e}")


# ── Private Helpers ────────────────────────────────────────────────────────────

def _build_message(to: str, subject: str, body: str, thread_id: Optional[str] = None) -> str:
    """Build a base64-encoded email message."""
    msg = MIMEMultipart()
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    return raw


def _parse_message(msg: dict) -> dict:
    """Parse Gmail API message object into clean structured dict."""
    payload = msg.get("payload", {})
    headers = {h["name"]: h["value"] for h in payload.get("headers", [])}

    body_text = ""
    if "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data", "")
                if data:
                    body_text = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
                    break
    else:
        data = payload.get("body", {}).get("data", "")
        if data:
            body_text = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

    return {
        "id": msg.get("id"),
        "thread_id": msg.get("threadId"),
        "from": headers.get("From", "Unknown"),
        "to": headers.get("To", ""),
        "subject": headers.get("Subject", "(No Subject)"),
        "date": headers.get("Date", ""),
        "snippet": msg.get("snippet", ""),
        "body": body_text[:3000],  # Limit body for LLM context
        "labels": msg.get("labelIds", []),
    }
