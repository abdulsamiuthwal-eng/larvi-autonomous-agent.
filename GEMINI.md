# Larvi AI Agent Workspace Guidelines

This repository contains **Larvi — Autonomous Email & Calendar AI Agent**, built with FastAPI, LangGraph, Google Gemini, and Google Cloud APIs.

For full architectural details, tool references, and execution workflows, refer to [`PROJECT_OVERVIEW.md`](file:///d:/DEVFORGE_INTERNSHIP/Final%20Exam/PROJECT_OVERVIEW.md).

## Key Components
- **Master Agent**: [`backend/agents/master_agent.py`](file:///d:/DEVFORGE_INTERNSHIP/Final%20Exam/backend/agents/master_agent.py) (LangGraph StateGraph, Intent Classification, Response Synthesis)
- **Email Agent & Tools**: [`backend/agents/email_agent.py`](file:///d:/DEVFORGE_INTERNSHIP/Final%20Exam/backend/agents/email_agent.py), [`backend/tools/email_tools.py`](file:///d:/DEVFORGE_INTERNSHIP/Final%20Exam/backend/tools/email_tools.py)
- **Calendar Agent & Tools**: [`backend/agents/calendar_agent.py`](file:///d:/DEVFORGE_INTERNSHIP/Final%20Exam/backend/agents/calendar_agent.py), [`backend/tools/calendar_tools.py`](file:///d:/DEVFORGE_INTERNSHIP/Final%20Exam/backend/tools/calendar_tools.py)
- **Memory Engine**: [`backend/memory/context_manager.py`](file:///d:/DEVFORGE_INTERNSHIP/Final%20Exam/backend/memory/context_manager.py)
- **OAuth Setup**: [`backend/auth_setup.py`](file:///d:/DEVFORGE_INTERNSHIP/Final%20Exam/backend/auth_setup.py)
- **Frontend UI**: [`frontend/index.html`](file:///d:/DEVFORGE_INTERNSHIP/Final%20Exam/frontend/index.html), [`frontend/js/app.js`](file:///d:/DEVFORGE_INTERNSHIP/Final%20Exam/frontend/js/app.js)

## Commands
- Backend: `cd backend && python -m uvicorn main:app --host 127.0.0.1 --port 8000`
- Frontend: `cd frontend && python -m http.server 5500`
- OAuth Login: `cd backend && python auth_setup.py`
