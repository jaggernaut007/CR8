# Frontend API Endpoints

The CR8 web server is a FastAPI application. When `frontend/static/index.html` is present (built via `make build-frontend`), it serves the React SPA; otherwise it falls back to the legacy Jinja2 UI.

**Entry point**: `frontend/app.py` (app factory, lifespan, middleware wiring, health check, SPA catch-all)

## Module Structure

Route logic was extracted from `app.py` into focused sub-modules during the Wave 3 restructure:

| Module | Purpose |
|--------|---------|
| `frontend/app.py` | FastAPI app factory, lifespan, CORS/middleware wiring, health check (`/health`), HTML pages (`/`, `/login`) |
| `frontend/middleware.py` | `AuthMiddleware`, `SecurityHeadersMiddleware`, `get_current_user()` dependency, rate limiter, session store |
| `frontend/auth_routes.py` | `/api/auth/*` — JWT register/login/refresh/me/logout + legacy session login |
| `frontend/job_routes.py` | `/api/upload`, `/api/start`, `/api/progress/{job_id}`, `/api/cancel/{job_id}`, `/api/download/{job_id}/{type}`, `/api/jobs`, `/api/jobs/{job_id}` |
| `frontend/view_routes.py` | `/api/view/*` — inline PDF, slide image carousel, MP4 video streaming for the React SPA content viewers |
| `frontend/quiz_routes.py` | `/api/quiz/*` — generate, fetch, submit, results, by-job (see [Quiz API](quiz.md)) |
| `frontend/quiz_models.py` | Pydantic request models (GenerateQuizRequest, SubmitQuizRequest, AnswerItem) |

## Endpoints

### HTML Pages / SPA Routes

| Endpoint | Method | Auth required | Description |
|----------|--------|---------------|-------------|
| `/` | GET | Yes | Serve the main application UI (React SPA `index.html` if built, else Jinja2) |
| `/login` | GET | No | Serve the login form (React SPA handles routing client-side; Jinja2 fallback serves a form) |
| `/{full_path}` | GET | No | SPA catch-all — returns `index.html` for any path not matched by an API route, enabling React Router client-side navigation |
| `/assets/{path}` | GET | No | Vite static asset passthrough — served without auth challenge so the SPA bundle loads correctly |
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
| `/api/start` | POST | Yes | Start pipeline for a job; `formats` list validated against `{"pdf","ppt","script","video"}` allowlist, returns `{status: running}` |
| `/api/progress/{job_id}` | GET | Yes | Poll progress: `{status, stage, percent, logs, elapsed, warnings}` |
| `/api/cancel/{job_id}` | POST | Yes | Cancel a running job |
| `/api/download/{job_id}/{type}` | GET | Yes | Download output files (pdf, ppt, scripts, videos) |
| `/api/jobs` | GET | Yes | List jobs for the current user (requires JWT + `DATABASE_URL`); `limit` capped at 100; response fields normalised via `_normalize_job()` |
| `/api/jobs/{job_id}` | GET | Yes | Get a single job by 8-char hex `short_id` (falls back to UUID lookup); returns 404 if job does not belong to the authenticated user; response normalised via `_normalize_job()` |

#### Job response shape (normalised)

`GET /api/jobs` and `GET /api/jobs/{job_id}` both return job objects in the shape the React frontend expects, produced by the `_normalize_job()` helper in `frontend/job_routes.py`:

```json
{
  "id": "abc12345",
  "filename": "syllabus.pdf",
  "status": "complete",
  "stage": null,
  "percent": 100,
  "created_at": "2026-03-09T10:00:00",
  "formats": ["pdf", "ppt"]
}
```

Field mapping from DB columns:

| Response field | DB column | Notes |
|----------------|-----------|-------|
| `id` | `short_id` (falls back to `id`) | 8-char hex identifier used in URLs |
| `filename` | first element of `file_names` | `"unknown"` if list is empty |
| `status` | `status` | — |
| `stage` | `current_stage` | `null` if absent |
| `percent` | `progress_pct` | — |
| `formats` | `output_formats` | Comma-separated string split into list |

### View Routes (`/api/view`)

Content viewer endpoints serve generated artifacts inline for the React SPA. All require a completed job (`status == complete`). The `job_id` must match the 8-character hex format enforced by `JOB_ID_RE`.

!!! note "Auth exemption for browser-native viewers"
    `/api/view/` paths are exempted from `AuthMiddleware`. Browser elements such as `<iframe>`, `<video>`, and `<img>` cannot send `Authorization: Bearer` headers. The unguessable 8-character `short_id` acts as a capability token — knowledge of the ID is sufficient for content access. All other API routes still enforce JWT or session auth.

!!! note "DB fallback for completed jobs"
    The view route handler `_get_completed_result()` checks in-memory `ProgressCapture` state first. If the job is not found in memory (e.g. after a server restart), it falls back to the `result_meta` JSONB column in the database. File paths (`pdf_path`, `ppt_path`, `video_dir`, `slide_images`) are stored to `result_meta` on job completion so that view routes continue to work across restarts.

| Endpoint | Method | Auth required | Description |
|----------|--------|---------------|-------------|
| `/api/view/{job_id}/pdf` | GET | No (short_id capability) | Serve generated PDF inline (`Content-Disposition: inline`) for iframe embedding |
| `/api/view/{job_id}/slides` | GET | No (short_id capability) | JSON `{slides: [...], total: N}` — list of `/api/view/{job_id}/slide/{i}` URLs for each existing slide PNG |
| `/api/view/{job_id}/slide/{index}` | GET | No (short_id capability) | Serve individual slide PNG by 1-based index |
| `/api/view/{job_id}/videos` | GET | No (short_id capability) | JSON `{videos: [{name, url}, ...]}` — one entry per MP4 in the job's video directory |
| `/api/view/{job_id}/video/{index}` | GET | No (short_id capability) | Stream MP4 by 0-based index; Starlette `FileResponse` handles HTTP Range requests for HTML5 seeking |

#### Slide listing response

```json
{
  "slides": [
    "/api/view/abc12345/slide/1",
    "/api/view/abc12345/slide/2"
  ],
  "total": 2
}
```

#### Video listing response

```json
{
  "videos": [
    {"name": "topic one", "url": "/api/view/abc12345/video/0"},
    {"name": "topic two", "url": "/api/view/abc12345/video/1"}
  ]
}
```

!!! warning "Incomplete jobs"
    All view endpoints return `404` if the job does not exist, is still running, or has not produced the requested artifact type. The React SPA handles this gracefully by showing an empty state rather than an error.

### Quiz Routes (`/api/quiz`)

All quiz endpoints require JWT authentication. See the [Quiz API reference](quiz.md) for full request/response documentation.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `POST /api/quiz/generate` | POST | Generate a quiz for a completed job; returns existing quiz if one already exists (idempotent) |
| `GET /api/quiz/{quiz_id}` | GET | Fetch quiz with questions (answer fields hidden until attempt submitted) |
| `POST /api/quiz/{quiz_id}/submit` | POST | Submit answers; one attempt per user enforced |
| `GET /api/quiz/{quiz_id}/results` | GET | Detailed score + per-question breakdown |
| `GET /api/quiz/by-job/{job_id}` | GET | List all quizzes for a specific job |

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

Login and registration failures are rate-limited per IP: 5 failures within 15 minutes triggers HTTP 429. The counter resets automatically after 15 minutes. Rate limiting applies to both `POST /api/auth/login` and `POST /api/auth/register`.

### DB-Less Mode

When `DATABASE_URL` is not set (local dev without Neon), auth routes that require a database return `503 Database not available`. The app runs normally in all other respects.

## Security Headers

`SecurityHeadersMiddleware` injects the following headers on every response:

| Header | Value |
|--------|-------|
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `SAMEORIGIN` (allows same-origin `<iframe>` for the PDF viewer) |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Content-Security-Policy` | `default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; media-src 'self'; frame-src 'self'` |

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

Body: {"job_id": "abc123", "formats": ["pdf", "ppt"]}

Response: {"status": "running"}
```

The pipeline runs in a background thread. Progress is tracked via `ProgressCapture`. On start, the endpoint scans the job directory for both `.pdf` and `.pptx` files to locate the uploaded source file.

The `formats` field is validated against the allowlist `{"pdf", "ppt", "script", "video"}`. A non-list value or any format not in the allowlist returns HTTP 422.

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
