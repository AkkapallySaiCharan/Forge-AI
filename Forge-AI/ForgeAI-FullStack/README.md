# ForgeAI — Multi-Agent Software Engineering Workspace

A full-stack portfolio project demonstrating how specialized AI/software-engineering agents can be coordinated by an orchestration layer.

## Stack

- Frontend: React + Vite + JavaScript
- Backend: Python + FastAPI
- Persistence: SQLite
- AI integration point: OpenAI-compatible service layer
- Code intelligence: Python AST
- Security: lightweight SAST + secret detection
- Testing: Pytest
- Deployment foundation: Docker

## Architecture

```text
React/Vite
   |
   | REST/JSON
   v
FastAPI
   |
   v
Orchestrator
   |
   +--> Planner Agent
   +--> Developer Agent
   +--> Testing Agent
   +--> Security Agent
   +--> Reviewer Agent
   |
   v
SQLite

Optional integrations:
LLM provider / GitHub API
```

## Run backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Swagger: http://127.0.0.1:8000/docs

## Run frontend

Open another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal, normally http://localhost:5173.

## Run tests

```powershell
cd backend
pytest -q
```

## Environment

Copy `backend/.env.example` to `backend/.env`.

This repository intentionally runs without an API key using deterministic agent logic. The LLM service is isolated so a real model can be plugged in without changing the API architecture.

## Git

```powershell
git init
git add .
git commit -m "Initial ForgeAI full-stack implementation"
```

## Production roadmap

For a real multi-user deployment, add PostgreSQL, Redis/Celery workers, authentication/authorization, repository sandboxing, GitHub webhooks, stronger SAST/dependency scanning, structured logging, observability and CI/CD.
