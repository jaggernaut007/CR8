# Frontend API Endpoints

The CR8 web UI is a FastAPI application serving a single-page HTML interface.

**Entry point**: `frontend/app.py` (app factory, lifespan, middleware wiring, health check)

## Module Structure

Route logic was extracted from `app.py` into focused sub-modules during the Wave 3 restructure:

| Module | Purpose |
|--------|---------|
| `frontend/app.py` | FastAPI app factory, lifespan, CORS/middleware wiring, health check (`/health`), HTML pages (`/`, `/login`) |
| `frontend/middleware.py` | `AuthMiddleware`, `SecurityHeadersMiddleware`, `get_current_user()` dependency, rate limiter, session store |
| `frontend/auth_routes.py` | `/api/auth/*` — JWT register/login/refresh/me/logout + legacy session login |
| `frontend/job_routes.py` | `/api/upload`, `/api/start`, `/api/progress/{job_id}`, `/api/cancel/{job_id}`, `/api/download/{job_id}/{type}`, `/api/jobs`, `/api/jobs/{job_id}` |
| `frontend/quiz_routes.py` | `/api/quiz/*` — stubs returning 501 (reserved for Phase 4) |

## Endpoints

### HTML Pages

| Endpoint | Method | Auth required | Description |
|----------|--------|---------------|-------------|
| `/` | GET | Yes | Serve the main application UI (redirects to `/login` if unauthenticated) |
| `/login` | GET | No | Serve the login form |
| `/health` | GET | No | Health check — returns `{"status": "ok"}` (used by Cloud Run readiness probe) |

### Auth Routes (`/api/auth`)

| Endpoint | Method | Auth required | Description |
|----------|--------|---------------|-------------|
| `/api/auth/register` | POST | No | Create account (requires `DATABASE_URL`); returns 201 with `access_token` + sets `cr8_refresh` httponly cookie |
| `/api/auth/login` | POST | No | JWT mode (email + password) or legacy mode (password only); returns access token or sets session cookie |
| `/api/auth/refresh` | POST | Yes | Issue new access token from `cr8_refresh` cookie |
| `/api/auth/me` | GET | Yes | Return `{user_id, email, role}` for the authenticated caller |
| `/api/auth/logout` | POST | No | Invalidate session and clear cookies; returns 204 |

### Job Routes (`/api`)

| Endpoint | Method | Auth required | Description |
|----------|--------|---------------|-------------|
| `/api/upload` | POST | Yes | Upload a PDF or PPTX, returns `{job_id, filename}` |
| `/api/start` | POST | Yes | Start pipeline for a job, returns `{status: running}` |
| `/api/progress/{job_id}` | GET | Yes | Poll progress: `{status, stage, percent, logs, elapsed, warnings}` |
| `/api/cancel/{job_id}` | POST | Yes | Cancel a running job |
| `/api/download/{job_id}/{type}` | GET | Yes | Download output files (pdf, ppt, scripts, videos) |
| `/api/jobs` | GET | Yes | List jobs for the current user (requires JWT + `DATABASE_URL`) |
| `/api/jobs/{job_id}` | GET | Yes | Get a single job record from the database |

### Quiz Routes (`/api/quiz`)

All quiz endpoints return `501 Not Implemented` — the quiz platform is reserved for Phase 4.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/quiz/` | GET | List quizzes (stub) |
| `/api/quiz/{quiz_id}` | GET | Get a quiz (stub) |
| `/api/quiz/{quiz_id}/start` | POST | Start a quiz attempt (stub) |
| `/api/quiz/{quiz_id}/submit` | POST | Submit quiz answers (stub) |

## Authentication

CR8 uses dual authentication: JWT Bearer token (primary) with legacy session cookie fallback.

### JWT Auth (primary)

```
POST /api/auth/login
Content-Type: application/json

Body: {"email": "user@example.com", "password": "secret"}

Response: {"access_token": "<jwt>", "token_type": "bearer"}
Set-Cookie: cr8_refresh=<refresh_jwt>; HttpOnly; Path=/api/auth/refresh
```

Use the access token in subsequent requests:

```
GET /api/auth/me
Authorization: Bearer <access_token>
```

Access tokens are short-lived. Use `/api/auth/refresh` with the `cr8_refresh` cookie to obtain a new one.

### Legacy Session Auth (backward-compatible)

```
POST /api/auth/login
Content-Type: application/json

Body: {"password": "CR8-AI"}

Response: {"message": "Logged in"}
Set-Cookie: cr8_session=<token>; HttpOnly
```

The `cr8_session` cookie is accepted as an alternative to JWT Bearer by `get_current_user()`. This path exists for the Jinja2 UI.

### Rate Limiting

Login failures are rate-limited per IP: 5 failures within 15 minutes triggers HTTP 429. The counter resets automatically after 15 minutes.

### DB-Less Mode

When `DATABASE_URL` is not set (local dev without Neon), auth routes that require a database return `503 Database not available`. The app runs normally in all other respects.

## Security Headers

`SecurityHeadersMiddleware` injects the following headers on every response:

| Header | Value |
|--------|-------|
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Content-Security-Policy` | `default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'` |

## CORS

CORS is configured from `settings.allowed_origins` (env var `ALLOWED_ORIGINS`, comma-separated list). Set this to the actual frontend domain in production. The wildcard `["*"]` origin is no longer used.

## Upload Flow

```
POST /api/upload
Content-Type: multipart/form-data

Body: file=<PDF or PPTX file>

Response: {"job_id": "abc123", "filename": "syllabus.pdf"}
```

The endpoint validates the uploaded file using magic bytes before saving:

- **PDF**: first 5 bytes must be `%PDF-`
- **PPTX**: first 4 bytes must be `PK\x03\x04` (ZIP header — all `.pptx` files are ZIP archives)

Any other file type is rejected with HTTP 400. The validated file is saved to a temporary directory keyed by `job_id`.

## Pipeline Execution

```
POST /api/start
Content-Type: application/json

Body: {"job_id": "abc123"}

Response: {"status": "running"}
```

The pipeline runs in a background thread. Progress is tracked via `ProgressCapture`. On start, the endpoint scans the job directory for both `.pdf` and `.pptx` files to locate the uploaded source file.

## Progress Polling

```
GET /api/progress/abc123

Response:
{
    "status": "running",
    "stage": "Research",
    "percent": 45,
    "logs": ["[Ingest] Extracting text...", "[Research] Searching web..."],
    "elapsed": 32.5,
    "warnings": []
}
```

The frontend polls this endpoint every 2 seconds to update the progress bar and log display. The `warnings` list accumulates any `[Video] ERROR:` or `[Video] WARNING:` lines captured during video generation. These are surfaced to the user as a yellow warning box below the download buttons on completion.

## ProgressCapture

The `ProgressCapture` class intercepts pipeline `print()` output and parses stage prefixes to compute progress percentage.

### Stage Weights

| Stage | Weight | Cumulative |
|-------|--------|------------|
| Upload & Validation | 0.02 | 2% |
| Ingest | 0.10 | 12% |
| Research | 0.18 | 30% |
| Module Generation | 0.20 | 50% |
| PPT Generation | 0.10 | 60% |
| Script Generation | 0.10 | 70% |
| PDF Build | 0.05 | 75% |
| PPT Build | 0.05 | 80% |
| Video Generation | 0.18 | 98% |
| Completion | 0.02 | 100% |

!!! warning "Video weight"
    The Video stage weight was increased from 2% to 18% (net 18% of total pipeline weight) to reflect the CPU time consumed by Kokoro TTS synthesis. The cumulative percentages above reflect this rebalancing.

### How It Works

1. `ProgressCapture` replaces `sys.stdout` with a custom writer
2. Each `print()` call is intercepted and parsed for stage prefixes (e.g., `[Research]`)
3. The stage prefix maps to a weight in the table above
4. Progress percentage is computed as the cumulative weight up to the current stage
5. Lines beginning with `[Video] ERROR:` or `[Video] WARNING:` are also collected into a separate `warnings` list
6. All captured output lines are stored in a thread-safe log buffer
7. The `/api/progress` endpoint reads from this buffer to return current state

## Download Endpoints

```
GET /api/download/abc123/pdf      # Download the learning module PDF
GET /api/download/abc123/ppt      # Download the gap analysis PPTX
GET /api/download/abc123/scripts  # Download video scripts (ZIP)
GET /api/download/abc123/videos   # Download generated videos (ZIP)
```

Files are served from the output directory associated with the `job_id`. Returns 404 if the pipeline has not completed or the requested output type was not generated.
