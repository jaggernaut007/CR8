---
description: CR8 API and backend coding standards for FastAPI endpoints, LangGraph pipeline, service layer, and configuration. Applied when editing Python files in frontend/ or backend/.
paths:
  - frontend/**/*.py
  - backend/**/*.py
---

# CR8 API & Backend Standards

## FastAPI Endpoints
- All endpoints return typed Pydantic response models — never return raw dicts
- Use `HTTPException` with correct status codes:
  - 422 for validation errors
  - 401/403 for auth failures
  - 404 for missing resources
  - 503 when upstream services (OpenAI, HeyGen, Tavily) are unavailable
- Protected routes use the `get_current_user` dependency from `frontend/app.py`
- Pipeline progress streams via `StreamingResponse` with `text/event-stream` media type
- Use `BackgroundTasks` for async file generation — return job ID immediately

## Service Layer
- All OpenAI, Tavily, HeyGen, and ChromaDB calls live in `backend/services/` only
- Agent files in `backend/pipeline/` call services — they never call external APIs directly
- Each service has a single responsibility: one file per external integration

## LangGraph Pipeline
- Pipeline state is a typed `TypedDict` defined in `backend/pipeline/state.py`
- State mutations are explicit — always return the full updated state from node functions
- Conditional edges use named constants, not inline strings
- Model routing uses `backend/config.py` settings (OPENAI_MODEL_NANO / MINI / MODEL / PREMIUM)

## Prompts
- All prompt strings live in `backend/prompts/` as Python module constants
- No inline prompt strings in agent files or service files
- When modifying prompts, run eval comparison before committing:
  `python -m backend.evals run_ab --variant [new-variant-name]`

## Configuration
- All configuration is in `backend/config.py` via Pydantic Settings
- No hardcoded values for ports, API endpoints, model names, or temperature settings
- Access config via the `settings` singleton: `from backend.config import settings`
