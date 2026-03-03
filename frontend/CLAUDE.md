# CLAUDE.md — frontend/
<!-- Lazy-loaded when editing files inside frontend/. Supplements root CLAUDE.md. -->

## Frontend Architecture

### Current State
The `frontend/` directory contains a **temporary prototype UI** — a FastAPI server
(`frontend/app.py`) serving plain HTML/CSS/JavaScript templates. A proper React/Next.js
frontend has NOT been implemented yet. This prototype exists to demonstrate the pipeline
and should be treated as a placeholder.

**Before building the real frontend**: create a research note at `docs/research/frontend-framework.md`
to decide on the tech stack (React + Vite, Next.js, etc.) and check `docs/adr/` for any
prior decisions on frontend architecture.

### Entry point
`frontend/app.py` — FastAPI application with Uvicorn on port 8080:
- `/` — Main application UI (Jinja2 template: `templates/index.html`)
- `/login` — Login form (Jinja2 template: `templates/login.html`)
- `/upload` — POST endpoint: accepts PDF, queues pipeline job, returns job ID
- `/progress/{job_id}` — GET: Server-Sent Events stream for real-time pipeline progress
- `/download/{filename}` — GET: serve completed output files
- `/logout` — POST: clear session

### Templates (frontend/templates/)
- `index.html` — Main app UI: drag-drop upload, format selection, real-time progress bar, download links
- `login.html` — Authentication form with rate-limiting feedback

These are static HTML files with inline CSS and vanilla JavaScript. No JSX or framework.

### Authentication
- Session-based auth using bcrypt password hashing
- `get_current_user()` dependency: inject into any protected route
- Rate limiting: 5 attempts per 15 minutes per IP (built into login handler)
- Session expiry: JS polling detects 401s and redirects to `/login`

### Progress Streaming
Pipeline progress uses Server-Sent Events (SSE):
- Backend: `StreamingResponse` with `text/event-stream` media type
- Frontend JS: polls every 3 seconds using `fetch` (not EventSource, due to auth headers)
- Progress events: `{"stage": "ingest|research|generate", "percent": 0-100, "message": "..."}`

### Tests (frontend/tests/)
- 80 tests using `pytest` + `httpx.AsyncClient` with FastAPI `TestClient`
- All tests mock the pipeline — they test HTTP routes and auth, not pipeline logic
- Key test files: `test_api.py` (route tests), `test_progress_capture.py` (SSE tests)

## Key Rules
- All HTML is in `templates/` — no inline HTML strings in `app.py`
- Auth middleware applies to every route except `/login` and `/static/`
- File uploads: 20 MB limit; accepted types: PDF, PPTX
- Outputs written to `outputs/` directory (gitignored); served via `/download/`
