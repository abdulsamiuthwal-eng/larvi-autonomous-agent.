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
* ⚡ **Multi-Model Auto-Fallback Engine**: Zero-quota disruption cascade prioritizing `gemini-2.5-flash` & `gemini-2.5-flash-lite` (1500 Requests/Day free tier quota, sub-second latency).
* 🎙️ **Voice Input (Microphone)**: Real-time Speech-to-Text via Web Speech API in the chat bar.
* ⏹️ **Instant Stop Generation Button**: AbortController-powered cancelation for in-flight LLM streams.
* 💬 **Gemini & ChatGPT-Style Multi-Chat Sidebar**: Persistent conversation histories, automatic conversation naming, and 1-click session switching powered by a persistent **SQLite Database**.
* 🌊 **Real-Time Word-by-Word Streaming (SSE)**: Live token generation with real-time workflow step indicators and tool execution feeds.
* ✉️ **Rich Interactive Visual Cards**:
  * **Interactive Email Draft Cards**: Recipient, Subject, and Body preview with 1-click **Send Email** and **Discard** actions.
  * **Calendar Event Badges**: Date badges, conflict indicators, and 1-click **Add to Calendar** and **Reschedule** actions.
* 👤 **Customizable User Profile**: Photo upload, display name & role updates, change password form, multi-point logout.
* 🔒 **Multi-User Google OAuth 2.0**: Secure per-session Google Workspace connection for Gmail and Google Calendar.
* 🛡️ **Human-in-the-Loop Safety**: Confirmation dialogs for destructive actions (sending emails, deleting events).

---

## 🏛️ System Architecture

```
User Input (Voice or Text) ──▶ FastAPI (/chat/stream) ──▶ Master Orchestrator (LangGraph)
                                                                 │
                 ┌───────────────────────────────────────────────┼──────────────────────────────┐
                 ▼                                               ▼                              ▼
        [Email Sub-Agent]                               [Calendar Sub-Agent]          [Chitchat Engine]
        * read_emails                                   * check_availability         * Context & Greetings
        * search_emails                                 * create_event                
        * draft_email                                   * get_upcoming_events         
        * send_email                                    * reschedule_event            
        * reply_to_email                                * delete_event                
        * summarize_unread                              * find_free_slots             
                 │                                               │
                 └───────────────────────┬───────────────────────┘
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
git clone https://github.com/abdulsamiuthwal-eng/larvi-autonomous-agent.git
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
GEMINI_MODEL=gemini-2.5-flash
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

## 🔒 Google Cloud OAuth 2.0 Setup

To enable real Gmail and Google Calendar features:
1. Create a project in [Google Cloud Console](https://console.cloud.google.com/).
2. Enable **Gmail API** and **Google Calendar API**.
3. Create OAuth 2.0 Credentials (Desktop App) and download as `credentials.json`.
4. Place `credentials.json` into the `backend/` folder.
5. Run the authentication script:
   ```bash
   cd backend
   python auth_setup.py
   ```

---

## 🌐 Production Deployment (Vercel)

Larvi is configured for instant serverless deployment on Vercel with Python Serverless Functions:
```bash
npx vercel --prod --yes
```

---
*Created for Larvi AI Assistant — DevForge Final Capstone Project.*
