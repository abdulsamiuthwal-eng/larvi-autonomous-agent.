"""
Larvi — Calendar Tools
LangChain-compatible tool definitions that wrap Google Calendar service calls.
The Calendar Agent and Master Agent use these tools to perform real actions.
"""
import json
from langchain_core.tools import tool

from services.gcal_service import (
    get_upcoming_events,
    search_calendar_events,
    check_free_busy,
    create_calendar_event,
    update_calendar_event,
    delete_calendar_event,
    get_event_by_id,
)


from typing import Any, Union

# Module-level deduplication cache to prevent duplicate event creation within same agent run
_CREATE_EVENT_CACHE: dict = {}


def _try_unpack_json(val: Any) -> dict:
    """Helper to unpack LLM-stringified JSON argument dictionaries."""
    if isinstance(val, dict):
        return val
    if isinstance(val, str) and val.strip().startswith("{") and val.strip().endswith("}"):
        try:
            return json.loads(val)
        except Exception:
            pass
    return {}


def _parse_int_arg(val: Any, default: int = 7) -> int:
    """Safely parse integer arguments from int, string, or json-stringified inputs."""
    if isinstance(val, int):
        return val
    if isinstance(val, dict):
        return int(val.get("days_ahead", default))
    if isinstance(val, str):
        val_str = val.strip()
        if val_str.startswith("{") and val_str.endswith("}"):
            try:
                d = json.loads(val_str)
                return int(d.get("days_ahead", default))
            except Exception:
                pass
        try:
            return int(val_str)
        except ValueError:
            return default
    return default


@tool
def get_events(days_ahead: Union[int, str, Any] = 7) -> str:
    """
    Get upcoming calendar events for the next N days.
    Use when user asks 'what meetings do I have', 'show my schedule', or 'what's happening today/tomorrow'.
    days_ahead: Number of days to look ahead (1=today, 2=tomorrow, 7=this week)
    """
    try:
        parsed_days = _parse_int_arg(days_ahead, default=7)
        events = get_upcoming_events(days_ahead=parsed_days)
        if not events:
            return json.dumps({
                "status": "empty",
                "message": f"No events found in the next {parsed_days} day(s).",
                "events": [],
            })
        return json.dumps({"status": "success", "count": len(events), "events": events})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@tool
def search_events(query: Union[str, Any]) -> str:
    """
    Search calendar events by keyword or topic.
    Use when user asks about a specific meeting by name or topic.
    Examples: 'project meeting', 'standup', 'interview with Ali'
    """
    try:
        unpacked = _try_unpack_json(query)
        if unpacked:
            query = unpacked.get("query", str(query))
        elif not isinstance(query, str):
            query = str(query)

        events = search_calendar_events(query=query)
        if not events:
            return json.dumps({
                "status": "no_results",
                "message": f"No calendar events found matching: '{query}'",
                "events": [],
            })
        return json.dumps({"status": "success", "count": len(events), "events": events})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@tool
def check_availability(date: str, start_time: str = "09:00", end_time: str = "17:00") -> str:
    """
    Check if the user is free during a specific time slot.
    ALWAYS call this ONCE before creating a new event to detect conflicts. Do NOT call it again.
    Args:
        date: Date in YYYY-MM-DD format (e.g., '2024-01-15')
        start_time: Start time in HH:MM 24-hour format (e.g., '14:00')
        end_time: End time in HH:MM 24-hour format (e.g., '15:00')
    Returns whether the user is free and lists any conflicts.
    """
    try:
        # Check if LLM passed full payload inside date as a JSON string
        unpacked = _try_unpack_json(date)
        if unpacked:
            date = unpacked.get("date", date)
            start_time = unpacked.get("start_time", start_time)
            end_time = unpacked.get("end_time", end_time)

        result = check_free_busy(date_str=date, start_time_str=start_time, end_time_str=end_time)
        conflicts = result.get("conflicts", [])
        n = len(conflicts)
        if result["free"]:
            result["message"] = (
                f"✅ AVAILABLE: You are free on {date} from {start_time} to {end_time}. "
                f"No conflicts found. STOP checking availability — call create_event NOW."
            )
        else:
            result["message"] = (
                f"⚠️ CONFLICT: {n} conflicting event(s) on {date} from {start_time} to {end_time}. "
                "Ask user if they want to proceed anyway or pick a different time."
            )
        return json.dumps({"status": "success", **result})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})



@tool
def create_event(
    title: str,
    date: str = "",
    start_time: str = "09:00",
    end_time: str = "10:00",
    description: str = "",
    attendees: str = "",
) -> str:
    """
    Create a new event in Google Calendar.
    IMPORTANT: Call this ONCE only after check_availability confirms the slot is free.
    Do NOT call this tool more than once per request — it will create duplicate events.
    Args:
        title: Event title/name
        date: Date in YYYY-MM-DD format
        start_time: Start time in HH:MM 24-hour format (e.g., '10:00')
        end_time: End time in HH:MM 24-hour format (e.g., '11:00')
        description: Optional event description / agenda
        attendees: Comma-separated list of email addresses
    """
    import time as _time

    try:
        unpacked = _try_unpack_json(title)
        if unpacked:
            title = unpacked.get("title", title)
            date = unpacked.get("date", date)
            start_time = unpacked.get("start_time", start_time)
            end_time = unpacked.get("end_time", end_time)
            description = unpacked.get("description", description)
            attendees = unpacked.get("attendees", attendees)

        # Deduplication guard — prevent same event from being created twice in same agent run
        dedup_key = f"{title}|{date}|{start_time}|{end_time}"
        now = _time.time()
        cached = _CREATE_EVENT_CACHE.get(dedup_key)
        if cached and (now - cached["ts"]) < 60:
            return json.dumps({
                "status": "success",
                "message": f"✅ Event '{title}' already created on {date} from {start_time} to {end_time}. Action is complete. Write your Final Answer now.",
                "event": cached["event"],
            })

        attendees_list = [a.strip() for a in attendees.split(",") if a.strip() and "@" in a] if attendees else []
        event = create_calendar_event(
            title=title,
            date_str=date,
            start_time_str=start_time,
            end_time_str=end_time,
            description=description,
            attendees=attendees_list,
        )

        _CREATE_EVENT_CACHE[dedup_key] = {"event": event, "ts": now}

        return json.dumps({
            "status": "success",
            "message": f"✅ Event '{title}' created on {date} from {start_time} to {end_time}. Action is complete. Write your Final Answer now.",
            "event": event,
        })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})



@tool
def update_event(event_id: str, changes: str) -> str:
    """
    Update an existing calendar event. Used for rescheduling or editing events.
    Use when user says 'move my meeting', 'reschedule', or 'change the time'.
    Args:
        event_id: The Google Calendar event ID (get this from search_events or get_events)
        changes: JSON string with fields to change.
                 Example: '{"start_time": "17:00", "end_time": "18:00"}'
                 Supported fields: title, date (YYYY-MM-DD), start_time (HH:MM), end_time (HH:MM), description
    """
    try:
        changes_dict = json.loads(changes) if isinstance(changes, str) else changes
        updated_event = update_calendar_event(event_id=event_id, changes=changes_dict)
        return json.dumps({
            "status": "success",
            "message": f"✅ Event updated successfully.",
            "event": updated_event,
        })
    except json.JSONDecodeError:
        return json.dumps({"status": "error", "message": "Invalid changes format. Must be valid JSON."})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


@tool
def delete_event(event_id: str) -> str:
    """
    Permanently delete a calendar event. This action is IRREVERSIBLE.
    Only call this tool after the user has explicitly confirmed they want to delete.
    Args:
        event_id: The Google Calendar event ID to delete
    """
    try:
        result = delete_calendar_event(event_id=event_id)
        return json.dumps({
            "status": "success",
            "message": "✅ Event permanently deleted.",
            **result,
        })
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


# ── Tool Registry ─────────────────────────────────────────────────────────────
ALL_CALENDAR_TOOLS = [
    get_events,
    search_events,
    check_availability,
    create_event,
    update_event,
    delete_event,
]
