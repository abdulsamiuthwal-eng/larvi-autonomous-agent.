# Larvi AI Agent Workspace Guidelines

This repository contains **Larvi — Autonomous Email & Calendar AI Agent**, built with FastAPI, LangGraph, Google Gemini, and Google Cloud APIs.

For full architectural details, tool references, and execution workflows, refer to [`PROJECT_OVERVIEW.md`](file:///d:/DEVFORGE_INTERNSHIP/Final%20Exam/PROJECT_OVERVIEW.md).

## Key Components & File Map
- **Master Orchestrator**: [`backend/agents/master_agent.py`](file:///d:/DEVFORGE_INTERNSHIP/Final%20Exam/backend/agents/master_agent.py) (LangGraph StateGraph, Intent Classification, Multi-Node Routing, Response Synthesis)
- **LLM Factory & Resilience**: [`backend/agents/llm_factory.py`](file:///d:/DEVFORGE_INTERNSHIP/Final%20Exam/backend/agents/llm_factory.py) (Automatic Multi-Model Cascade: `gemini-2.5-flash`, `gemini-2.5-flash-lite`, 1500 RPD free tier, low-latency fallback)
- **Email Agent & Tools**: [`backend/agents/email_agent.py`](file:///d:/DEVFORGE_INTERNSHIP/Final%20Exam/backend/agents/email_agent.py), [`backend/tools/email_tools.py`](file:///d:/DEVFORGE_INTERNSHIP/Final%20Exam/backend/tools/email_tools.py)
- **Calendar Agent & Tools**: [`backend/agents/calendar_agent.py`](file:///d:/DEVFORGE_INTERNSHIP/Final%20Exam/backend/agents/calendar_agent.py), [`backend/tools/calendar_tools.py`](file:///d:/DEVFORGE_INTERNSHIP/Final%20Exam/backend/tools/calendar_tools.py)
- **Memory Engine**: [`backend/memory/context_manager.py`](file:///d:/DEVFORGE_INTERNSHIP/Final%20Exam/backend/memory/context_manager.py) (SQLite persistence + Multi-Turn Working Memory)
- **Google OAuth**: [`backend/auth/google_oauth.py`](file:///d:/DEVFORGE_INTERNSHIP/Final%20Exam/backend/auth/google_oauth.py), [`backend/auth_setup.py`](file:///d:/DEVFORGE_INTERNSHIP/Final%20Exam/backend/auth_setup.py)
- **FastAPI Server**: [`backend/main.py`](file:///d:/DEVFORGE_INTERNSHIP/Final%20Exam/backend/main.py) (SSE streaming at `/chat/stream`, REST at `/chat`, OAuth routes)
- **Frontend UI & Views**:
  - Main Shell: [`frontend/index.html`](file:///d:/DEVFORGE_INTERNSHIP/Final%20Exam/frontend/index.html)
  - Core App Logic: [`frontend/js/app.js`](file:///d:/DEVFORGE_INTERNSHIP/Final%20Exam/frontend/js/app.js) (Voice input mic, Stop response button, Chat sessions, Settings)
  - API Client: [`frontend/js/api.js`](file:///d:/DEVFORGE_INTERNSHIP/Final%20Exam/frontend/js/api.js) (SSE streaming with AbortController signal)
  - Chat Renderer: [`frontend/js/chat.js`](file:///d:/DEVFORGE_INTERNSHIP/Final%20Exam/frontend/js/chat.js) (Email widgets, Calendar badges)
  - Context & State: [`frontend/js/context.js`](file:///d:/DEVFORGE_INTERNSHIP/Final%20Exam/frontend/js/context.js)

## Commands
- **Backend Server**: `cd backend && python -m uvicorn main:app --host 127.0.0.1 --port 8000`
- **Frontend Server**: `cd frontend && python -m http.server 5500`
- **OAuth Desktop Login**: `cd backend && python auth_setup.py`
- **Vercel Deploy**: `npx vercel --prod --yes`

## Recent Major Features
1. **Voice Input (Microphone)**: Real-time Speech-to-Text via Web Speech API in chat bar.
2. **Stop Response Generation Button**: AbortController-powered cancelation for in-flight LLM streams.
3. **User Profile System**: Custom avatar photo upload, display name & role updates, change password form, multi-point logout.
4. **Resilient Date Inferences & Parameter Parsing**: Live date injection (`current_datetime`) in agent prompts and robust `_parse_int_arg` for calendar tools.
5. **High-Quota Low-Latency Models**: Prioritizes `gemini-2.5-flash` and `gemini-2.5-flash-lite` (1500 RPD, zero 429 quota exhaustion).
