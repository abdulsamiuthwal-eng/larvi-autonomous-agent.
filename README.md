<div align="center">

# 🤖 Larvi — Autonomous Email & Calendar AI Agent

<img src="https://img.shields.io/badge/Status-Live%20%26%20Production%20Ready-brightgreen?style=for-the-badge&logo=vercel" alt="Status">
<img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
<img src="https://img.shields.io/badge/FastAPI-0.110+-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
<img src="https://img.shields.io/badge/Google%20Gemini-2.5%20Flash-4285F4?style=for-the-badge&logo=google&logoColor=white" alt="Gemini">
<img src="https://img.shields.io/badge/LangGraph-Agentic-FF6B35?style=for-the-badge" alt="LangGraph">
<img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="License">

<br/><br/>

**Larvi** is a production-grade, fully autonomous AI agent that reads, drafts, sends emails and schedules calendar events — all through natural language. No forms. No clicks. Just conversation.

<br/>

[![🚀 Live Demo](https://img.shields.io/badge/🚀%20Live%20Demo-Visit%20Larvi%20Now-FF4500?style=for-the-badge&logoColor=white)](https://larvi-autonomous-agent.vercel.app)

<br/>

![Larvi Banner](https://img.shields.io/badge/Larvi%20AI-Email%20%26%20Calendar%20Agent-gradient?style=for-the-badge)

</div>

---

## ✨ What Larvi Can Do

| Capability | Description |
|---|---|
| 📧 **Read Emails** | Fetch, summarize, and search your Gmail inbox via natural language |
| ✍️ **Compose & Draft** | AI-written email drafts with professional tone and context-aware content |
| 📤 **Send Emails** | Send emails directly to recipients with a single command |
| 💬 **Reply Intelligently** | Read threads and generate contextual replies |
| 📅 **Schedule Meetings** | Create Google Calendar events with conflict detection |
| 🔍 **Check Availability** | Real-time free/busy analysis before scheduling |
| 🔄 **Reschedule Events** | Update or reschedule meetings naturally |
| 🗑️ **Delete Events** | Safe deletion with explicit user confirmation required |
| 🎤 **Voice Input** | Speak your commands via Web Speech API |
| ⏹️ **Stop Streaming** | Cancel in-flight AI responses with one click |
| 💾 **Multi-Turn Memory** | Remembers context across conversation turns via SQLite |
| 👤 **User Profiles** | Custom avatar, display name, and role management |

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     LARVI SYSTEM ARCHITECTURE                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   Frontend (Vanilla HTML/CSS/JS)                                │
│   ├── Chat UI with SSE streaming                                │
│   ├── Email widget renderer                                     │
│   ├── Calendar event cards                                      │
│   ├── Voice input (Web Speech API)                              │
│   └── Responsive mobile-first design                            │
│                                           │                     │
│                                     HTTP/SSE                    │
│                                           │                     │
│   FastAPI Backend                         ▼                     │
│   ├── /chat/stream   ──────────► Master Orchestrator            │
│   ├── /auth/login                         │                     │
│   └── /auth/callback          ┌──────────┴──────────┐          │
│                                │                     │          │
│                         Email Agent          Calendar Agent     │
│                         (LangGraph)          (LangGraph)        │
│                                │                     │          │
│                         Gmail Tools          GCal Tools         │
│                         (send/read/          (create/check/     │
│                          draft/reply)         delete/update)    │
│                                │                     │          │
│                         ┌──────┴─────────────────────┘          │
│                         │                                       │
│                    LLM Factory                                  │
│                    Gemini 2.5 Flash → Flash Lite → Fallback     │
│                         │                                       │
│                    Memory Engine                                │
│                    SQLite + Working Memory Context              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🧠 Technical Stack

### Backend
| Component | Technology |
|---|---|
| **API Framework** | FastAPI + Uvicorn (async, streaming) |
| **AI Orchestration** | LangGraph StateGraph + ReAct Agent pattern |
| **LLM Provider** | Google Gemini 2.5 Flash / Flash-Lite (1500 RPD free tier) |
| **LLM Framework** | LangChain (`langchain-google-genai`) |
| **Email Integration** | Gmail API via Google OAuth 2.0 |
| **Calendar Integration** | Google Calendar API via Google OAuth 2.0 |
| **Session Memory** | SQLite + in-memory working memory context |
| **Streaming** | Server-Sent Events (SSE) for real-time responses |
| **Authentication** | Google OAuth 2.0 PKCE Web Flow |

### Frontend
| Component | Technology |
|---|---|
| **Structure** | Semantic HTML5 |
| **Styling** | Vanilla CSS (glassmorphism, dark mode, responsive) |
| **Logic** | Vanilla JavaScript (ES6+, no frameworks) |
| **Streaming** | SSE with AbortController for stop-response |
| **Voice Input** | Web Speech API |
| **Rendering** | Dynamic email/calendar widget builder |

---

## 🔐 Security Architecture

> **No secrets are ever committed to this repository.**

| Security Layer | Implementation |
|---|---|
| **Secrets Management** | All credentials via environment variables only |
| **OAuth Tokens** | Stored server-side only, never exposed to frontend |
| **`.gitignore`** | `.env`, `credentials.json`, `token.json`, `*.db` all excluded |
| **`.vercelignore`** | Sensitive files excluded from Vercel deployment artifacts |
| **Authorized Users** | Google OAuth app in "Testing" mode — explicit user allowlist |
| **CORS Policy** | Restricted to configured `FRONTEND_URL` only |
| **Session Isolation** | Per-user session IDs with isolated credential storage |
| **No Hardcoded Keys** | Zero secrets in source code — verified pre-commit |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- A Google Cloud Project with Gmail API + Calendar API enabled
- A Google Gemini API key (free at [aistudio.google.com](https://aistudio.google.com))

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/abdulsamiuthwal-eng/larvi-autonomous-agent.git
cd larvi-autonomous-agent
```

### 2️⃣ Set Up Environment Variables

```bash
cd backend
cp .env.example .env
# Edit .env and fill in your actual values
```

Required variables:

```env
GEMINI_API_KEY=your_gemini_api_key
GOOGLE_CLIENT_ID=your_google_oauth_client_id
GOOGLE_CLIENT_SECRET=your_google_oauth_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback
SECRET_KEY=your_random_secret_key
```

### 3️⃣ Install Python Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 4️⃣ Set Up Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create an **OAuth 2.0 Client ID** → Web Application type
3. Add Authorized Redirect URI: `http://localhost:8000/auth/callback`
4. Download `credentials.json` and place it inside `backend/`
5. Enable **Gmail API** and **Google Calendar API** in your project

### 5️⃣ Run the Desktop OAuth Flow (First Time)

```bash
cd backend
python auth_setup.py
```

This opens a browser, lets you authorize the app, and saves your token locally.

### 6️⃣ Start the Backend Server

```bash
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

### 7️⃣ Start the Frontend Server

```bash
cd frontend
python -m http.server 5500
```

### 8️⃣ Open the App

Navigate to: **[http://localhost:5500](http://localhost:5500)**

---

## 🌐 Deployment (Vercel)

Larvi is production-deployed on Vercel. The `vercel.json` configuration routes:
- `/api/*` and `/auth/*` → FastAPI (Python serverless)
- Everything else → Static frontend

### Deploy Your Own Instance

```bash
# Install Vercel CLI
npm i -g vercel

# Set environment variables on Vercel
vercel env add GEMINI_API_KEY
vercel env add GOOGLE_CLIENT_ID
vercel env add GOOGLE_CLIENT_SECRET
vercel env add GOOGLE_REDIRECT_URI   # https://your-app.vercel.app/auth/callback
vercel env add SECRET_KEY
vercel env add FRONTEND_URL          # https://your-app.vercel.app

# Deploy
vercel --prod
```

> **Important:** After deploying, visit `https://your-app.vercel.app/auth/login` to complete OAuth on the production server.

---

## 📁 Project Structure

```
larvi-autonomous-agent/
│
├── backend/
│   ├── agents/
│   │   ├── master_agent.py       # LangGraph StateGraph orchestrator
│   │   ├── email_agent.py        # ReAct email agent
│   │   ├── calendar_agent.py     # ReAct calendar agent
│   │   └── llm_factory.py        # Multi-model Gemini cascade
│   │
│   ├── tools/
│   │   ├── email_tools.py        # LangChain Gmail tools
│   │   └── calendar_tools.py     # LangChain Calendar tools
│   │
│   ├── services/
│   │   ├── gmail_service.py      # Gmail API wrapper
│   │   └── gcal_service.py       # Google Calendar API wrapper
│   │
│   ├── auth/
│   │   └── google_oauth.py       # OAuth 2.0 flow + token management
│   │
│   ├── memory/
│   │   └── context_manager.py    # SQLite session + working memory
│   │
│   ├── main.py                   # FastAPI app + SSE streaming endpoint
│   ├── config.py                 # Pydantic settings from env vars
│   ├── auth_setup.py             # Desktop OAuth setup helper
│   ├── requirements.txt          # Python dependencies
│   └── .env.example              # Environment variable template
│
├── frontend/
│   ├── index.html                # Main shell
│   ├── css/
│   │   ├── main.css              # Design tokens, reset
│   │   ├── layout.css            # Responsive layout system
│   │   └── chat.css              # Chat UI, widgets, cards
│   └── js/
│       ├── app.js                # Core app logic, voice, sessions
│       ├── api.js                # SSE streaming client
│       ├── chat.js               # Message renderer, email/calendar widgets
│       └── context.js            # Client-side state management
│
├── vercel.json                   # Vercel routing configuration
├── .gitignore                    # Security: excludes all secrets
└── README.md                     # This file
```

---

## 🤖 Agent Architecture Deep Dive

### Master Orchestrator (`master_agent.py`)
The central brain — a **LangGraph StateGraph** that:
1. Classifies intent (email / calendar / both / general)
2. Routes to the appropriate specialized agent(s)
3. Synthesizes final response for the frontend
4. Manages state across multi-agent workflows

### LLM Factory (`llm_factory.py`)
Resilient **multi-model cascade** with automatic fallback:
```
gemini-2.5-flash → gemini-2.5-flash-lite → gemini-flash-latest → gemini-3.5-flash
```
Zero `429 Rate Limit` errors — 1500 RPD free tier optimized.

### ReAct Agent Pattern
Both Email and Calendar agents use the **ReAct (Reason + Act)** pattern:
```
Thought → Action → Observation → Thought → ... → Final Answer
```
Custom parse error recovery handles LLM format deviations gracefully.

### Memory System
- **SQLite persistence**: Conversation history survives server restarts
- **Working memory**: Active context (last email read, last event created) injected into every agent prompt

---

## 💬 Example Conversations

```
User:  "Send an email to john@example.com about tomorrow's standup at 9 AM"
Larvi: Drafts and sends a professional email with meeting details ✅

User:  "Schedule a 1-hour Zoom meeting with the design team on Friday at 2 PM"
Larvi: Checks availability → Creates calendar event → Confirms ✅

User:  "Summarize my last 5 emails"
Larvi: Fetches, summarizes, and presents emails as rich cards ✅

User:  "Reschedule my Monday meeting to Wednesday same time"
Larvi: Finds event → Updates calendar → Confirms change ✅
```

---

## 🔧 Key Design Decisions

### Why Vanilla JS?
Zero build complexity. SSE streaming works natively. No framework overhead — just fast, maintainable code.

### Why LangGraph over simple LangChain?
Multi-agent routing with shared state. Email + Calendar tasks can run in parallel with a single user prompt.

### Why Gemini Flash Lite as primary?
1500 requests/day free — no quota exhaustion in demos or evaluations. Falls back gracefully to stronger models.

### Why FastAPI + SSE?
True real-time streaming. Users see tokens as they're generated, not after a multi-second wait.

---

## 📊 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/chat` | Non-streaming chat |
| `POST` | `/chat/stream` | SSE streaming chat |
| `GET` | `/auth/login` | Initiate Google OAuth flow |
| `GET` | `/auth/callback` | OAuth callback handler |
| `GET` | `/auth/status` | Check authentication status |
| `GET` | `/emails/list` | List recent emails |
| `GET` | `/calendar/list` | List upcoming events |
| `GET` | `/health` | Health check |

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit with semantic messages: `git commit -m "feat: add amazing feature"`
4. Push: `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Author

**Abdul Sami Uthwal**
- GitHub: [@abdulsamiuthwal-eng](https://github.com/abdulsamiuthwal-eng)
- Project: [larvi-autonomous-agent](https://github.com/abdulsamiuthwal-eng/larvi-autonomous-agent)

---

<div align="center">

**Built with ❤️ using Google Gemini, LangGraph, FastAPI, and pure determination.**

[![🚀 Try Larvi Live](https://img.shields.io/badge/🚀%20Try%20Larvi%20Live-larvi--autonomous--agent.vercel.app-FF4500?style=for-the-badge)](https://larvi-autonomous-agent.vercel.app)

</div>
