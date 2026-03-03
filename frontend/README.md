# frontend/

Prototype web UI for the CR8 pipeline. **Not the final frontend.**

## Current State

This is a **temporary FastAPI + Jinja2 prototype** to demonstrate the pipeline.
A proper React/Next.js frontend is planned but not yet implemented.

## Structure

```
frontend/
├── app.py          ← FastAPI server on port 8080
├── templates/
│   ├── index.html  ← Main app UI (drag-drop upload, progress, downloads)
│   └── login.html  ← Authentication form
└── tests/          ← 80 route and auth tests
```

## Running

```bash
make dev    # hot-reload dev server → http://localhost:8080
make serve  # production-style server
```

## Key Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Main UI (requires auth) |
| `/login` | GET/POST | Login form |
| `/logout` | POST | Clear session |
| `/upload` | POST | Accept PDF, start pipeline, return job ID |
| `/progress/{job_id}` | GET | SSE stream: real-time pipeline progress |
| `/download/{filename}` | GET | Serve completed output files |

## Authentication

Session-based auth with bcrypt. All routes except `/login` require authentication.
Rate limited: 5 login attempts per 15 minutes per IP.

## Future Frontend

When implementing the proper frontend:
1. Create `docs/research/frontend-framework.md` (React? Next.js? Vite?)
2. Check `docs/adr/` for any prior frontend decisions
3. The FastAPI backend (`app.py`) will remain as the API layer
