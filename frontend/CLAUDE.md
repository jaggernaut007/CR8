# CLAUDE.md — frontend/
<!-- Lazy-loaded when editing files inside frontend/. Supplements root CLAUDE.md. -->

## Frontend Architecture

### Current State
The `frontend/` directory contains a **temporary prototype UI** — a FastAPI server
serving plain HTML/CSS/JavaScript templates. A proper React/Next.js frontend has NOT
been implemented yet. This prototype exists to demonstrate the pipeline and should be
treated as a placeholder.

**Before building the real frontend**: create a research note at `docs/research/frontend-framework.md`
to decide on the tech stack (React + Vite, Next.js, etc.) and check `docs/adr/` for any
prior decisions on frontend architecture.

### Module Structure (Wave 3 restructure)

`frontend/app.py` was refactored from ~693 lines to ~320 lines. Route logic now lives in
separate modules. `app.py` is responsible for app creation, lifespan, CORS/middleware
wiring, and router mounting only.

| Module | Purpose |
|--------|---------|
| `frontend/app.py` | FastAPI app factory, lifespan, middleware wiring, health check, HTML pages |
| `frontend/middleware.py` | `AuthMiddleware`, `SecurityHeadersMiddleware`, `get_current_user()` dependency, rate-limiter, session store |
| `frontend/auth_routes.py` | `/api/auth/*` — JWT register/login/refresh/me/logout + legacy session login |
| `frontend/job_routes.py` | `/api/upload`, `/api/start`, `/api/progress/{job_id}`, `/api/cancel/{job_id}`, `/api/download/{job_id}/{type}`, `/api/jobs`, `/api/jobs/{job_id}` |
| `frontend/quiz_routes.py` | `/api/quiz/*` — stubs returning 501 (Phase 4) |

### Entry point
`frontend/app.py` — FastAPI application with Uvicorn on port 8080.

**HTML pages (served directly from app.py):**
- `/` — Main application UI (Jinja2 template: `templates/index.html`)
- `/login` — Login form (Jinja2 template: `templates/login.html`)
- `/health` — Health check (public, no auth; used by Cloud Run readiness probe)

**Auth routes (prefix `/api/auth`):**
- `POST /api/auth/register` — Create account (email + password, requires DATABASE_URL)
- `POST /api/auth/login` — Issue access token (JWT mode: email + password) or set session cookie (legacy mode: password only)
- `POST /api/auth/refresh` — Issue new access token from `cr8_refresh` cookie
- `GET /api/auth/me` — Return current user info
- `POST /api/auth/logout` — Invalidate session and clear cookies (204)

**Job routes (prefix `/api`):**
- `POST /api/upload` — Upload PDF or PPTX, returns `{job_id, filename}`
- `POST /api/start` — Start pipeline for uploaded job, returns `{status: running}`
- `GET /api/progress/{job_id}` — Poll progress: `{status, stage, percent, logs, elapsed, warnings}`
- `POST /api/cancel/{job_id}` — Cancel a running job
- `GET /api/download/{job_id}/{type}` — Download artifact (pdf, ppt, scripts, videos)
- `GET /api/jobs` — List jobs for current user (requires JWT auth + DATABASE_URL)
- `GET /api/jobs/{job_id}` — Get single job from database

**Quiz routes (prefix `/api/quiz`):**
- All return `501 Not Implemented` — reserved for Phase 4

### Templates (frontend/templates/)
- `index.html` — Main app UI: drag-drop upload, format selection, real-time progress bar, download links
- `login.html` — Authentication form with rate-limiting feedback

These are static HTML files with inline CSS and vanilla JavaScript. No JSX or framework.

### Authentication
- **Dual auth**: JWT Bearer token (primary) with legacy session cookie fallback
- `get_current_user()` dependency in `frontend/middleware.py`: tries JWT Bearer first, falls back to `cr8_session` cookie
- JWT tokens: access token (short-lived, in response body) + refresh token (httponly cookie, path-scoped to `/api/auth/refresh`)
- Legacy session: 256-bit random token, 8-hour TTL, stored in process memory; for Jinja2 UI backward-compat
- Rate limiting: 5 failed attempts per 15 minutes per IP (sliding window, in-memory)
- `AuthMiddleware` enforces auth on all paths except `/login`, `/api/auth/login`, `/api/auth/register`, `/health`, `/static/`

### Security Headers
`SecurityHeadersMiddleware` adds to all responses:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'`

### CORS
`allowed_origins` is read from `settings.allowed_origins` (comma-separated string). The
app no longer uses `["*"]`. Set the `ALLOWED_ORIGINS` environment variable in production.

### DB Pool Lifecycle
On app startup (`lifespan`), if `DATABASE_URL` is set, an asyncpg pool is initialised and
stored at `app.state.db_pool`. On shutdown the pool is closed. If `DATABASE_URL` is absent
(local dev without Neon), the app runs without a database — auth routes requiring DB
return `503 Database not available`.

### Progress Streaming
Pipeline progress uses polling:
- Backend: `ProgressCapture` class in `frontend/app.py` intercepts `print()` from the pipeline thread
- Frontend JS: polls `/api/progress/{job_id}` every 2-3 seconds using `fetch` with auth header
- Progress events: `{"stage": "Ingest|Research|Generate|Script|Video", "percent": 0-100, "logs": [...], "warnings": [...]}`

### Tests (frontend/tests/)
- Tests use `pytest` + `httpx.AsyncClient` with FastAPI `TestClient`
- All tests mock the pipeline — they test HTTP routes and auth, not pipeline logic
- Key test files: `test_api.py` (route tests), `test_progress_capture.py` (SSE + progress tests)

## Key Rules
- All HTML is in `templates/` — no inline HTML strings in Python files
- Auth middleware applies to every route except the public paths listed above
- File uploads: 20 MB limit; accepted types: PDF, PPTX
- Outputs written to `outputs/` directory (gitignored); served via `/api/download/`
- Job routes import `ProgressCapture` and `_run_pipeline_sync` from `frontend.app` at call time (circular import guard)
