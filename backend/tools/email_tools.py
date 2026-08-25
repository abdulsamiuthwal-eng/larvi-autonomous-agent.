"""
Larvi — Email Tools
LangChain-compatible tool definitions that wrap Gmail service calls.
The Email Agent and Master Agent use these tools to perform real actions.
"""
import json
from langchain_core.tools import tool

from services.gmail_service import (
    search_emails_raw,
    get_email_detail,
    list_recent_emails,
    create_draft_raw,
    send_email_raw,
    reply_to_email_raw,
)


@tool
def search_emails(query: str, max_results: int = 10) -> str:
    """
    Search emails in Gmail using any search query.
    Supports Gmail operators like 'from:', 'subject:', 'has:attachment'.
    Examples: 'from:ahmed@example.com', 'subject:meeting', 'project update'.
    Returns a JSON string with matching email summaries.
    """
    try:
        raw_messages = search_emails_raw(query=query, max_results=max_results)
        if not raw_messages:
            return json.dumps({"status": "no_results", "count": 0, "emails": [],
                               "message": f"No emails found for query: '{query}'"})

        emails = []
        for msg_ref in raw_messages[:max_results]:
            try:
                detail = get_email_detail(msg_ref["id"])
                emails.append({
                    "id": detail["id"],
                    "from": detail["from"],
                    "subject": detail["subject"],
                    "date": detail["date"],
                    "snippet": detail["snippet"],
                })
            except Exception:
                continue

        return json.dumps({
            "status": "success",
            "count": len(emails),
            "emails": emails,
        })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@tool
def read_email(message_id: str) -> str:
    """
    Read the full content of a specific email by its message ID.
    Returns complete email including headers and body text.
    Use this after finding an email with search_emails to get full content.
    """
    try:
        detail = get_email_detail(message_id)
        return json.dumps({"status": "success", "email": detail})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@tool
def get_recent_emails(count: int = 10) -> str:
    """
    Get the most recent emails from the inbox.
    Use when user asks 'show me my latest emails' or 'what's in my inbox'.
    Count can be 1-20.
    """
    try:
        emails = list_recent_emails(count=min(count, 20))
        if not emails:
            return json.dumps({"status": "empty", "message": "No emails found in inbox.", "emails": []})
        # Return summaries for context efficiency
        summaries = [{
            "id": e["id"],
            "from": e["from"],
            "subject": e["subject"],
            "date": e["date"],
            "snippet": e["snippet"],
        } for e in emails]
        return json.dumps({"status": "success", "count": len(summaries), "emails": summaries})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@tool
def create_draft(to: str, subject: str, body: str) -> str:
    """
    Create an email draft in Gmail (does NOT send it).
    Use when user asks to 'draft an email' or 'compose a message'.
    Args:
        to: Recipient email address
        subject: Email subject line
        body: Email body text
    Returns draft confirmation with draft ID.
    """
    try:
        if not to or "@" not in to:
            return json.dumps({"status": "error", "message": "Invalid recipient email address."})
        result = create_draft_raw(to=to, subject=subject, body=body)
        return json.dumps({"status": "success", **result})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@tool
def send_email(to: str, subject: str, body: str) -> str:
    """
    Send an email via Gmail. This action is IRREVERSIBLE.
    Only call this tool after the user has explicitly confirmed they want to send.
    Args:
        to: Recipient email address
        subject: Email subject line
        body: Email body text
    """
    try:
        if not to or "@" not in to:
            return json.dumps({"status": "error", "message": "Invalid recipient email address."})
        result = send_email_raw(to=to, subject=subject, body=body)
        return json.dumps({"status": "success", **result,
                           "message": f"Email sent to {to} with subject '{subject}'."})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@tool
def reply_to_email(message_id: str, body: str) -> str:
    """
    Reply to an existing email thread by message ID.
    Use when user says 'reply to this email' or 'respond to X's email'.
    Only call after user confirmation for important replies.
    Args:
        message_id: The ID of the email to reply to
        body: The reply message body text
    """
    try:
        result = reply_to_email_raw(message_id=message_id, body=body)
        return json.dumps({"status": "success", **result})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


# ── Tool Registry ────────────────────────────────────────────────────────────
# All email tools in a single list for easy binding to agents
ALL_EMAIL_TOOLS = [
    search_emails,
    read_email,
    get_recent_emails,
    create_draft,
    send_email,
    reply_to_email,
]
