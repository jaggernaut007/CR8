# CLAUDE.md — frontend/
<!-- Lazy-loaded when editing files inside frontend/. Supplements root CLAUDE.md. -->

## Frontend Architecture

### Current State (v0.5.3)
The `frontend/` directory contains two layers:

1. **React SPA** (`frontend/react-app/`) — the primary UI, built with React 19 + Vite 7 + Tailwind v4 + Tanstack Query
2. **FastAPI backend** (`frontend/app.py`) — serves the API + static SPA files in production

The SPA is built via `make build-frontend` → copies to `frontend/static/` (gitignored).
FastAPI detects `frontend/static/index.html` at import time — if present, serves the React SPA;
otherwise falls back to Jinja2 templates (legacy). The Jinja2 fallback is retained while the React SPA is the primary path.

### React SPA Structure (`frontend/react-app/`)

| Path | Purpose |
|------|---------|
| `src/api/client.ts` | JWT-aware fetch wrapper with auto-refresh on 401 |
| `src/api/auth.ts` | Auth API: login, register, logout, fetchCurrentUser |
| `src/api/jobs.ts` | Job API: fetchJobs, uploadFile, startPipeline, fetchProgress, cancelJob, downloadUrl |
| `src/context/AuthContext.tsx` | Auth state provider with silent refresh on mount |
| `src/components/Navbar.tsx` | Top navigation bar with logout |
| `src/components/ProtectedRoute.tsx` | Auth guard wrapping `<Outlet />` |
| `src/components/ContentTabs.tsx` | Tab bar switching between PDF / Slides / Video viewer panels |
| `src/components/PdfViewer.tsx` | Inline PDF viewer via `<iframe>` (browser-native, zero deps) |
| `src/components/PptCarousel.tsx` | Slide image carousel — prev/next, counter, keyboard arrow navigation |
| `src/components/VideoPlayer.tsx` | HTML5 `<video>` with topic selector dropdown |
| `src/pages/LoginPage.tsx` | Login + register card with glassmorphism |
| `src/pages/DashboardPage.tsx` | Job history list with status badges |
| `src/pages/UploadPage.tsx` | Drag-drop file upload + format selection |
| `src/pages/ProgressPage.tsx` | Pipeline stages + progress bar + ETA polling |
| `src/pages/ResultsPage.tsx` | Viewer panels (PDF / Slides / Video) above download buttons |
| `src/index.css` | Tailwind v4 design system (`@theme` + `@utility` directives) |

**Key patterns:**
- Access tokens stored in memory only (never localStorage) — prevents XSS exfiltration
- Silent refresh on mount via httpOnly `cr8_refresh` cookie
- Tanstack Query for all GET requests (caching, refetch, loading states)
- All API types centralized in `api/jobs.ts` and `api/auth.ts`

### FastAPI Module Structure

`frontend/app.py` was refactored from ~693 lines to ~320 lines. Route logic now lives in
separate modules. `app.py` is responsible for app creation, lifespan, CORS/middleware
wiring, and router mounting only.

| Module | Purpose |
|--------|---------|
| `frontend/app.py` | FastAPI app factory, lifespan, middleware wiring, health check, SPA catch-all |
| `frontend/middleware.py` | `AuthMiddleware`, `SecurityHeadersMiddleware`, `get_current_user()` dependency, rate-limiter, session store |
| `frontend/auth_routes.py` | `/api/auth/*` — JWT register/login/refresh/me/logout + legacy session login |
| `frontend/job_routes.py` | `/api/upload`, `/api/start`, `/api/progress/{job_id}`, `/api/cancel/{job_id}`, `/api/download/{job_id}/{type}`, `/api/jobs`, `/api/jobs/{job_id}` |
| `frontend/quiz_routes.py` | `/api/quiz/*` — stubs returning 501 (Phase 4) |
| `frontend/view_routes.py` | `/api/view/*` — inline PDF, slide images, video streaming for content viewers |

### API Endpoints

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

**View routes (prefix `/api/view`):**
- `GET /api/view/{job_id}/pdf` — Serve PDF inline (Content-Disposition: inline) for iframe embedding
- `GET /api/view/{job_id}/slides` — JSON listing of slide image URLs and count
- `GET /api/view/{job_id}/slide/{index}` — Individual slide PNG (1-based index)
- `GET /api/view/{job_id}/videos` — JSON listing of video names and stream URLs
- `GET /api/view/{job_id}/video/{index}` — Stream MP4 video (0-based index, supports Range requests)

**Quiz routes (prefix `/api/quiz`):**
- All return `501 Not Implemented` — reserved for Phase 4

### Authentication
- **Dual auth**: JWT Bearer token (primary) with legacy session cookie fallback (see ADR-002)
- `get_current_user()` dependency in `frontend/middleware.py`: tries JWT Bearer first, falls back to `cr8_session` cookie
- JWT tokens: access token (short-lived, in response body) + refresh token (httponly cookie, path-scoped to `/api/auth/refresh`)
- Legacy session: 256-bit random token, 8-hour TTL, stored in process memory; being removed after v0.5.3
- Rate limiting: 5 failed attempts per 15 minutes per IP (sliding window, in-memory)
- `AuthMiddleware` enforces auth on all paths except `/login`, `/api/auth/login`, `/api/auth/register`, `/health`, `/static/`

### Security Headers
`SecurityHeadersMiddleware` adds to all responses:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: SAMEORIGIN` (allows PDF iframe embedding from same origin)
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; media-src 'self'; frame-src 'self'`

### Development
- **React dev server**: `cd frontend/react-app && npm run dev` → port 5173 (proxies `/api` to 8080)
- **FastAPI server**: `make dev` → port 8080
- **Build SPA**: `make build-frontend` → `frontend/static/` (gitignored)
- `frontend/static/` and `frontend/react-app/dist/` are gitignored — build artifacts only

### Tests (frontend/tests/)
- Tests use `pytest` + `httpx.AsyncClient` with FastAPI `TestClient`
- All tests mock the pipeline — they test HTTP routes and auth, not pipeline logic
- Key test files: `test_api.py` (route tests), `test_progress_capture.py` (progress tests)

## Key Rules
- Access tokens in memory only — NEVER in localStorage or cookies
- Auth middleware applies to every route except the public paths listed above
- File uploads: 50 MB limit; accepted types: PDF, PPTX
- Outputs written to `outputs/` directory (gitignored); served via `/api/download/`
- Job routes import `ProgressCapture` and `_run_pipeline_sync` from `frontend.app` at call time (circular import guard)
- All API types live in `api/jobs.ts` and `api/auth.ts` — pages import from these, not inline
