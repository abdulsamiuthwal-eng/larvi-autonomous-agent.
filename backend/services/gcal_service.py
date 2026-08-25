"""
Larvi — Google Calendar Service
Authenticated Google Calendar API client wrapper.
All tools in calendar_tools.py call methods from this service.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from auth.google_oauth import get_or_create_credentials
from memory.context_manager import current_session_id


def _get_calendar_client(session_id: Optional[str] = None):
    """Build and return an authenticated Google Calendar API client for the active session."""
    sid = session_id or current_session_id.get()
    creds = get_or_create_credentials(sid)
    if creds is None:
        raise PermissionError(
            "Not authenticated with Google. Please connect your Google account in Larvi first."
        )
    return build("calendar", "v3", credentials=creds)


def get_upcoming_events(days_ahead: int = 7, max_results: int = 20) -> list[dict]:
    """
    Fetch upcoming calendar events from now until N days ahead.
    Returns list of parsed event dicts.
    """
    service = _get_calendar_client()
    now = datetime.now(timezone.utc)
    time_min = now.isoformat()
    time_max = (now + timedelta(days=days_ahead)).isoformat()

    try:
        result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        return [_parse_event(e) for e in result.get("items", [])]
    except HttpError as e:
        raise RuntimeError(f"Calendar API get_events error: {e}")


def search_calendar_events(query: str, days_ahead: int = 30) -> list[dict]:
    """Search calendar events by text query."""
    service = _get_calendar_client()
    now = datetime.now(timezone.utc)
    try:
        result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=now.isoformat(),
                timeMax=(now + timedelta(days=days_ahead)).isoformat(),
                q=query,
                singleEvents=True,
                orderBy="startTime",
                maxResults=20,
            )
            .execute()
        )
        return [_parse_event(e) for e in result.get("items", [])]
    except HttpError as e:
        raise RuntimeError(f"Calendar API search error: {e}")


def check_free_busy(date_str: str, start_time_str: str, end_time_str: str) -> dict:
    """
    Check if user is free during a time slot.
    Args: date_str='2024-01-15', start_time_str='14:00', end_time_str='15:00'
    Returns: { free: bool, conflicts: list }
    """
    service = _get_calendar_client()
    try:
        # Parse times
        start_dt = datetime.strptime(f"{date_str} {start_time_str}", "%Y-%m-%d %H:%M")
        end_dt = datetime.strptime(f"{date_str} {end_time_str}", "%Y-%m-%d %H:%M")

        # Make timezone-aware (use local timezone)
        import time as time_module
        local_offset = -time_module.timezone
        tz = timezone(timedelta(seconds=local_offset))
        start_dt = start_dt.replace(tzinfo=tz)
        end_dt = end_dt.replace(tzinfo=tz)

        body = {
            "timeMin": start_dt.isoformat(),
            "timeMax": end_dt.isoformat(),
            "items": [{"id": "primary"}],
        }
        result = service.freebusy().query(body=body).execute()
        busy_slots = result.get("calendars", {}).get("primary", {}).get("busy", [])

        return {
            "free": len(busy_slots) == 0,
            "conflicts": busy_slots,
            "checked_slot": f"{date_str} {start_time_str}–{end_time_str}",
        }
    except HttpError as e:
        raise RuntimeError(f"Calendar API free/busy error: {e}")


def create_calendar_event(
    title: str,
    date_str: str,
    start_time_str: str,
    end_time_str: str,
    description: str = "",
    attendees: Optional[list[str]] = None,
) -> dict:
    """
    Create a new Google Calendar event.
    Returns the created event details.
    """
    service = _get_calendar_client()
    try:
        start_dt = datetime.strptime(f"{date_str} {start_time_str}", "%Y-%m-%d %H:%M")
        end_dt = datetime.strptime(f"{date_str} {end_time_str}", "%Y-%m-%d %H:%M")

        event_body = {
            "summary": title,
            "description": description,
            "start": {
                "dateTime": start_dt.isoformat(),
                "timeZone": "Asia/Karachi",
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": "Asia/Karachi",
            },
        }

        if attendees:
            event_body["attendees"] = [{"email": a} for a in attendees]

        created = (
            service.events()
            .insert(calendarId="primary", body=event_body, sendUpdates="all")
            .execute()
        )
        return _parse_event(created)
    except HttpError as e:
        raise RuntimeError(f"Calendar API create_event error: {e}")


def update_calendar_event(event_id: str, changes: dict) -> dict:
    """
    Update an existing calendar event by ID.
    changes dict can include: title, date, start_time, end_time, description
    """
    service = _get_calendar_client()
    try:
        # Fetch existing event first
        existing = service.events().get(calendarId="primary", eventId=event_id).execute()

        # Apply changes
        if "title" in changes:
            existing["summary"] = changes["title"]
        if "description" in changes:
            existing["description"] = changes["description"]
        if "start_time" in changes or "date" in changes:
            date = changes.get("date", existing["start"]["dateTime"][:10])
            start_time = changes.get("start_time", existing["start"]["dateTime"][11:16])
            end_time = changes.get("end_time", existing["end"]["dateTime"][11:16])
            start_dt = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M")
            end_dt = datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M")
            existing["start"]["dateTime"] = start_dt.isoformat()
            existing["end"]["dateTime"] = end_dt.isoformat()

        updated = (
            service.events()
            .update(calendarId="primary", eventId=event_id, body=existing)
            .execute()
        )
        return _parse_event(updated)
    except HttpError as e:
        raise RuntimeError(f"Calendar API update_event error: {e}")


def delete_calendar_event(event_id: str) -> dict:
    """Permanently delete a calendar event. Returns confirmation."""
    service = _get_calendar_client()
    try:
        service.events().delete(calendarId="primary", eventId=event_id).execute()
        return {"status": "deleted", "event_id": event_id}
    except HttpError as e:
        raise RuntimeError(f"Calendar API delete_event error: {e}")


def get_event_by_id(event_id: str) -> dict:
    """Fetch a single event by its ID."""
    service = _get_calendar_client()
    try:
        event = service.events().get(calendarId="primary", eventId=event_id).execute()
        return _parse_event(event)
    except HttpError as e:
        raise RuntimeError(f"Calendar API get_event error: {e}")


# ── Private Helpers ────────────────────────────────────────────────────────────

def _parse_event(event: dict) -> dict:
    """Parse Google Calendar API event object into clean structured dict."""
    start = event.get("start", {})
    end = event.get("end", {})
    start_str = start.get("dateTime", start.get("date", ""))
    end_str = end.get("dateTime", end.get("date", ""))

    return {
        "id": event.get("id", ""),
        "title": event.get("summary", "(No Title)"),
        "description": event.get("description", ""),
        "start": start_str,
        "end": end_str,
        "location": event.get("location", ""),
        "attendees": [
            a.get("email", "") for a in event.get("attendees", [])
        ],
        "status": event.get("status", "confirmed"),
        "html_link": event.get("htmlLink", ""),
    }
