# Web UI

CR8 ships a React SPA (v0.5.2+) served by the FastAPI backend. The Jinja2 prototype remains as a fallback when the React build is absent.

## Starting the Server

```bash
# Build the React SPA (one-time or after frontend changes)
make build-frontend

# Start the backend server
make dev
# Opens at http://localhost:8080
```

Without `make build-frontend`, the server serves the legacy Jinja2 UI.

## Prerequisites

The React SPA requires a database connection for user accounts. See [Configuration > Database](configuration.md#database-neon-postgresql) for setup.

Without a database, the server falls back to the legacy Jinja2 UI with shared-password auth.

## Creating an Account

1. Navigate to `http://localhost:8080` — you'll be redirected to `/login`
2. Click "Create account" to switch to the registration form
3. Enter a display name, email, and password
4. After registration, you're automatically logged in and redirected to the dashboard

## React SPA (v0.5.2+)

**Stack**: React 19 + Vite 7 + Tailwind v4 + Tanstack Query + React Router v7.

**Pages**:

| Route | Page | Description |
|-------|------|-------------|
| `/login` | `LoginPage` | JWT login/register form; redirects to `/dashboard` on success |
| `/dashboard` | `DashboardPage` | Recent jobs list; protected route |
| `/upload` | `UploadPage` | Drag-and-drop PDF/PPTX upload with format selector |
| `/progress/:jobId` | `ProgressPage` | Real-time progress polling (2 s interval via Tanstack Query) |
| `/results/:jobId` | `ResultsPage` | Download buttons + quiz generation for completed jobs |
| `/quiz/:quizId` | `QuizPage` | One-question-at-a-time quiz view with navigation |
| `/quiz/:quizId/results` | `QuizResultsPage` | Score summary + per-question feedback in review mode |

**Features**:
- Glassmorphism design system (backdrop-blur, semi-transparent cards)
- JWT-aware fetch client — attaches `Authorization: Bearer` automatically; auto-refreshes on 401
- `AuthContext` — provides `user`, `login`, `logout`, and `isLoading` throughout the tree
- `ProtectedRoute` guard — unauthenticated users are redirected to `/login`
- Responsive `Navbar` with user display and logout
- On-demand quiz generation from completed pipeline output (v0.5.4)

## Building the React App

```bash
# In the project root
make build-frontend
# Equivalent: cd frontend/react-app && npm ci && npm run build
# Output: frontend/static/ (index.html + /assets/ bundle)
```

The FastAPI catch-all (`/{full_path:path}`) serves `frontend/static/index.html` for all non-API paths when the build is present, enabling React Router client-side navigation.

## Legacy Jinja2 UI (fallback)

When `frontend/static/index.html` is absent, the server falls back to the Jinja2-templated prototype. This path remains useful for quick local development without a Node.js build step.

Features of the legacy UI:
- **PDF upload** — drag-and-drop or file picker
- **Format selection** — PDF (always on), PPT (optional), Script (optional), Video (Kokoro TTS)
- **Real-time progress** — stage label, progress bar, elapsed/estimated time, scrolling log area
- **Download** — PDF as direct download, scripts and videos as .zip files

## Architecture

The web UI follows a simple async pattern: the browser polls for progress while the pipeline runs in a background thread.

```
Browser (JS fetch)     FastAPI (async uvicorn)      Pipeline Thread
    |                        |                            |
    |-- POST /api/upload --->|  save PDF to uploads/      |
    |<-- { job_id } ---------|                            |
    |                        |                            |
    |-- POST /api/start ---->|  asyncio.create_task()     |
    |                        |    +-- asyncio.to_thread()-->|
    |<-- {status: running} --|         run_job()          |
    |                        |                            |-- ThreadPoolExecutor(8)
    |-- GET /api/progress -->|                            |   (parallel topics)
    |<-- {stage, pct, logs} -|  reads ProgressCapture     |
    |   (poll every 3s)      |                            |
    |                        |<--- result dict -----------|
    |-- GET /api/progress -->|                            |
    |<-- {complete, files} --|                            |
    |                        |                            |
    |-- GET /api/download -->|                            |
    |<-- file bytes ---------|                            |
```

1. The browser uploads a PDF via `POST /api/upload`, receiving a `job_id`.
2. `POST /api/start` launches the pipeline in a background thread using `asyncio.to_thread()`.
3. The browser polls `GET /api/progress/{job_id}` every 3 seconds to get the current stage, percentage, and log output.
4. When the pipeline completes, the progress response includes the list of downloadable files.
5. The browser requests files via `GET /api/download/{job_id}/{type}`.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serve the HTML UI |
| `/api/upload` | POST | Upload a PDF, returns `{job_id, filename}` |
| `/api/start` | POST | Start pipeline for a job, returns `{status: running}` |
| `/api/progress/{job_id}` | GET | Poll progress: `{status, stage, percent, logs, elapsed}` |
| `/api/download/{job_id}/{type}` | GET | Download output files (pdf, scripts, videos) |

## Progress Tracking

The `ProgressCapture` class (defined in `frontend/app.py`) intercepts pipeline `print()` output and parses stage prefixes (`[Ingest]`, `[Research]`, `[Generate]`, `[Script]`, `[Video]`) to compute an overall progress percentage using stage weights:

| Stage | Weight | Cumulative |
|-------|--------|------------|
| Ingest | 15% | 0--15% |
| Research | 50% | 15--65% |
| Generate | 25% | 65--90% |
| Script | 8% | 90--98% |
| Video | 2% | 98--100% |

Sub-step progress (`Topic X/Y`, `Module X/Y`) is interpolated within each stage for smooth progress bar updates. For example, if the Research agent is on topic 8 of 15, the progress bar shows approximately `15% + (8/15 * 50%) = 41.7%`.
