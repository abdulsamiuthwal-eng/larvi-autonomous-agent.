# 📘 LARVI — Autonomous Multi-Agent AI Executive Assistant
## Comprehensive Project & Technical Architecture Report
**Final Capstone Examination & Evaluation Documentation**

---

## 1. Executive Summary

**Larvi** is an enterprise-grade, autonomous multi-agent AI executive assistant designed to automate email communication and calendar scheduling via natural language interactions. Built on **FastAPI**, **LangGraph**, **Google Gemini models**, and official **Google Cloud APIs (Gmail & Google Calendar)**, Larvi orchestrates complex multi-step workflows with real-time feedback, persistent session memory, human-in-the-loop safety guardrails, and rich interactive visual components.

```
+─────────────────────────────────────────────────────────────────────────────+
|                                LARVI ECOSYSTEM                              |
|                                                                             |
|  +-----------------------------------------------------------------------+  |
|  |                     Client Interface (Web Browser)                    |  |
|  |  * Multi-Chat Sidebar     * Real-Time Token Streaming (SSE)           |  |
|  |  * Interactive Draft Card * Calendar Conflict Widget  * Status Docks  |  |
|  +-----------------------------------------------------------------------+  |
|                                     ▲                                       |
|                        HTTP / REST / SSE Stream (port 8000)                 |
|                                     ▼                                       |
|  +-----------------------------------------------------------------------+  |
|  |                     Master Orchestration Agent (LangGraph)            |  |
|  |  * Intent Classifier       * Fallback Cascade Engine                  |  |
|  |  * StateGraph Flow Control * Multi-Agent Routing & Response Synthesis|  |
|  +-----------------------------------------------------------------------+  |
|                     ▲                                 ▲                     |
|         Delegate    │                                 │   Delegate          |
|                     ▼                                 ▼                     |
|  +---------------------------+       +-----------------------------------+  |
|  |      Email Sub-Agent      |       |       Calendar Sub-Agent          |  |
|  | * 6 Gmail ReAct Tools     |       | * 6 Calendar ReAct Tools          |  |
|  | * Search, Draft, Send,    |       | * Freebusy Check, Schedule,       |  |
|  |   Summarize, Reply        |       |   Reschedule, Delete, Agenda      |  |
|  +---------------------------+       +-----------------------------------+  |
|               │                                       │                     |
|               ▼                                       ▼                     |
|  +-----------------------------------------------------------------------+  |
|  |                 Google Cloud APIs & OAuth 2.0 Security Layer          |  |
|  |  * Per-Session Tokens     * Automatic Token Refresh                   |  |
|  +-----------------------------------------------------------------------+  |
|                                     ▲                                       |
|                                     ▼                                       |
|  +-----------------------------------------------------------------------+  |
|  |                 Persistent SQLite Database (larvi.db)                 |  |
|  |  * Sessions Table         * Messages Table      * Working Memory      |  |
|  +-----------------------------------------------------------------------+  |
+─────────────────────────────────────────────────────────────────────────────+
```

---

## 2. Problem Statement & Design Objectives

Modern knowledge workers lose 2.5+ hours daily triaging emails, resolving meeting conflicts, and coordinating schedules. Existing solutions suffer from:
1. **Single-turn limitations**: Incapable of reasoning across multiple steps or remembering context across messages.
2. **Fragile LLM rate limits**: API failure when individual model daily quotas are exhausted.
3. **Lack of UX responsiveness**: Blank loading screens during complex tool execution.
4. **Ephemeral memory**: Loss of conversation context upon browser reload.

### Design Objectives
* **Zero-Interruption Multi-Model Cascade**: Automatic fallback across `gemini-3.5-flash`, `gemini-2.5-flash-lite`, `gemini-3.7-flash`, and `gemini-3.6-flash`.
* **Sub-50ms Initial Feedback**: Token-by-token live streaming over Server-Sent Events (SSE).
* **Multi-Chat Persistent SQLite Store**: Permanent conversation histories and working memory slots.
* **Safety First**: Human-in-the-loop confirmation for destructive or external actions (e.g. sending emails or deleting events).

---

## 3. Detailed Component Architecture

### 3.1 Master Orchestration Agent (`backend/agents/master_agent.py`)
The Master Agent uses a LangGraph `StateGraph` state machine to direct user queries:
1. **Intent Classification (`classify_intent`)**: Classifies the query into `email`, `calendar`, `hybrid`, `chitchat`, or `unknown`.
2. **Conditional Routing (`route_intent`)**:
   - `chitchat` / `unknown` &rarr; `chitchat_node`
   - `email` &rarr; `email_agent_node`
   - `calendar` &rarr; `calendar_agent_node`
   - `hybrid` &rarr; sequential execution of both sub-agents.
3. **Response Synthesis (`synthesize_response`)**: Consolidates results from sub-agents, formats user-friendly output, and populates `workflow_steps` and `tool_calls`.

### 3.2 Sub-Agents & Tool Registries
* **Email Agent (`backend/agents/email_agent.py`)**:
  - `read_emails`: Fetches latest emails with sender, subject, date, snippet, and thread IDs.
  - `search_emails`: Full-text search with Gmail query syntax (e.g., `from:boss subject:urgent`).
  - `draft_email`: Creates Gmail drafts with confirmation requirements.
  - `send_email`: Dispatches emails with security checks.
  - `reply_to_email`: Thread-aware contextual replies.
  - `summarize_unread`: Aggregates unread message threads.

* **Calendar Agent (`backend/agents/calendar_agent.py`)**:
  - `check_availability`: Queries Google Calendar `freebusy` API to detect scheduling conflicts.
  - `create_event`: Creates new calendar events with date/time, summary, description, and attendees.
  - `get_upcoming_events`: Lists events within customizable time horizons (today, tomorrow, next 7 days).
  - `reschedule_event`: Modifies start/end times with conflict validation.
  - `delete_event`: Removes events with safety verification.
  - `find_free_slots`: Discovers available meeting intervals within specified working hours.

### 3.3 Zero-Cost SQLite Persistent Database (`backend/memory/db.py`)
* File-based relational database (`backend/larvi.db`) initialized automatically on startup.
* **Schema**:
  - `sessions`: `(id TEXT PRIMARY KEY, title TEXT, created_at TIMESTAMP, updated_at TIMESTAMP, working_memory_json TEXT)`
  - `messages`: `(id INTEGER PRIMARY KEY, session_id TEXT, role TEXT, content TEXT, agent_used TEXT, intent TEXT, tool_calls_json TEXT, created_at TIMESTAMP)`
* REST API endpoints: `GET /sessions`, `GET /sessions/{id}`, `POST /sessions`, `DELETE /sessions/{id}`.

### 3.4 Multi-Model Fallback Engine (`backend/agents/llm_factory.py`)
To prevent preview quota exhaustion (e.g. 20 req/day limits on preview models), the LLM Factory cycles through:
1. `gemini-3.5-flash` (Primary fast stable model)
2. `gemini-2.5-flash-lite` (High-speed secondary fallback)
3. `gemini-3.7-flash` (Advanced reasoning fallback)
4. `gemini-3.6-flash` (Preview fallback)

---

## 4. Frontend & User Experience Architecture

1. **Modern Layout**: 3-column responsive layout built with clean CSS, warm editorial tokens (no harsh darks or default blues), and 8pt spatial grid.
2. **Gemini / ChatGPT Style Multi-Chat Sidebar**:
   - Auto-generated conversation titles derived from the first user prompt.
   - 1-click chat session switching with instant message history restore.
   - Dynamic `+ New Chat` button and conversation deletion.
3. **Live SSE Streaming Renderer**:
   - Yields token words with smooth visual typing indicators.
   - Displays real-time step trackers (`workflow_step`) and tool execution pills (`tool_call`).
4. **Rich Interactive UI Widgets**:
   - **Email Draft Card**: Displays recipient, subject, preview body, and 1-click action buttons (✉️ **Send Email**, 🗑️ **Discard**).
   - **Calendar Event Card**: Displays date badges, conflict status, and interactive buttons (✅ **Add to Calendar**, 🕒 **Reschedule**).

---

## 5. Security, OAuth 2.0 & Privacy

* **Zero Hardcoded Secrets**: All sensitive keys reside in `.env` (strictly excluded by `.gitignore`).
* **Session-Isolated Authentication**: Each user session generates its own OAuth token file in `backend/tokens/{session_id}.json`.
* **Scope Minimization**: Limited to `gmail.modify` and `calendar` without administrative or account-takeover scopes.
* **Human-in-the-Loop Confirmation**: Destructive actions (sending emails, deleting calendar events) require explicit user approval before execution.

---

## 6. Evaluation Test Suite & Verification Matrix

| Test Scenario | Input Prompt | Expected System Behavior | Result |
|---|---|---|---|
| **Chitchat / General** | *"Hello, who are you and what can you do?"* | Master Agent recognizes `chitchat`, introduces capabilities without triggering tools. | **PASSED** ✅ |
| **Email Summarization** | *"Summarize my unread emails"* | Email Agent calls `summarize_unread` or `read_emails`, returns structured summaries. | **PASSED** ✅ |
| **Email Drafting** | *"Draft an email to john@example.com about the project deadline"* | Email Agent calls `draft_email`, generates interactive Draft Card with Send/Discard buttons. | **PASSED** ✅ |
| **Calendar Freebusy** | *"Am I free tomorrow at 3 PM?"* | Calendar Agent unpacks ISO date, calls `check_availability`, returns clear availability verdict. | **PASSED** ✅ |
| **Calendar Scheduling** | *"Schedule a meeting with Sarah tomorrow at 10 AM for 30 minutes"* | Calendar Agent calls `create_event`, presents interactive event badge widget. | **PASSED** ✅ |
| **Hybrid Cross-Domain** | *"Find the email from Alex and schedule a meeting based on his proposed time"* | Master Agent routes to Email Agent (search), extracts date/time, then routes to Calendar Agent. | **PASSED** ✅ |
| **Memory Recall** | *"Remember my team name is Alpha. [Followup]: What is my team name?"* | Working memory stores key-value pair, correctly retrieves value in followup turn. | **PASSED** ✅ |
| **Multi-Chat Persistence** | *Create 2 chats, reload browser tab* | SQLite database retains both chats, sidebar lists titles, clicking loads full message history. | **PASSED** ✅ |

---

## 7. Conclusion & Deliverables

Larvi meets and exceeds all project requirements for an autonomous multi-agent AI system. It demonstrates production-level engineering through:
- **Resilient AI architecture** (LangGraph orchestration + multi-model fallback).
- **Sub-second interactive UX** (SSE streaming + rich interactive action cards).
- **Reliable persistent storage** (SQLite session history + multi-chat sidebar).
- **1-Click Free Deployment** (Vercel serverless + Render support).
