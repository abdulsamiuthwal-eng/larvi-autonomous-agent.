# 🤖 Larvi — Autonomous Email & Calendar AI Executive Assistant

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.0.30-blue.svg?logo=langchain&logoColor=white)](https://github.com/langchain-ai/langgraph)
[![Gemini](https://img.shields.io/badge/Google%20Gemini-Flash-orange.svg?logo=google&logoColor=white)](https://aistudio.google.com/)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57.svg?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Vercel](https://img.shields.io/badge/Deploy-Vercel-black.svg?logo=vercel&logoColor=white)](https://vercel.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> **Larvi** is an enterprise-grade autonomous multi-agent AI assistant designed to automate email communication and calendar scheduling via natural language interactions. Built on **FastAPI**, **LangGraph**, **Google Gemini**, and **Google Cloud APIs (Gmail & Calendar)**.

---

## ✨ Key Features

* 🤖 **Master Multi-Agent Orchestrator**: LangGraph StateGraph state machine that routes queries across Email, Calendar, and Hybrid sub-agents.
* ⚡ **Multi-Model Auto-Fallback Engine**: Zero-quota disruption cascade cycling through `gemini-3.5-flash`, `gemini-2.5-flash-lite`, `gemini-3.7-flash`, and `gemini-3.6-flash`.
* 💬 **Gemini & ChatGPT-Style Multi-Chat Sidebar**: Persistent conversation histories, automatic conversation naming, and 1-click session switching powered by a persistent **SQLite Database**.
* 🌊 **Real-Time Word-by-Word Streaming (SSE)**: Live token generation with real-time workflow step indicators and tool execution feeds.
* ✉️ **Rich Interactive Visual Cards**:
  * **Interactive Email Draft Cards**: Recipient, Subject, and Body preview with 1-click **Send Email** and **Discard** actions.
  * **Calendar Event Badges**: Date badges, conflict indicators, and 1-click **Add to Calendar** and **Reschedule** actions.
* 🔒 **Multi-User Google OAuth 2.0**: Secure per-session Google Workspace connection for Gmail and Google Calendar.
* 🛡️ **Human-in-the-Loop Safety**: Confirmation dialogs for destructive actions (sending emails, deleting events).

---

## 🏛️ System Architecture

```
User Input ──▶ FastAPI (/chat/stream) ──▶ Master Orchestrator (LangGraph)
                                                │
                 ┌──────────────────────────────┼──────────────────────────────┐
                 ▼                              ▼                              ▼
        [Email Sub-Agent]              [Calendar Sub-Agent]          [Chitchat Engine]
        * read_emails                  * check_availability         * Context & Greetings
        * search_emails                * create_event                
        * draft_email                  * get_upcoming_events         
        * send_email                   * reschedule_event            
        * reply_to_email               * delete_event                
        * summarize_unread             * find_free_slots             
                 │                              │
                 └──────────────┬───────────────┘
                                ▼
                   Google Cloud APIs (OAuth 2.0)
                                │
                                ▼
                 SQLite Persistent DB (larvi.db)
                                │
                                ▼
               SSE Real-Time Stream to Client UI
```

---

## ⚡ 1-Minute Quick Start

### 1. Clone & Setup Environment
```bash
git clone https://github.com/your-username/larvi-autonomous-agent.git
cd larvi-autonomous-agent

# Create Python virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `backend/.env` and add your **Gemini API Key**:
```bash
cp .env.example backend/.env
```
Edit `backend/.env`:
```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.5-flash
```

### 3. Start Backend & Frontend
In Terminal 1 (Backend):
```bash
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

In Terminal 2 (Frontend):
```bash
cd frontend
python -m http.server 5500
```

Open your browser at: **`http://localhost:5500`** 🚀

---

## 🚀 1-Click Free Cloud Deployment (Vercel)

Deploy both the Frontend and FastAPI Backend to **Vercel** with a single command:

```bash
# Install Vercel CLI (if not already installed)
npm install -g vercel

# Deploy to production
vercel --prod
```

Set your `GEMINI_API_KEY` in the Vercel Project Environment Variables dashboard.

---

## 🧪 Evaluator & Demo Test Prompts

Try these natural language prompts in the chat interface to test all system capabilities:

| Category | Test Prompt | Description |
|---|---|---|
| **Chitchat** | `Hello! Who are you and how can you help me?` | Tests master orchestrator and intent classification. |
| **Email Summary** | `Show me my latest emails` / `Summarize my unread emails` | Tests Gmail ReAct agent reading and summarizing inbox threads. |
| **Email Drafting** | `Draft an email to client@example.com about our project launch` | Tests draft generation and renders the interactive Draft Card. |
| **Calendar Check** | `Am I free tomorrow at 3 PM?` | Tests Google Calendar Freebusy API for conflict detection. |
| **Calendar Schedule**| `Schedule a team sync tomorrow at 10 AM for 45 minutes` | Tests calendar event creation and renders the Event Card. |
| **Hybrid Workflow** | `Find the email from Alex and schedule a meeting based on his time` | Tests multi-agent delegation (Gmail search ➔ Calendar creation). |
| **Memory Recall** | `Remember my budget code is B-900` then `What is my budget code?` | Tests working memory slot filling and context recall. |

---

## 📁 Repository Structure

```
larvi-autonomous-agent/
├── backend/
│   ├── agents/
│   │   ├── master_agent.py      # LangGraph StateGraph orchestrator
│   │   ├── email_agent.py       # Gmail ReAct sub-agent
│   │   ├── calendar_agent.py    # Google Calendar ReAct sub-agent
│   │   └── llm_factory.py       # Multi-model fallback cascade manager
│   ├── tools/
│   │   ├── email_tools.py       # 6 Gmail integration tools
│   │   └── calendar_tools.py    # 6 Google Calendar integration tools
│   ├── memory/
│   │   ├── context_manager.py   # Multi-session memory & context manager
│   │   └── db.py                # SQLite database storage & session history
│   ├── auth/
│   │   └── google_oauth.py      # Google OAuth 2.0 flow & token management
│   ├── config.py                # Pydantic environment configuration
│   ├── main.py                  # FastAPI application & REST/SSE endpoints
│   └── requirements.txt         # Python dependencies
├── frontend/
│   ├── css/                     # Warm Editorial Design System styles
│   │   ├── main.css             # CSS variables & typography tokens
│   │   ├── layout.css           # 3-column responsive layout
│   │   ├── chat.css             # Message bubbles & interactive widgets
│   │   └── sidebar.css          # Multi-chat sidebar & agent status docks
│   ├── js/
│   │   ├── app.js               # Main application controller & session switch
│   │   ├── api.js               # REST & SSE communication layer
│   │   ├── chat.js              # Live streaming renderer & UI widgets
│   │   ├── context.js           # Client-side session state
│   │   └── workflow.js          # Stepper & action feed updater
│   └── index.html               # Clean semantic HTML5 application shell
├── PROJECT_REPORT.md            # Comprehensive Capstone Examination Report
├── vercel.json                  # Vercel 1-click cloud deployment config
├── .env.example                 # Clean environment variables template
├── .gitignore                   # Secure credential & artifact exclusion rules
└── README.md                    # Project documentation & evaluator guide
```

---

## 📄 License
This project is open-source and available under the [MIT License](LICENSE).
