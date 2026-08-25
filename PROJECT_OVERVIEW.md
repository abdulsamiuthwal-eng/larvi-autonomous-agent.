# 🚀 Larvi — Autonomous Email & Calendar AI Agent
### Complete Master Project Overview & Architecture Guide

> **Purpose of this file:** Whenever you open a new AI chat or onboarding session in Antigravity / Cursor / VS Code, this document provides 100% complete, authoritative context of the system architecture, features, tools, memory engine, file structure, API endpoints, and execution workflows.

---

## 📌 1. Project Summary & Identity

* **Project Title:** Larvi — Autonomous Email & Calendar AI Agent
* **Domain:** DevForge Internship Final Capstone Project
* **Objective:** Build an autonomous multi-agent AI system capable of understanding natural-language instructions, routing to specialized agents, executing real operations via connected APIs (Gmail & Google Calendar), maintaining conversation context/memory, and returning synthesized responses.
* **Core Philosophy:** Beyond a standard chatbot — Larvi is an autonomous multi-agent orchestrator with real API integrations, state tracking, and safety confirmation mechanisms.

---

## 🏗️ 2. Core Multi-Agent Architecture

```
                                  User Input (Text or Voice)
                                              │
                                              ▼
                              ┌─────────────────────────────────┐
                              │    Larvi Master Agent Node      │
                              │   (LangGraph StateGraph Engine) │
                              └───────────────┬─────────────────┘
                                              │
                                              ▼
                              ┌─────────────────────────────────┐
                              │    Intent Classifier Node       │
                              │ (email | calendar | multi | ...) │
                              └───────────────┬─────────────────┘
                                              │
                 ┌────────────────────────────┼───────────────────────────┐
                 ▼                            ▼                           ▼
        ┌───────────────────┐       ┌───────────────────┐       ┌───────────────────┐
        │    Email Agent    │       │  Calendar Agent   │       │  Multi-Agent Node │
        │ (LangChain ReAct) │       │ (LangChain ReAct) │       │ (Email ➔ Calendar)│
        └────────┬──────────┘       └─────────┬─────────┘       └─────────┬─────────┘
                 │                            │                           │
                 ▼                            ▼                           ▼
        ┌───────────────────┐       ┌───────────────────┐       ┌───────────────────┐
        │    Email Tools    │       │  Calendar Tools   │       │ Chained Pipeline  │
        │ (Gmail API Client)│       │(Google Cal Client)│       │  State Resolution │
        └────────┬──────────┘       └─────────┬─────────┘       └─────────┬─────────┘
                 │                            │                           │
                 └────────────────────────────┼───────────────────────────┘
                                              │
                                              ▼
                              ┌─────────────────────────────────┐
                              │   Response Synthesis Node       │
                              │  (Context & Memory Injection)   │
                              └───────────────┬─────────────────┘
                                              │
                                              ▼
                              ┌─────────────────────────────────┐
                              │  Final Formatted Output ➔ User  │
                              │ (SSE Real-Time Streaming / Cards│
                              └─────────────────────────────────┘
```

---

## 🛠️ 3. Tech Stack & Dependencies

| Layer | Component / Technology | Role |
| :--- | :--- | :--- |
| **LLM Model** | Google Gemini (`gemini-2.5-flash`, `gemini-2.5-flash-lite`, `gemini-2.0-flash`) | Core reasoning, intent classification, agent thinking with 1500 RPD free tier & sub-second latency |
| **Resilience Engine** | Automatic Multi-Model Fallback Cascade (`backend/agents/llm_factory.py`) | Prevents 429 quota exhaustion by cycling through ordered models |
| **Agent Orchestration** | LangGraph (`StateGraph`) + LangChain ReAct | Graph-based multi-agent routing & subtask coordination |
| **Backend Framework** | Python 3.11/3.12 + FastAPI + Uvicorn | High-performance REST & SSE streaming server |
| **Email Integration** | Google Cloud Gmail API (`google-api-python-client`) | Real email search, read, draft, send, reply |
| **Calendar Integration** | Google Cloud Calendar API | Real schedule viewing, availability check, event CRUD |
| **Auth System** | Google OAuth 2.0 (`google-auth-oauthlib`) | Desktop OAuth flow & Web redirect flow with auto token refresh |
| **Memory System** | SQLite (`larvi.db`) + Custom In-Memory Context Engine | Multi-turn entity resolution ("it", "that meeting") & persistent session history |
| **Frontend UI** | HTML5, Vanilla CSS3 (Curated Design System), Vanilla JS (ES6) | Responsive multi-view UI (Chat, Inbox, Calendar, Profile, Settings) |
| **Speech-to-Text** | Web Speech API (`SpeechRecognition`) | Real-time voice microphone input in chat bar |
| **Stream Control** | `AbortController` + Fetch API | Instant Stop Response generation button |

---

## 📂 4. Project Directory Structure

```
Final Exam/
├── GEMINI.md                    # Quick workspace rules and guidelines for AI coding agents
├── PROJECT_OVERVIEW.md          # 🌟 Master documentation for new chats & developers
├── PROJECT_REPORT.md            # Comprehensive project evaluation and implementation report
├── README.md                    # Public documentation with setup & usage guides
├── .gitignore                   # Ignores .env, credentials.json, token.json, venv
├── requirements.txt             # Python dependencies
├── vercel.json                  # Production Vercel deployment configuration
│
├── backend/
│   ├── main.py                  # FastAPI server entry point (Routes: /chat, /chat/stream, /auth, /health, /sessions, /views)
│   ├── config.py                # Pydantic/dotenv settings manager & environment validator
│   ├── auth_setup.py            # Quick CLI script to run desktop OAuth login & generate token.json
│   ├── requirements.txt         # Backend Python dependencies
│   ├── .env                     # Local environment file (GEMINI_API_KEY, GOOGLE_CLIENT_ID, etc.)
│   ├── .env.example             # Template for environment configuration
│   ├── credentials.json         # Google Cloud OAuth Desktop client credentials
│   ├── token.json               # Generated user OAuth access/refresh token
│   │
│   ├── agents/                  # 🧠 AI Agent Modules
│   │   ├── __init__.py
│   │   ├── master_agent.py      # LangGraph StateGraph, Intent Classifier, Multi-Node Orchestrator
│   │   ├── llm_factory.py       # Resilient LLM factory with automated fallback cascade
│   │   ├── email_agent.py       # ReAct agent managing Gmail operations & live datetime injection
│   │   └── calendar_agent.py    # ReAct agent managing Calendar schedule, availability, & live datetime
│   │
│   ├── tools/                   # ⚙️ LangChain Tool Definitions
│   │   ├── __init__.py
│   │   ├── email_tools.py       # 6 Gmail tools: search, read, recent, draft, send, reply
│   │   └── calendar_tools.py    # 6 Calendar tools: get, search, freebusy, create, update, delete (with _parse_int_arg)
│   │
│   ├── services/                # 🌐 Real Google API Wrappers
│   │   ├── __init__.py
│   │   ├── gmail_service.py     # Authenticated Gmail API calls & MIME email parsers
│   │   └── gcal_service.py      # Authenticated Google Calendar API calls & timezone parser
│   │
│   ├── memory/                  # 💾 Context & Working Memory
│   │   ├── __init__.py
│   │   └── context_manager.py   # SQLite database engine + SessionManager & WorkingMemory
│   │
│   └── auth/                    # 🔐 OAuth Authentication
│       ├── __init__.py
│       └── google_oauth.py      # OAuth 2.0 flow, token persistence, picture/profile attributes, auto-refresh
│
└── frontend/                    # 🎨 Editorial Glassmorphic Web Interface
    ├── index.html               # Multi-view app shell (Chat, Inbox, Calendar, Profile, Settings)
    ├── css/
    │   ├── main.css             # Design tokens, typography, CSS reset, themes
    │   ├── layout.css           # Responsive layout grid, topbar, sidebars
    │   ├── chat.css             # Chat bubbles, widgets, chips, markdown styling
    │   ├── sidebar.css          # Chat history hub, mic button, stop button, status indicators
    │   ├── views.css            # Dedicated Views (Inbox list, Calendar schedule, Profile cards, Settings)
    │   └── components.css       # Modals, confirmation dialogs, toast notifications
    │
    └── js/
        ├── app.js               # App bootstrap, Voice mic, Stop button, Views router, Profile management
        ├── chat.js              # Chat UI renderer, interactive widgets (Email cards, Calendar badges)
        ├── workflow.js          # Live workflow execution stepper & tool activity feed
        ├── api.js               # Backend HTTP & SSE streaming API client (with AbortSignal support)
        └── context.js           # Frontend state manager (Working memory & Auth sync, Avatar overrides)
```

---

## ⚡ 5. Detailed Capabilities & Tools

### A. Email Agent (`backend/tools/email_tools.py`)
1. `search_emails(query, max_results)` — Searches inbox with query operators (`from:`, `subject:`, `after:`).
2. `read_email(message_id)` — Fetches complete email body, headers, sender, date, snippet.
3. `get_recent_emails(count)` — Retrieves the newest emails from user inbox.
4. `create_draft(to, subject, body)` — Creates a safe draft in Gmail without sending.
5. `send_email(to, subject, body)` — Sends a real email (requires user confirmation).
6. `reply_to_email(message_id, body)` — Sends a threaded reply to an existing email.

### B. Calendar Agent (`backend/tools/calendar_tools.py`)
1. `get_events(days_ahead)` — Lists upcoming schedule for the next N days (robust integer parsing for strings/JSON).
2. `search_events(query)` — Searches calendar events by title/topic.
3. `check_availability(date, start_time, end_time)` — Checks Google Free/Busy API for scheduling conflicts.
4. `create_event(title, date, start_time, end_time, description, attendees)` — Schedules a new event in Google Calendar.
5. `update_event(event_id, title, date, start_time, end_time, description)` — Moves or reschedules an existing event.
6. `delete_event(event_id)` — Cancels and removes an event from calendar.

### C. Multi-Agent Workflows
1. **Email ➔ Calendar Pipeline:**
   * User: *"Find the email from Ahmed about the project meeting and add it to my calendar."*
   * Step 1: Master Agent routes to Email Agent.
   * Step 2: Email Agent searches for Ahmed's email, extracts date (`2026-08-26`), time (`3:00 PM`), and topic.
   * Step 3: Master Agent forwards extracted details to Calendar Agent.
   * Step 4: Calendar Agent checks free/busy availability and creates the event in Google Calendar.
   * Step 5: Master Agent returns a final combined confirmation to the user.

---

## 🎙️ 6. Real-Time Interaction Features

1. **Voice Input (Microphone):**
   - Click the microphone icon in the chat input bar to speak prompts directly.
   - Built with the native browser Web Speech API. Real-time transcript fills the textarea automatically.

2. **Stop Response Generation Button:**
   - When the agent is streaming or executing tools, the Send button turns into a pulsing red Stop Button.
   - Clicking it triggers an `AbortController` signal, instantly stopping generation and resetting UI state.

3. **User Profile System:**
   - Custom Profile Picture upload (stored locally and synced across header and sidebar).
   - Personal profile information edit form (Name, Email, Role) with instant save.
   - Change Password form with validation.
   - Multi-point Logout buttons (Top Header, Left Sidebar footer, Profile view).

---

## 🧠 7. Context & Working Memory System

Located in [`backend/memory/context_manager.py`](file:///d:/DEVFORGE_INTERNSHIP/Final%20Exam/backend/memory/context_manager.py):

* **Entity Resolution:**
  When a user asks:
  1. User: *"Find my meeting with Ali tomorrow."* ➔ Larvi finds: `Project Review at 3:00 PM (ID: evt_123)`.
  2. User: *"Move it to 5 PM."* ➔ Larvi knows `"it"` refers to `Project Review` and updates `evt_123`.
* **State Tracked:**
  * `last_email_id`, `last_email_subject`, `last_email_from`
  * `last_event_id`, `last_event_title`, `last_event_date`, `last_event_start`, `last_event_end`
  * `active_person`
  * `pending_action` (for safety confirmation dialogs)

---

## 🚀 8. Quick Commands for Running the Project

### Start Backend:
```bash
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

### Start Frontend:
```bash
cd frontend
python -m http.server 5500
```
> Or open `frontend/index.html` via VS Code Live Server (`http://localhost:5500`).

### Google Account OAuth Login (One-Time Setup):
```bash
cd backend
python auth_setup.py
```
> Opens browser for granting Gmail + Calendar permissions and generates `token.json`.

### Deploy to Production (Vercel):
```bash
npx vercel --prod --yes
```

---

## 🌐 9. API Endpoints Reference

| Endpoint | Method | Purpose |
| :--- | :---: | :--- |
| `/chat` | `POST` | Primary synchronous chat endpoint (Master Agent orchestration) |
| `/chat/stream` | `POST` | Real-time Server-Sent Events (SSE) streaming with live workflow steps |
| `/health` | `GET` | System health check (Gemini config & Google auth status) |
| `/auth/status` | `GET` | Returns whether Gmail & Calendar tokens are active for a session |
| `/auth/login` | `GET` | Initiates Web OAuth flow & redirects user to Google Consent Screen |
| `/auth/callback` | `GET` | Google OAuth callback handler that binds token to user session |
| `/sessions` | `GET` | Lists all saved conversations from SQLite database |
| `/sessions/{id}` | `GET` | Loads conversation history for a specific session |
| `/sessions/{id}` | `DELETE` | Deletes a conversation session from SQLite database |
| `/views/inbox` | `GET` | Fetches email list for Mail Inbox view |
| `/views/calendar` | `GET` | Fetches events list for Calendar Schedule view |
| `/docs` | `GET` | Interactive Swagger API documentation |

---
*Created for Larvi AI Assistant — DevForge Final Capstone Project.*
