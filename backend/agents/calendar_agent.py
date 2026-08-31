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
- Delete events (ONLY after user explicitly confirms)

STRICT WORKFLOW RULES — FOLLOW EXACTLY:
1. Today's live date is {current_datetime}. ALWAYS calculate "today", "tomorrow", "next week" relative to this date.
2. To schedule an event:
   - Step 1: Call `check_availability` ONCE for the requested date and time.
   - Step 2: Call `create_event` ONCE.
   - Step 3: IMMEDIATELY output your Final Answer. Example: `Final Answer: I have scheduled your meeting on [Date] from [Start] to [End].`
3. NEVER call `create_event` more than once! Once you see `✅ Event created`, you MUST stop and give your Final Answer.
4. NEVER call `check_availability` more than once.
5. NEVER delete an event without explicit user confirmation.
6. For rescheduling, check new slot once then update immediately and provide Final Answer.

DATE/TIME FORMAT:
- Dates: YYYY-MM-DD (e.g., 2026-08-26)
- Times: HH:MM in 24-hour format (e.g., 10:00 for 10 AM, 13:00 for 1 PM, 14:00 for 2 PM)
- Tool Inputs: Pass standard primitive values. Do not enclose simple parameters in JSON unless requested.

Current working memory context:
{working_memory}

Conversation history:
{chat_history}

You have access to the following tools:
{tools}

Tool names: {tool_names}

Use the following EXACT format (do NOT use markdown bold like **Thought:** or **Action:**, write plain text):
Question: the input question you must answer
Thought: you should always think about what to do
Action: the tool name to use, exactly one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

CRITICAL FORMATTING INSTRUCTIONS:
- Every Thought that uses a tool MUST immediately be followed by Action: and Action Input:
- Once an event is created or tool finishes, immediately output:
Thought: I now know the final answer
Final Answer: your response to the user

Begin!

Question: {input}
Thought:{agent_scratchpad}""")


from agents.llm_factory import get_llm, invoke_llm_with_fallback


def _custom_handle_parsing_errors(error) -> str:
    err_str = str(error)
    if "Could not parse LLM output:" in err_str:
        raw = err_str.split("Could not parse LLM output:")[1].strip("` \n")
        # If the raw text contains a tool name pattern like 'tool_name(' or 'Action:',
        # it's a malformed tool call - tell agent to use correct format
        tool_names = ["check_availability", "create_event", "update_event", "delete_event",
                      "list_events", "search_events"]
        if any(t in raw for t in tool_names) or "Action:" in raw:
            return (
                "Invalid format. You must use this exact format:\n"
                "Thought: <your reasoning>\n"
                "Action: <tool_name>\n"
                "Action Input: <input>\n"
                "If you already completed the task, write:\n"
                "Thought: I now know the final answer\n"
                "Final Answer: <your response>"
            )
        # Raw text looks like a natural language response — use as Final Answer
        if len(raw) > 20 and not raw.startswith("{"):
            return f"Thought: I now know the final answer\nFinal Answer: {raw}"
    return (
        "Format error. Use one of these formats:\n"
        "To use a tool: Thought/Action/Action Input\n"
        "To finish: Thought: I now know the final answer\nFinal Answer: <response>"
    )


def _build_fallback_response(intermediate_steps: list, original_task: str) -> str:
    """Build a meaningful response from completed tool steps when agent hits iteration limit."""
    import json as _json
    created_events = []
    for step in intermediate_steps:
        if not isinstance(step, (list, tuple)) or len(step) < 2:
            continue
        action = step[0]
        observation = step[1]
        tool_name = getattr(action, "tool", "")
        if tool_name == "create_event":
            try:
                obs_data = _json.loads(observation) if isinstance(observation, str) else {}
                if obs_data.get("status") == "success":
                    event = obs_data.get("event", {})
                    created_events.append({
                        "title": event.get("summary", "Event"),
                        "date": event.get("start", {}).get("date") or event.get("start", {}).get("dateTime", "")[:10],
                        "start": event.get("start", {}).get("dateTime", "")[11:16],
                        "end": event.get("end", {}).get("dateTime", "")[11:16],
                    })
            except Exception:
                pass

    if created_events:
        parts = []
        for ev in created_events:
            title = ev["title"]
            date = ev["date"]
            start = ev["start"]
            end = ev["end"]
            parts.append(f"✅ **{title}** on {date} from {start} to {end}")
        return "I've successfully added the following to your calendar:\n" + "\n".join(parts)

    return "I've processed your calendar request. Please check your Google Calendar to see the updates."


def run_calendar_agent(task: str, session: Session) -> dict:
    """
    Run the Calendar Agent on a given task.
    
    Args:
        task: Natural language calendar task
        session: Active session object with working memory

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
            max_iterations=5,
            max_execution_time=45,
            handle_parsing_errors=_custom_handle_parsing_errors,
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

        response_text = result.get("output", "")
        intermediate_steps = result.get("intermediate_steps", [])

        # If agent stopped at iteration limit, build a helpful response from tool results
        if not response_text or "agent stopped" in response_text.lower() or "iteration limit" in response_text.lower():
            response_text = _build_fallback_response(intermediate_steps, task)

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
    """Detect if the agent is proposing a destructive calendar action (e.g. deleting an event)."""
    destructive_tools = {"delete_event"}
    tools_used = {tc.get("tool") for tc in tool_calls if isinstance(tc, dict)}
    return bool(destructive_tools.intersection(tools_used))
