"""
Larvi — Email Agent
A LangChain ReAct agent specialized in email operations.
Uses all Gmail tools to search, read, draft, and send emails.
"""
import json
from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_react_agent, AgentExecutor
from langchain_core.prompts import PromptTemplate

from config import settings
from tools.email_tools import ALL_EMAIL_TOOLS
from memory.context_manager import Session


from datetime import datetime


EMAIL_AGENT_PROMPT = PromptTemplate.from_template("""You are Larvi's Email Agent — a specialized AI assistant for managing Gmail.

Today's Date & Time: {current_datetime}

Your capabilities:
- Search emails by sender, subject, keywords, or any Gmail operator
- Read full email content
- Get recent emails from inbox
- Create email drafts
- Send emails (ONLY after user explicitly confirms)
- Reply to emails (ONLY after user explicitly confirms)

IMPORTANT SAFETY RULES:
1. Today's live date is {current_datetime}. When dates/times are mentioned, calculate relative to this live date.
2. NEVER send or reply to emails without explicit user confirmation.
3. If asked to send/reply, create a draft first and ask user to confirm.
4. Always be honest — if an email is not found, say so clearly.
5. Extract and return useful information (dates, times, names, meeting details) from emails.

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


def run_email_agent(task: str, session: Session) -> dict:
    """
    Run the Email Agent on a given task.
    
    Args:
        task: Natural language email task
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
            tools=ALL_EMAIL_TOOLS,
            prompt=EMAIL_AGENT_PROMPT,
        )
        executor = AgentExecutor(
            agent=agent,
            tools=ALL_EMAIL_TOOLS,
            verbose=True,
            max_iterations=8,
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

        response_text = result.get("output", "I couldn't process that email request.")
        intermediate_steps = result.get("intermediate_steps", [])

        # Extract tool call logs
        tool_calls = _extract_tool_calls(intermediate_steps)

        # Update working memory from tool results
        _update_memory_from_steps(session, intermediate_steps)

        return {
            "agent": "email_agent",
            "response": response_text,
            "tool_calls": tool_calls,
            "requires_confirmation": _check_needs_confirmation(response_text, tool_calls),
        }

    except Exception as e:
        return {
            "agent": "email_agent",
            "response": f"I encountered an error while processing your email request: {str(e)}",
            "tool_calls": [],
            "requires_confirmation": False,
        }


def _format_chat_history(messages: list[dict]) -> str:
    """Format chat history for prompt injection."""
    if not messages:
        return "No previous conversation."
    lines = []
    for msg in messages[-10:]:  # Last 10 messages for context
        role = "User" if msg["role"] == "user" else "Larvi"
        lines.append(f"{role}: {msg['content']}")
    return "\n".join(lines)


def _extract_tool_calls(intermediate_steps: list) -> list[dict]:
    """Extract clean tool call log from agent intermediate steps."""
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
    """Create a human-readable summary of a tool result."""
    if tool_name == "search_emails":
        count = result.get("count", 0)
        return f"Found {count} email(s)"
    elif tool_name == "read_email":
        email = result.get("email", {})
        return f"Read email: '{email.get('subject', 'Unknown')}' from {email.get('from', 'Unknown')}"
    elif tool_name == "get_recent_emails":
        count = result.get("count", 0)
        return f"Retrieved {count} recent email(s)"
    elif tool_name == "create_draft":
        return f"Draft created for {result.get('to', 'unknown recipient')}"
    elif tool_name == "send_email":
        return f"Email sent to {result.get('to', 'unknown')}"
    elif tool_name == "reply_to_email":
        return f"Reply sent to {result.get('to', 'unknown')}"
    return f"Tool executed with status: {result.get('status', 'unknown')}"


def _update_memory_from_steps(session: Session, intermediate_steps: list) -> None:
    """Update session working memory based on what email tools returned."""
    for action, observation in intermediate_steps:
        try:
            result = json.loads(observation) if isinstance(observation, str) else observation
            # Update memory from email reads
            if action.tool in ("read_email", "search_emails") and result.get("status") == "success":
                email_data = result.get("email") or (result.get("emails", [{}])[0] if result.get("emails") else None)
                if email_data:
                    session.working_memory.update_from_email(email_data)
        except Exception:
            continue


def _check_needs_confirmation(response: str, tool_calls: list) -> bool:
    """Detect if the agent is proposing a send/reply action that needs confirmation."""
    destructive_tools = {"send_email", "reply_to_email"}
    tools_used = {tc["tool"] for tc in tool_calls}
    return bool(destructive_tools.intersection(tools_used))
