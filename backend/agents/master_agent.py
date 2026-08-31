"""
Larvi — Master Agent (Central Orchestrator)
The brain of Larvi. Receives user input, classifies intent,
routes to Email Agent / Calendar Agent / both, and synthesizes the final response.
Uses LangGraph StateGraph for multi-step workflow orchestration.
"""
import json
import re
from typing import TypedDict, Annotated, Literal
from datetime import datetime

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END

from config import settings
from agents.email_agent import run_email_agent
from agents.calendar_agent import run_calendar_agent
from memory.context_manager import Session


# ── Graph State Definition ────────────────────────────────────────────────────

class LarviState(TypedDict):
    """The state that flows through the LangGraph workflow nodes."""
    user_input: str
    session: Session
    intent: str                   # "email" | "calendar" | "multi" | "chitchat"
    email_task: str               # Subtask for Email Agent
    calendar_task: str            # Subtask for Calendar Agent
    email_result: dict            # Result from Email Agent
    calendar_result: dict         # Result from Calendar Agent
    workflow_steps: list[dict]    # Step-by-step workflow log
    requires_confirmation: bool   # Whether UI should show confirm dialog
    pending_confirmation_data: dict  # Data for the pending action
    final_response: str           # Final user-facing response


# ── Intent Classification ─────────────────────────────────────────────────────

INTENT_PROMPT = """You are Larvi's intent classifier. Analyze the user's message and classify it.

IMPORTANT: Use the working memory context to understand references like "it", "that meeting", "the email".

Working Memory:
{working_memory}

User message: "{user_input}"

Classify the intent as ONE of:
- "email": Only email operations needed (search, read, draft, send)
- "calendar": Only calendar operations needed (view events, schedule, reschedule, check availability)
- "multi": BOTH email AND calendar operations needed (e.g., "find email from X and add meeting to calendar")
- "chitchat": General conversation, greetings, questions about Larvi itself

Also extract:
- email_task: The specific email subtask (empty string if not email-related)
- calendar_task: The specific calendar subtask (empty string if not calendar-related)

Respond in this exact JSON format:
{{
  "intent": "email|calendar|multi|chitchat",
  "email_task": "specific email task description or empty string",
  "calendar_task": "specific calendar task description or empty string",
  "confidence": 0.95
}}

Today's date is: {today}
"""


from agents.llm_factory import get_llm, invoke_llm_with_fallback


def classify_intent(state: LarviState) -> LarviState:
    """Node 1: Classify user intent and extract sub-tasks."""
    session = state["session"]
    working_memory = session.working_memory.get_context_summary()
    today = datetime.now().strftime("%Y-%m-%d (%A)")

    prompt = INTENT_PROMPT.format(
        working_memory=working_memory or "No previous context",
        user_input=state["user_input"],
        today=today,
    )

    def _do_classify(model_name: str):
        llm = get_llm(temperature=0, model=model_name)
        return llm.invoke([HumanMessage(content=prompt)])

    try:
        response = invoke_llm_with_fallback(_do_classify)
        raw = response.content.strip()
    except Exception:
        raw = "{}"

    # Extract JSON from response
    try:
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
        else:
            data = {"intent": "chitchat", "email_task": "", "calendar_task": ""}
    except Exception:
        data = {"intent": "chitchat", "email_task": "", "calendar_task": ""}

    intent = data.get("intent", "chitchat")
    email_task = data.get("email_task", "")
    calendar_task = data.get("calendar_task", "")

    # For email/calendar intents, use full user_input if subtask is empty
    if intent == "email" and not email_task:
        email_task = state["user_input"]
    if intent == "calendar" and not calendar_task:
        calendar_task = state["user_input"]

    new_state = dict(state)
    new_state["intent"] = intent
    new_state["email_task"] = email_task
    new_state["calendar_task"] = calendar_task
    new_state["workflow_steps"] = [
        {
            "step": 1,
            "name": "Analyze Request",
            "status": "done",
            "detail": f"Intent: {intent.upper()} | Routing to appropriate agent(s)",
        }
    ]
    return new_state


def route_intent(state: LarviState) -> Literal["email_node", "calendar_node", "multi_node", "chitchat_node"]:
    """Router: Directs workflow to the correct node based on classified intent."""
    intent = state.get("intent", "chitchat")
    routing = {
        "email": "email_node",
        "calendar": "calendar_node",
        "multi": "multi_node",
        "chitchat": "chitchat_node",
    }
    return routing.get(intent, "chitchat_node")


# ── Agent Execution Nodes ─────────────────────────────────────────────────────

def email_node(state: LarviState) -> LarviState:
    """Node: Run Email Agent."""
    new_state = dict(state)
    steps = list(state.get("workflow_steps", []))
    steps.append({"step": 2, "name": "Email Agent", "status": "in_progress", "detail": "Searching and processing emails..."})
    new_state["workflow_steps"] = steps

    result = run_email_agent(task=state["email_task"], session=state["session"])

    steps[-1]["status"] = "done"
    steps[-1]["detail"] = f"Email Agent completed. Tool calls: {len(result.get('tool_calls', []))}"
    new_state["email_result"] = result
    new_state["requires_confirmation"] = result.get("requires_confirmation", False)
    return new_state


def calendar_node(state: LarviState) -> LarviState:
    """Node: Run Calendar Agent."""
    new_state = dict(state)
    steps = list(state.get("workflow_steps", []))
    steps.append({"step": 2, "name": "Calendar Agent", "status": "in_progress", "detail": "Checking calendar..."})
    new_state["workflow_steps"] = steps

    result = run_calendar_agent(task=state["calendar_task"], session=state["session"])

    steps[-1]["status"] = "done"
    steps[-1]["detail"] = f"Calendar Agent completed. Tool calls: {len(result.get('tool_calls', []))}"
    new_state["calendar_result"] = result
    new_state["requires_confirmation"] = result.get("requires_confirmation", False)
    return new_state


def multi_node(state: LarviState) -> LarviState:
    """
    Node: Multi-agent workflow — Email Agent runs first, then Calendar Agent.
    Email results are injected into the calendar task for context.
    """
    new_state = dict(state)
    steps = list(state.get("workflow_steps", []))

    # Step 2: Email Agent
    steps.append({"step": 2, "name": "Email Agent", "status": "in_progress",
                  "detail": "Searching and extracting information from emails..."})
    new_state["workflow_steps"] = steps

    email_result = run_email_agent(task=state["email_task"], session=state["session"])

    steps[-1]["status"] = "done"
    steps[-1]["detail"] = f"Email Agent: {email_result.get('response', '')[:100]}..."

    # Step 3: Calendar Agent — enrich calendar task with email findings
    calendar_task_enriched = (
        f"{state['calendar_task']}\n\n"
        f"Email Agent found the following information:\n{email_result.get('response', '')}"
    )
    steps.append({"step": 3, "name": "Calendar Agent", "status": "in_progress",
                  "detail": "Using email information to schedule calendar event..."})

    calendar_result = run_calendar_agent(task=calendar_task_enriched, session=state["session"])

    steps[-1]["status"] = "done"
    steps[-1]["detail"] = f"Calendar Agent: {calendar_result.get('response', '')[:100]}..."

    new_state["email_result"] = email_result
    new_state["calendar_result"] = calendar_result
    new_state["workflow_steps"] = steps
    new_state["requires_confirmation"] = (
        email_result.get("requires_confirmation", False) or
        calendar_result.get("requires_confirmation", False)
    )
    return new_state


def chitchat_node(state: LarviState) -> LarviState:
    """Node: Handle general conversation and Larvi self-description."""
    system_msg = """You are Larvi, an autonomous AI Email and Calendar assistant.
You are friendly, professional, and concise. 
You can manage Gmail and Google Calendar through natural language.
If the user asks what you can do, explain your email and calendar capabilities clearly.
Keep responses short and helpful."""

    def _do_chitchat(model_name: str):
        llm = get_llm(temperature=0.7, model=model_name)
        return llm.invoke([
            SystemMessage(content=system_msg),
            HumanMessage(content=state["user_input"]),
        ])

    response = invoke_llm_with_fallback(_do_chitchat)

    new_state = dict(state)
    new_state["workflow_steps"] = [
        {"step": 1, "name": "Larvi Response", "status": "done", "detail": "Direct response (no agent needed)"}
    ]
    new_state["final_response"] = response.content
    return new_state


# ── Synthesis Node ────────────────────────────────────────────────────────────

def synthesize_response(state: LarviState) -> LarviState:
    """
    Node: Combine Email Agent and Calendar Agent results into a
    single, coherent, natural-language final response.
    """
    # If chitchat already set final_response, skip synthesis
    if state.get("final_response"):
        return state

    intent = state.get("intent", "")
    email_result = state.get("email_result", {})
    calendar_result = state.get("calendar_result", {})

    if intent == "email":
        final = email_result.get("response", "I processed your email request.")
    elif intent == "calendar":
        final = calendar_result.get("response", "I processed your calendar request.")
    elif intent == "multi":
        synthesis_prompt = f"""The user asked: "{state['user_input']}"

Email Agent completed its task and responded:
{email_result.get('response', 'No email result')}

Calendar Agent completed its task and responded:
{calendar_result.get('response', 'No calendar result')}

Write a single, clear, concise combined response that tells the user what was done across both email and calendar. Be natural and professional."""

        def _do_synthesis(model_name: str):
            llm = get_llm(temperature=0.3, model=model_name)
            return llm.invoke([HumanMessage(content=synthesis_prompt)])

        synth_response = invoke_llm_with_fallback(_do_synthesis)
        final = synth_response.content
    else:
        final = "I'm here to help with your emails and calendar!"

    # Mark workflow complete
    steps = list(state.get("workflow_steps", []))
    final_step_num = len(steps) + 1
    steps.append({
        "step": final_step_num,
        "name": "Final Response",
        "status": "done",
        "detail": "Larvi response ready",
    })

    new_state = dict(state)
    new_state["final_response"] = final
    new_state["workflow_steps"] = steps
    return new_state


# ── Build LangGraph ───────────────────────────────────────────────────────────

def build_master_graph() -> StateGraph:
    """Construct and compile the LangGraph workflow graph."""
    graph = StateGraph(LarviState)

    # Add nodes
    graph.add_node("classify", classify_intent)
    graph.add_node("email_node", email_node)
    graph.add_node("calendar_node", calendar_node)
    graph.add_node("multi_node", multi_node)
    graph.add_node("chitchat_node", chitchat_node)
    graph.add_node("synthesize", synthesize_response)

    # Add edges
    graph.add_edge(START, "classify")
    graph.add_conditional_edges("classify", route_intent, {
        "email_node": "email_node",
        "calendar_node": "calendar_node",
        "multi_node": "multi_node",
        "chitchat_node": "chitchat_node",
    })
    graph.add_edge("email_node", "synthesize")
    graph.add_edge("calendar_node", "synthesize")
    graph.add_edge("multi_node", "synthesize")
    graph.add_edge("chitchat_node", "synthesize")
    graph.add_edge("synthesize", END)

    return graph.compile()


# ── Main Entry Point ──────────────────────────────────────────────────────────

# Compile graph once at module load time for reuse
_compiled_graph = None


def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_master_graph()
    return _compiled_graph


def run_master_agent(user_input: str, session: Session) -> dict:
    """
    Main entry point: Run the full Larvi Master Agent workflow.
    
    Args:
        user_input: Natural language instruction from user
        session: Current conversation session with memory
    
    Returns:
        Complete result dict with response, workflow steps, tool calls, etc.
    """
    graph = get_graph()

    initial_state: LarviState = {
        "user_input": user_input,
        "session": session,
        "intent": "",
        "email_task": "",
        "calendar_task": "",
        "email_result": {},
        "calendar_result": {},
        "workflow_steps": [],
        "requires_confirmation": False,
        "pending_confirmation_data": {},
        "final_response": "",
    }

    try:
        final_state = graph.invoke(initial_state)

        # Collect all tool calls from sub-agents
        all_tool_calls = []
        if final_state.get("email_result"):
            all_tool_calls.extend(final_state["email_result"].get("tool_calls", []))
        if final_state.get("calendar_result"):
            all_tool_calls.extend(final_state["calendar_result"].get("tool_calls", []))

        # Determine primary agent used
        intent = final_state.get("intent", "chitchat")
        agent_label = {
            "email": "Email Agent",
            "calendar": "Calendar Agent",
            "multi": "Email Agent + Calendar Agent",
            "chitchat": "Larvi",
        }.get(intent, "Larvi")

        return {
            "response": final_state["final_response"],
            "agent_used": agent_label,
            "intent": intent,
            "workflow_steps": final_state.get("workflow_steps", []),
            "tool_calls": all_tool_calls,
            "requires_confirmation": final_state.get("requires_confirmation", False),
            "working_memory": session.working_memory.to_dict(),
        }

    except Exception as e:
        err_str = str(e)
        if "429" in err_str or "quota" in err_str.lower() or "resourceexhausted" in err_str.lower():
            friendly_msg = "⚠️ Gemini API quota exhausted for today. Please try again tomorrow or add a new API key."
        elif "404" in err_str or "no longer available" in err_str.lower() or "not found for api" in err_str.lower():
            friendly_msg = "⚠️ Gemini API quota exhausted for today. Please try again tomorrow or add a new API key."
        else:
            friendly_msg = f"I encountered an issue while processing your request: {err_str}. Please try again."

        return {
            "response": friendly_msg,
            "agent_used": "Larvi",
            "intent": "error",
            "workflow_steps": [{"step": 1, "name": "Rate Limit / Notice", "status": "error", "detail": friendly_msg}],
            "tool_calls": [],
            "requires_confirmation": False,
            "working_memory": {},
        }
