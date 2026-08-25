"""
Larvi — Calendar Agent
A LangChain ReAct agent specialized in Google Calendar operations.
Uses all calendar tools to view, create, update, and delete events.
"""
import json
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import PromptTemplate

from config import settings
from tools.calendar_tools import ALL_CALENDAR_TOOLS
from memory.context_manager import Session


from datetime import datetime


CALENDAR_AGENT_PROMPT = PromptTemplate.from_template("""You are Larvi's Calendar Agent — a specialized AI assistant for managing Google Calendar.

Today's Date & Time: {current_datetime}

Your capabilities:
- View upcoming calendar events
- Search events by keyword or topic
- Check user availability (free/busy) for specific time slots
- Create new calendar events (ALWAYS check availability first)
- Update/reschedule existing events
- Delete events (ONLY after user explicitly confirms)

IMPORTANT SAFETY & DATE RULES:
1. Today's live date is {current_datetime}. When the user says "today", "tomorrow", or "next week", ALWAYS calculate relative to this live date. Never use 2024 or outdated years.
2. ALWAYS call check_availability before creating any new event.
3. NEVER delete an event without explicit user confirmation.
4. For rescheduling, always check the new slot's availability first.
5. If a conflict is detected, inform the user and suggest alternatives.
6. When creating events from email info, verify all details (date, time, title) before proceeding.

DATE/TIME FORMAT:
- Dates: YYYY-MM-DD (e.g., 2026-08-26)
- Times: HH:MM in 24-hour format (e.g., 10:00 for 10 AM, 14:00 for 2 PM, 17:00 for 5 PM)
- Tool Inputs: Pass standard primitive values (e.g., days_ahead=2 as number or string). Do not enclose simple parameters in JSON unless requested.

Current working memory context:
{working_memory}

Conversation history:
{chat_history}

You have access to the following tools:
{tools}

Tool names: {tool_names}

Use the following format:
Question: the input question you must answer
Thought: think about what to do
Action: the tool name to use (must be one of [{tool_names}])
Action Input: the input to the tool
Observation: the result of the tool
... (repeat Thought/Action/Observation as needed)
Thought: I now know the final answer
Final Answer: your comprehensive, helpful response to the user

Begin!

Question: {input}
Thought: {agent_scratchpad}""")


from agents.llm_factory import get_llm, invoke_llm_with_fallback


def run_calendar_agent(task: str, session: Session) -> dict:
    """
    Run the Calendar Agent on a given task.

    Args:
        task: Natural language calendar task
        session: Current user session with working memory

    Returns:
        dict with response, tool_calls, and updated working memory data
    """
    working_memory_ctx = session.working_memory.get_context_summary()
    chat_history = _format_chat_history(session.get_history_for_llm())
    current_dt = datetime.now().strftime("%Y-%m-%d %H:%M (%A)")

    def _execute_agent(model_name: str):
        llm = get_llm(temperature=0.1, model=model_name)
        agent = create_react_agent(
            llm=llm,
            tools=ALL_CALENDAR_TOOLS,
            prompt=CALENDAR_AGENT_PROMPT,
        )
        executor = AgentExecutor(
            agent=agent,
            tools=ALL_CALENDAR_TOOLS,
            verbose=True,
            max_iterations=10,
            handle_parsing_errors=True,
            return_intermediate_steps=True,
        )
        return executor.invoke({
            "input": task,
            "current_datetime": current_dt,
            "working_memory": working_memory_ctx or "No previous context.",
            "chat_history": chat_history,
        })

    try:
        result = invoke_llm_with_fallback(_execute_agent)

        response_text = result.get("output", "I couldn't process that calendar request.")
        intermediate_steps = result.get("intermediate_steps", [])

        tool_calls = _extract_tool_calls(intermediate_steps)
        _update_memory_from_steps(session, intermediate_steps)

        return {
            "agent": "calendar_agent",
            "response": response_text,
            "tool_calls": tool_calls,
            "requires_confirmation": _check_needs_confirmation(tool_calls),
        }

    except Exception as e:
        return {
            "agent": "calendar_agent",
            "response": f"I encountered an error with your calendar request: {str(e)}",
            "tool_calls": [],
            "requires_confirmation": False,
        }


def _format_chat_history(messages: list[dict]) -> str:
    if not messages:
        return "No previous conversation."
    lines = []
    for msg in messages[-10:]:
        role = "User" if msg["role"] == "user" else "Larvi"
        lines.append(f"{role}: {msg['content']}")
    return "\n".join(lines)


def _extract_tool_calls(intermediate_steps: list) -> list[dict]:
    tool_calls = []
    for action, observation in intermediate_steps:
        try:
            obs_data = json.loads(observation) if isinstance(observation, str) else observation
            tool_calls.append({
                "tool": action.tool,
                "input": action.tool_input,
                "result_status": obs_data.get("status", "unknown"),
                "summary": _summarize_tool_result(action.tool, obs_data),
            })
        except Exception:
            tool_calls.append({
                "tool": getattr(action, "tool", "unknown"),
                "input": getattr(action, "tool_input", ""),
                "result_status": "parsed",
                "summary": str(observation)[:200],
            })
    return tool_calls


def _summarize_tool_result(tool_name: str, result: dict) -> str:
    if tool_name == "get_events":
        return f"Retrieved {result.get('count', 0)} upcoming event(s)"
    elif tool_name == "search_events":
        return f"Found {result.get('count', 0)} matching event(s)"
    elif tool_name == "check_availability":
        if result.get("free"):
            return f"✅ Free during {result.get('checked_slot', 'requested time')}"
        else:
            conflicts = len(result.get("conflicts", []))
            return f"⚠️ {conflicts} conflict(s) found during {result.get('checked_slot', 'requested time')}"
    elif tool_name == "create_event":
        event = result.get("event", {})
        return f"✅ Created: '{event.get('title', 'Event')}' on {event.get('start', '')[:10]}"
    elif tool_name == "update_event":
        event = result.get("event", {})
        return f"✅ Updated: '{event.get('title', 'Event')}'"
    elif tool_name == "delete_event":
        return "✅ Event deleted"
    return f"Tool executed: {result.get('status', 'unknown')}"


def _update_memory_from_steps(session: Session, intermediate_steps: list) -> None:
    for action, observation in intermediate_steps:
        try:
            result = json.loads(observation) if isinstance(observation, str) else observation
            if action.tool in ("create_event", "update_event", "get_events", "search_events"):
                if result.get("status") == "success":
                    event_data = result.get("event") or (
                        result.get("events", [{}])[0] if result.get("events") else None
                    )
                    if event_data:
                        session.working_memory.update_from_event(event_data)
        except Exception:
            continue


def _check_needs_confirmation(tool_calls: list) -> bool:
    destructive_tools = {"delete_event", "create_event", "update_event"}
    tools_used = {tc["tool"] for tc in tool_calls}
    return bool(destructive_tools.intersection(tools_used))
