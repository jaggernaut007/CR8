# Changelog

> **See also**: [Services Reference](services/index.md) and [Prompt Templates](agents/prompts.md) — Complete technical reference for all builders, prompts, and eval checks.

## v0.5.5 — Production Bug Fixes (2026-03-13)

### Fixed

- **asyncpg DataError on job completion** — `result_meta` dict was passed raw to asyncpg which expects JSON strings for JSONB columns. Added `json.dumps()` serialization in `db_client.update_job_result()`, matching the pattern already used for `topics`, `gap_summary`, and `modules_md`. This caused `/api/progress` to return 500 after every successful pipeline run.
- **Content-Length corruption on file serving** — Converted `AuthMiddleware` and `SecurityHeadersMiddleware` from Starlette `BaseHTTPMiddleware` to pure ASGI middleware. `BaseHTTPMiddleware` buffers and replays `FileResponse` bodies, which corrupted `Content-Length` headers when serving PDFs, slide images, and videos via `/api/view/` routes.

### Changed

| File | Change |
|------|--------|
| `backend/services/db_client.py` | `result_meta` now serialized with `json.dumps()` before passing to asyncpg |
| `frontend/middleware.py` | Both middleware classes rewritten as pure ASGI (no `BaseHTTPMiddleware`) |

---

## v0.5.4 — Quiz Agent + Quiz UI (2026-03-09)

**Summary**: Adds a dedicated Quiz Agent LangGraph pipeline and a full edX-style quiz experience in the React SPA. The 4 previous 501 stub routes in `quiz_routes.py` are replaced with 5 real endpoints. The quiz flow is one-attempt, enforced at both the API and database layers. Questions carry Bloom's taxonomy labels and difficulty ratings. Test suite grew from 928 pytest / 81 Vitest / 10 E2E to **1063 pytest / 124 Vitest / 17 E2E = 1204 total**.

### Added — Quiz Pipeline

| File | Description |
|------|-------------|
| `backend/prompts/quiz.py` | `GENERATE_QUIZ` prompt — instructs LLM to produce MCQs with Bloom's level, difficulty, correct index, four distractors |
| `backend/pipeline/quiz_state.py` | `QuizState` TypedDict: `job_id`, `topics`, `quiz_id`, `questions`, `error` |
| `backend/pipeline/agent_quiz.py` | LangGraph node: calls LLM generator, parses questions, persists via db_client |
| `backend/pipeline/quiz_graph.py` | Standalone LangGraph graph (separate from main pipeline); single node: `agent_quiz` |

### Added — Quiz API (`frontend/quiz_routes.py`)

Replaces the 4 previous 501 stub routes with 5 real endpoints:

| Endpoint | Description |
|----------|-------------|
| `POST /api/quiz/start` | Trigger quiz generation for a completed job; returns `{quiz_id}` |
| `GET /api/quiz/{quiz_id}/question/{n}` | Fetch the nth question (0-based); question text and options |
| `POST /api/quiz/{quiz_id}/answer` | Submit answer; returns `{correct, explanation}` for immediate feedback |
| `GET /api/quiz/{quiz_id}/results` | Final score and per-question breakdown |
| `GET /api/quiz/attempts` | List all quiz attempts for the authenticated user |

`frontend/quiz_models.py` — Pydantic models: `StartQuizRequest`, `SubmitAnswerRequest`, `QuizQuestion`, `QuizResult`, `AttemptSummary`.

### Added — Database
- 8 new async CRUD functions in `backend/services/db_client.py`: `create_quiz`, `get_quiz`, `list_quizzes`, `create_question`, `list_questions`, `create_attempt`, `record_answer`, `get_attempt_results`
- `update_job_result` gains optional `pipeline_data` parameter
- `backend/db/schema.sql` — `curriculum_scope TEXT` column added to `quizzes` table

### Added — React Quiz UI

| Component / Page | Description |
|-----------------|-------------|
| `src/api/quiz.ts` | API client functions for all 5 quiz endpoints |
| `src/components/quiz/QuestionCard.tsx` | MCQ card with red/green answer highlighting post-submission |
| `src/components/quiz/QuizProgressBar.tsx` | Question N of M progress indicator |
| `src/components/quiz/ScoreSummary.tsx` | Final score with pass/fail styling |
| `src/pages/QuizPage.tsx` | One-attempt quiz flow: question → answer → next → redirect to results |
| `src/pages/QuizResultsPage.tsx` | Score breakdown with per-question correct/incorrect review |
| `src/App.tsx` | 2 new routes: `/quiz/:quizId` and `/quiz/:quizId/results` |
| `src/pages/ResultsPage.tsx` | `QuizSection` added above download buttons |

### Test Suite
- 135 new pytest tests: quiz pipeline agent, db_client CRUD (8 functions), quiz routes, Pydantic models, pipeline data persistence, job validation (928 → 1063)
- 43 new Vitest component tests: QuestionCard, QuizProgressBar, ScoreSummary, QuizPage, QuizResultsPage (81 → 124)
- 7 new Playwright E2E tests in `e2e/quiz.spec.ts` (10 → 17)

---

## v0.5.3 — Content Viewers (2026-03-09)

**Summary**: Inline content viewers embedded in the React SPA ResultsPage. Users can preview generated PDF, browse PPT slides, and watch videos without downloading files. Three-wave delivery: backend view endpoints → React viewer components → keyboard navigation + Playwright E2E. Post-wave path traversal security fix (CWE-23). Test suite grew from 795 pytest / 42 Vitest / 5 E2E to **853 pytest / 81 Vitest / 10 E2E = 944 total**.

### Added — Backend View Endpoints (`frontend/view_routes.py`)

| Endpoint | Description |
|----------|-------------|
| `GET /api/view/{job_id}/pdf` | Serve generated PDF inline (`Content-Disposition: inline`) for iframe embedding |
| `GET /api/view/{job_id}/slides` | JSON `{slides: [...], total: N}` — list of slide image URLs |
| `GET /api/view/{job_id}/slide/{index}` | Individual slide PNG (1-based index) |
| `GET /api/view/{job_id}/videos` | JSON `{videos: [{name, url}, ...]}` — per-topic video listing |
| `GET /api/view/{job_id}/video/{index}` | Stream MP4 (0-based index); Starlette `FileResponse` handles HTTP Range for seeking |

All view endpoints validate `job_id` format and require job status `complete`.

### Added — React Viewer Components

| Component | Description |
|-----------|-------------|
| `ContentTabs` | Tab bar switching between PDF / Slides / Video panels |
| `PdfViewer` | Browser-native PDF rendering via `<iframe>` — zero new npm dependencies |
| `PptCarousel` | Slide image carousel with prev/next, slide counter, keyboard arrow key navigation |
| `VideoPlayer` | HTML5 `<video>` element with topic selector dropdown |
| `ResultsPage` | Viewer panels displayed above download buttons |

### Changed — Security Headers
- `SecurityHeadersMiddleware`: `X-Frame-Options` changed from `DENY` to `SAMEORIGIN` (allows same-origin iframe for PDF viewer)
- `Content-Security-Policy` extended with `media-src 'self'` (HTML5 video) and `frame-src 'self'` (PDF iframe)

### Fixed — Security
- **CWE-23 Path Traversal**: `job_id` validated against 8-character hex regex (`JOB_ID_RE`); all resolved file paths checked against the outputs root using `Path.resolve()` before serving. Paths escaping the outputs directory return HTTP 400.

### Test Suite
- 39 new pytest tests (Wave 1 view routes) + 19 post-wave tests (path traversal edge cases): 795 → 853
- 27 new Vitest tests (viewer components + keyboard nav) + 12 post-wave: 42 → 81
- 5 new Playwright E2E tests (`results.spec.ts`): 5 → 10

---

## v0.5.2 — React SPA Shell (2026-03-09)

**Summary**: Delivered the full React 19 + Vite 7 + Tailwind v4 frontend in three waves. All five pages (Login, Dashboard, Upload, Progress, Results) are wired to the real API via Tanstack Query and a JWT-aware fetch client. Added 42 Vitest component tests and 5 Playwright E2E auth flow tests. Removed 7 stale Jinja2 backend tests. Backend test count: 802 → 795.

### Added — React SPA

| Component | Description |
|-----------|-------------|
| `frontend/react-app/` | React 19 + Vite 7 + Tailwind v4 SPA with glassmorphism design |
| `LoginPage` | JWT login form with error display, redirects to `/dashboard` on success |
| `DashboardPage` | Authenticated landing page with recent jobs list (Tanstack Query) |
| `UploadPage` | Drag-and-drop PDF/PPTX upload with format selector checkboxes |
| `ProgressPage` | Real-time polling every 2 s (Tanstack Query), stage + percent + log stream |
| `ResultsPage` | Download buttons for PDF, PPT, scripts, and video ZIP |
| `api/client.ts` | JWT-aware fetch — attaches `Authorization: Bearer`, auto-refresh on 401 |
| `api/jobs.ts` | Centralised `Job`, `ProgressResponse`, `UploadResponse` types + API functions |
| `AuthContext` | React context: `user`, `login`, `logout`, `isLoading` |
| `ProtectedRoute` | Redirects unauthenticated users to `/login` |
| `Navbar` | Responsive nav with user display and logout |

### Added — Tests

- **42 Vitest component tests** — all pages and shared components
- **5 Playwright E2E tests** — login, protected route guard, logout, token persistence, invalid credentials
- Factory-pattern test utilities: `makeUser()`, `renderWithAuth()`, `renderWithQueryClient()`

### Changed

- `AuthMiddleware` — `/assets/` path prefix added to allowlist so Vite bundles load without auth challenge
- 7 stale Jinja2 backend tests replaced; backend suite reduced from 802 → 795

---

## v0.5.1 — Foundation: DB + JWT Auth + Route Restructure + Test Optimization

**Summary**: Migrated to uv package manager. Added asyncpg database layer (8 tables), JWT auth service (PyJWT + bcrypt), refactored frontend/app.py from 693→320 lines into 4 route modules + middleware. Added SPA catch-all, configurable upload size, and pytest-xdist parallel testing (802 tests in ~42s, 4.1x speedup). Grew test suite from 626 → 802 tests (+176).

---

### Added — Route Modules (Wave 3)

| Module | Purpose |
|--------|---------|
| `frontend/middleware.py` | `AuthMiddleware`, `SecurityHeadersMiddleware`, `get_current_user()` dependency, in-memory rate limiter (5 failures / 15 min per IP), session store |
| `frontend/auth_routes.py` | `/api/auth/*` — JWT register/login/refresh/me/logout + legacy session login |
| `frontend/job_routes.py` | `/api/upload`, `/api/start`, `/api/progress/{job_id}`, `/api/cancel/{job_id}`, `/api/download/{job_id}/{type}`, `/api/jobs`, `/api/jobs/{job_id}` |
| `frontend/quiz_routes.py` | `/api/quiz/*` — stubs returning 501 (reserved for Phase 4) |

`frontend/app.py` is now responsible for app creation, lifespan, CORS/middleware wiring, and health check only. All route logic has moved to the modules above.

### Added — Security (Wave 3)

- **`SecurityHeadersMiddleware`** — Injects `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, and a `Content-Security-Policy` header on every response.
- **`AuthMiddleware`** — Enforces authentication on all paths except `/login`, `/api/auth/login`, `/api/auth/register`, `/health`, and `/static/`. Unauthenticated requests to protected paths receive HTTP 401.
- **CORS scoped** — `allowed_origins` is now read from `settings.allowed_origins` (env var `ALLOWED_ORIGINS`, comma-separated). The wildcard `["*"]` origin has been removed.
- **DB pool lifecycle** — `app.lifespan` initialises an asyncpg connection pool on startup when `DATABASE_URL` is set and closes it cleanly on shutdown. Auth routes that require a DB return `503 Database not available` when the pool is absent (local dev without Neon).

### Added — Auth Routes (Wave 3)

| Endpoint | Description |
|----------|-------------|
| `POST /api/auth/register` | Create account (email + password, min 6 chars); requires `DATABASE_URL`. Returns 201 with `access_token` + sets `cr8_refresh` httponly cookie. |
| `POST /api/auth/login` | JWT mode (email + password): returns access token + refresh cookie. Legacy mode (password only): sets `cr8_session` cookie for Jinja2 UI. |
| `POST /api/auth/refresh` | Issues new access token from `cr8_refresh` cookie. |
| `GET /api/auth/me` | Returns `{user_id, email, role}` for the authenticated caller. |
| `POST /api/auth/logout` | Invalidates session and clears cookies; returns 204. |

Dual auth: `get_current_user()` tries JWT Bearer first, then falls back to the `cr8_session` legacy cookie. JWT access tokens are short-lived; refresh tokens are httponly, path-scoped to `/api/auth/refresh`.

### Added — Playwright E2E Testing (Wave 4)

17 end-to-end scenarios validated via Playwright MCP against the running dev server:

| Scenario group | What was verified |
|----------------|-------------------|
| Health check | `GET /health` returns 200 with `{"status": "ok"}` |
| Security headers | All four security headers present on every response |
| Auth redirect | Unauthenticated requests to `/` redirect to `/login` |
| Login / logout | Correct password issues session; wrong password returns 401; logout clears cookie |
| Upload — valid PDF | PDF accepted; `job_id` returned |
| Upload — invalid file | Non-PDF rejected with HTTP 400 |
| Rate limiting | Six rapid failed login attempts triggers HTTP 429 |
| Quiz stubs | All quiz endpoints return HTTP 501 |
| Job validation | `/api/start` with missing `job_id` returns 422 |
| DB-less mode | Auth routes return 503 when `DATABASE_URL` is absent |

### Changed (Wave 3)

- `frontend/app.py`: reduced from ~693 lines to ~320 lines
- CORS origins: `["*"]` replaced by `settings.allowed_origins` (env-configurable)

### Test Suite — 626 → 687 Tests

| New file | Tests | What it covers |
|----------|-------|----------------|
| `frontend/tests/test_auth_routes.py` | 49 | Register (201, 409, 400, 503, email normalisation), JWT login (200, 401, 429), legacy login, refresh (happy path, invalid token, no cookie), `/me` (JWT Bearer, legacy session, expired), logout (204, session invalidation), `get_current_user` (expired JWT, malformed header) |
| `frontend/tests/test_quiz_routes.py` | 12 | All quiz stub endpoints return 501 with `error` key and "not yet implemented" message |

### Files Changed

| File | Change |
|------|--------|
| `frontend/app.py` | Refactored: ~693 → ~320 lines; routes moved to sub-modules; middleware and CORS wired from new modules |
| `frontend/middleware.py` | New — `AuthMiddleware`, `SecurityHeadersMiddleware`, `get_current_user()`, rate limiter, session store |
| `frontend/auth_routes.py` | New — JWT + legacy auth routes |
| `frontend/job_routes.py` | New — upload/start/progress/cancel/download/jobs routes |
| `frontend/quiz_routes.py` | New — quiz stubs (501) |
| `frontend/tests/test_auth_routes.py` | New — 49 auth tests |
| `frontend/tests/test_quiz_routes.py` | New — 12 quiz stub tests |

---

## [0.4.0] — 2026-03-04 — Kokoro Video Pipeline, GPU Service, Dual-Service Deployment

**Summary**: Open-source Kokoro TTS video pipeline replaces the HeyGen placeholder. Videos can run locally (CPU/MPS/CUDA) or be offloaded to an NVIDIA L4 GPU microservice on Cloud Run via GCS. Dual-service deployment script, hardware-accelerated encoding, stage-aware ETA, security hardening, and 507-test suite.

### Added — Kokoro Video Pipeline
- `backend/services/script_parser.py` — NEW: parses `[SLIDE N]` markers from video scripts into per-segment lists
- `backend/services/tts_engine.py` — NEW: Kokoro TTS wrapper with lazy `KPipeline`, 24kHz audio, GPU-aware device selection (MPS/CUDA/CPU)
- `backend/services/video_builder.py` — Two-phase pipeline: sequential TTS (shared engine, ~3.4 GB peak) → parallel ffmpeg composition (`VIDEO_MAX_WORKERS=12`). Hardware H.264 encoding (VideoToolbox/NVENC/QSV/AMF/libx264). Per-worker thread control.
- `backend/services/gpu_utils.py` — NEW: `get_torch_device()` (CUDA > MPS > CPU), `get_ffmpeg_encoder()` (probes ffmpeg for hardware encoder support)
- `backend/services/file_parser.py` — `export_slides_as_images()`: PDF via PyMuPDF, PPTX via LibreOffice CLI → pdftoppm
- `VIDEO_PROVIDER=kokoro` — fully open-source, zero-cost video pipeline

### Added — Cloud Run GPU Service

```
CPU service (europe-west2, London)          GPU service (europe-west4, Netherlands)
─────────────────────────────────          ────────────────────────────────────────
Pipeline: Ingest → Research → Generate      Receives job via HTTP POST /api/v1/video-jobs
Slide export → GCS upload ──────────────>  Downloads slides from GCS
Poll for completion  <──────────────────── Kokoro TTS + ffmpeg on NVIDIA L4
Download MP4s from GCS <─────────────────  Uploads MP4s to GCS
```

- `backend/services/gcs_client.py` — NEW: `GCSVideoClient` for CPU↔GPU data transfer via GCS
- `backend/services/gpu_client.py` — NEW: `GPUVideoClient` HTTP client with identity token auth, progress polling, fallback to secondary GPU region
- `gpu_service/` — NEW: FastAPI GPU microservice (`app.py`, `worker.py`, `config.py`, `gcs_client.py`)
- `Dockerfile.gpu` — NEW: 3-stage CUDA build (ffmpeg with NVENC → Python deps + pre-cached Kokoro model → runtime)
- `deploy.sh` — Multi-service deployment: CPU (europe-west2) + GPU (europe-west4 primary, europe-west1 fallback)

### Added — Frontend & UX
- PPTX upload support — magic byte validation for both PDF and PPTX
- Video checkbox enabled, labelled "Kokoro TTS" (was disabled/HeyGen)
- Stage-aware ETA with per-stage time budgets (measured from e2e benchmark)
- `AUTH_PASSWORD` env var for configurable login password

### Changed
- `_validate_video_provider()` extracted as shared function (CLI + web use identical logic)
- `STAGE_TIME_BUDGETS` calibrated from measured benchmark (Ingest 51s, Research 150s, Generate 140s, Script 14s, Video 1690s)

### Fixed
- `_get_slide_images()` — videos now use generated PPT slides (was falling back to original PDF)

### Test Suite
Total: **626 tests passing** (was 362). Covers GCS/GPU clients, video dispatch, GPU service worker/endpoints, script parser, TTS engine, file parser slide export, PPTX upload, video UI, stage-aware ETA, and video provider validation.

---

## [0.3.0] — 2026-03-03

### Added

- 6 new Claude Code subagents: `adr-writer` (opus), `eval-judge` (opus), `test-writer` (sonnet), `debug-detective` (sonnet), `prompt-optimizer` (opus), `docs-writer` (sonnet)
- Subagent routing table in `AGENTS.md` for automatic agent dispatch without user prompting
- Commitizen semantic versioning with conventional-commit format enforcement via pre-commit hook
- `CHANGELOG.md` at project root managed by `cz bump --changelog`
- Pre-commit lint gate and docs-staleness warning hook in `.claude/hooks.json`

---

## Unreleased — March 2026 Hardening: Bug Fixes & Comprehensive Test Suite

**Summary**: Fixed 10 production-ready bugs across the eval harness, pipeline agents, and video builder. Grew the test suite from 144 → 362 tests (+218) using modern testing practices: property-based testing with `hypothesis`, snapshot regression testing with `syrupy`, LangGraph graph integration tests, and full mock isolation for all agent tests. Zero real API calls in the full suite.

---

### Bug Fixes

| File | Bug | Fix |
|------|-----|-----|
| `backend/evals/harness/comparator.py` | Per-criterion mean used sum of all scores instead of mean per variant | Fixed to compute per-criterion mean correctly across cases |
| `backend/evals/judges/base_judge.py` | Unparseable judge response returned fake `score=1` | Returns `[]` on parse failure — lets callers handle gracefully |
| `backend/evals/harness/scorer.py` | `compute_weighted_total([])` raised `ZeroDivisionError` | Returns `0.0` for empty list |
| `backend/evals/config.py` | No validation that `DEEPSEEK_API_KEY` was set before judge calls | Added `require_judge_key()` called in `BaseJudge.__init__` |
| `backend/pipeline/agent_ingest.py` | `json.JSONDecodeError` during topic extraction crashed ingest | Fallback to single-topic `"Curriculum Overview"` with warning |
| `backend/pipeline/agent_research.py` | Tavily search futures had no timeout — could hang indefinitely | `future.result(timeout=30)` with per-search exception catch |
| `backend/pipeline/state.py` | `output_formats` field missing from `PipelineState` | Added `output_formats: str` field |
| `backend/run_pipeline.py` | `output_formats` not passed in initial state | Initial state now includes `output_formats` |
| `backend/services/video_builder.py` | `_process_single_video` silently produced corrupt output if status response had no URL | Raises `RuntimeError("No download URL")` on missing URL key |
| `backend/pipeline/agent_generate.py` | `output_formats` read from `settings` instead of `state` | Now reads `state.get("output_formats", settings.output_formats)` |

---

### Test Suite Refactor — 144 → 362 Tests

#### New Test Dependencies

Added to `pyproject.toml` dev extras:

```toml
"syrupy>=4.0",        # snapshot/golden file testing
"hypothesis>=6.100",  # property-based testing
```

#### New Test Files

| File | Tests | What it covers |
|------|-------|----------------|
| `backend/tests/test_bug_fixes.py` | 21 | Regression suite for every bug fixed above |
| `backend/tests/test_structural_checks.py` | 63 | All 3 L1 structural check modules + `_sanitize` property-based |
| `backend/tests/test_eval_harness.py` | 28 | Comparator winner/regression math, scorer L1-only, syrupy snapshots |
| `backend/tests/test_graph_integration.py` | 8 | LangGraph `build_pipeline()`, node wiring, state propagation |
| `backend/tests/test_pipeline_agents.py` | 45 | All 3 agent nodes + `_validate_module`, `_detect_hook_type` helpers |
| `backend/tests/test_services.py` | 13 | `get_llm()` tier routing, mocked Tavily search |

#### Enhanced Existing Tests

| File | Added |
|------|-------|
| `backend/tests/conftest.py` | 7 shared fixtures: `mock_llm`, `base_pipeline_state`, `valid_module_md`, `valid_script`, `valid_ppt_single`, `valid_ppt_full` |
| `backend/tests/test_file_parser.py` | Nonexistent file, empty PDF, unsupported extension edge cases |
| `backend/tests/test_chromadb_store.py` | Custom IDs, metadata, empty collection query, `n_results` limit |

#### Testing Techniques

- **Property-based** (`hypothesis`): `@given(st.text())` generates thousands of inputs for `_sanitize` control-char stripping, `@given(st.text(max_size=1999))` for length invariants
- **Snapshot tests** (`syrupy`): `EvalResult` and `ComparisonResult` field names snapshotted — fails immediately on schema renames or removals
- **LangGraph graph tests**: All agent nodes patched via `unittest.mock.patch` before `build_pipeline()` — verifies wiring and state flow without running real agent logic
- **Full mock isolation**: `ChromaStore`, `get_llm`, `extract_text`, `search`, `build_pdf`, `build_gap_ppt`, `build_videos` replaced with `MagicMock` in all agent tests

See the full [Testing Guide](testing/index.md).

---

### Files Changed

| File | Change |
|------|--------|
| `pyproject.toml` | Added `syrupy>=4.0`, `hypothesis>=6.100` to dev extras |
| `backend/tests/conftest.py` | Added 7 shared fixtures |
| `backend/tests/test_bug_fixes.py` | New — 21 regression tests |
| `backend/tests/test_structural_checks.py` | New — 63 structural + property-based tests |
| `backend/tests/test_eval_harness.py` | New — 28 harness tests with snapshots |
| `backend/tests/test_graph_integration.py` | New — 8 LangGraph tests |
| `backend/tests/test_pipeline_agents.py` | New — 45 agent tests |
| `backend/tests/test_services.py` | New — 13 service tests |
| `backend/tests/test_file_parser.py` | Enhanced with error cases |
| `backend/tests/test_chromadb_store.py` | Enhanced with edge cases |
| `backend/tests/__snapshots__/` | New — syrupy golden files |
| `backend/evals/config.py` | Added `require_judge_key()` |
| `backend/evals/harness/comparator.py` | Per-criterion mean fix |
| `backend/evals/judges/base_judge.py` | Parse failure returns `[]` |
| `backend/pipeline/state.py` | Added `output_formats` field |
| `backend/pipeline/agent_ingest.py` | `JSONDecodeError` fallback |
| `backend/pipeline/agent_research.py` | Search timeout handling |
| `backend/pipeline/agent_generate.py` | Read `output_formats` from state |
| `backend/run_pipeline.py` | Pass `output_formats` in initial state |
| `backend/services/video_builder.py` | URL guard in `_process_single_video` |

---

## Unreleased — Pipeline Optimization: Multi-Model Routing, Token Efficiency, Quality Improvements

**Summary**: Implemented a 3-tier model system (nano/mini/premium) with task-specific temperature, severity-based routing for module generation, filtered per-topic context for scripts (86% token reduction), parallel PDF+PPT build, split PPT structuring, ChromaDB result caching, map-reduce summarization for long files, module quality validation with retry, hook variety enforcement across scripts, and richer PDF rendering with bold/italic/code block support.

---

### Multi-Model Architecture

The pipeline now uses three model tiers with task-specific temperature presets instead of a single model for all tasks:

| Tier | Model | Temperature | Tasks |
|------|-------|-------------|-------|
| Nano | gpt-5-nano | 0.2 | File summarization, topic extraction, PPT executive summary |
| Mini | gpt-5-mini | 0.3 | Gap analysis, moderate/minor module generation, PPT per-topic slides |
| Premium | gpt-5.1 | 0.3-0.55 | Critical module generation (0.3), video scripts (0.55) |

Severity-based routing: Modules for topics with "critical" gap severity use gpt-5.1; "moderate" and "minor" topics use gpt-5-mini. This concentrates premium budget where quality matters most.

---

### Token Optimization

- **Filtered context for scripts**: Each video script now receives only its own topic's module content (~1.5K tokens) instead of all modules (~44K tokens). Saves ~190K premium input tokens per run (86% reduction).
- **Split PPT structuring**: Per-topic slide calls replace one monolithic call, reducing per-call input and improving output quality.
- **ChromaDB result caching**: Vector queries are performed once for all topics and reused across module generation and script generation, eliminating redundant searches.
- **Map-reduce summarization**: Files >15K characters are split into 12K chunks, each summarized independently, then combined. No more truncation.

---

### Speed Improvements

- **Parallel PDF + PPT**: PDF build and PPT LLM structuring now run concurrently when both formats are requested.
- **Video concurrency**: `max_workers` increased from hardcoded 2 to configurable 4 (via `VIDEO_MAX_WORKERS`).
- **Map-reduce summarization**: Long files are processed in parallel chunks instead of being truncated.

---

### Quality Improvements

- **Module validation**: Generated modules are checked for required sections (`## Module Overview`, `## Learning Objectives`, `## Core Content`, `## Key Takeaways`) and minimum character count (2000). Failed modules are retried up to 2 times.
- **Hook variety enforcement**: Thread-safe tracking of used hook types across scripts. Each script receives guidance emphasizing unused hook types to prevent all scripts from using the same opening style.
- **Severity-based routing**: Critical topics get premium model quality; the research agent now outputs a `severity` field (`critical`/`moderate`/`minor`) in gap analysis.
- **Richer PDF rendering**: Bold (`**text**`) and italic (`*text*`) now render with actual font style changes instead of being stripped. Triple-backtick code blocks render with Courier font on a light gray background.

---

### New/Modified Files

| File | Change |
|------|--------|
| `backend/config.py` | Added `openai_model_premium`, `openai_model_nano`, temperature presets, `video_max_workers` |
| `backend/services/llm.py` | 4-tier model support (`nano`/`mini`/`full`/`premium`) with optional temperature override |
| `backend/pipeline/agent_ingest.py` | Map-reduce summarization for long files, switched to nano model |
| `backend/prompts/ingest.py` | Added `SUMMARIZE_CHUNK` and `REDUCE_SUMMARIES` prompts |
| `backend/pipeline/agent_research.py` | Temperature override for gap analysis |
| `backend/prompts/research.py` | Added `severity` field to gap analysis JSON output |
| `backend/pipeline/agent_generate.py` | ChromaDB caching, severity routing, filtered context, module validation/retry, parallel PDF+PPT, split PPT structuring, hook variety enforcement |
| `backend/prompts/ppt.py` | Added `STRUCTURE_SINGLE_TOPIC_SLIDE` and `STRUCTURE_EXECUTIVE_SUMMARY` prompts |
| `backend/services/pdf_builder.py` | Rich text rendering (bold/italic), code block rendering |
| `backend/services/video_builder.py` | Configurable `max_workers` parameter |
| `Docs/OpenAI_Model_Research.md` | New — model pricing, pipeline task-to-model matrix, token budget analysis |

---

## Unreleased — Gap Analysis PowerPoint, Chained Generation Flow, Slide-Synced Scripts

**Summary**: Added PowerPoint generation for gap analysis, implemented a chained generation flow (PDF → PPT → Script → Video) where each output builds on the previous, and added a slide-synced video script that maps one narration section per PPT slide. UI updated with dependency-enforcing checkboxes.

---

### Chained Generation Flow

Outputs are now generated in a dependency chain instead of independently:

```
modules_md ──→ PDF (ground truth)
                ↓
PDF content + research/gaps ──→ PPT (structured around PDF chapters)
                                 ↓
PPT slides + PDF + research ──→ Video Script (one section per slide)
                                  ↓
                             Script ──→ Video (HeyGen API)
```

**Key behaviors**:
- **PDF** is always generated first as the ground truth
- **PPT** follows the PDF's chapter order, enriching each topic with gap analysis and research data
- **Video Script** is structured around PPT slides (`[SLIDE N: title]` sections), with narration content drawn from both the PDF modules and research data
- **Fallback**: If PPT is not selected but scripts are, the old per-module script generation is used

---

### Gap Analysis PowerPoint Builder

New `backend/services/ppt_builder.py` generates professional widescreen (16:9) `.pptx` files using `python-pptx`.

**Slide types** (6 types, in order):

| # | Slide | Visual Elements |
|---|-------|----------------|
| 1 | Title | Dark navy background, white title, accent line, date |
| 2 | Executive Summary | KPI callout boxes (total gaps + topics analyzed), critical gaps list |
| 3 | Severity Overview | Scorecard rows with colored severity badges (red/orange/green) |
| 4–N | Topic Gap Detail | Two-column: curriculum vs. industry, impact dots, recommendation strip |
| N+1 | Recommendations | Priority badges with affected topics |
| N+2 | Closing | Dark navy background, next steps |

**Design tokens**: Matches the existing CR8 web UI palette (`#1a1a2e` dark navy, `#4361ee` medium blue). Uses Calibri font, severity color coding (critical=red, moderate=orange, minor=green), and shape-based visual elements (rounded rectangles, ovals, header bars).

---

### Slide-Synced Video Script

New `SCRIPT_FROM_SLIDES` prompt in `backend/prompts/video.py` takes three inputs:
- PPT slide structure (defines script ordering)
- PDF module content (for rich narration)
- Research/gap analysis data (for industry context)

Output format:
```
[SLIDE 1: Title]
<spoken narration>

[SLIDE 2: Executive Summary]
<spoken narration>

[SLIDE 3: Topic Name - Key Gaps]
<spoken narration>
...
```

---

### UI Updates

**Format dependency chain** enforced in `frontend/templates/index.html`:
- Checking "Script" auto-checks "PPT" (scripts depend on PPT)
- Checking "Video" auto-checks both "PPT" and "Script"
- Unchecking "PPT" auto-unchecks "Script" and "Video"
- Labels show hints: `PDF → PPT → Script → Video`

**New format option**: "Gap Analysis PowerPoint (.pptx)" checkbox with hint "Based on PDF + research"

---

### New Files

| File | Purpose |
|------|---------|
| `backend/services/ppt_builder.py` | PowerPoint generation with 6 slide types, shapes, badges |
| `backend/prompts/ppt.py` | `STRUCTURE_GAP_SLIDES` — LLM prompt for PDF+gap → slide JSON |

### Modified Files

| File | Change |
|------|--------|
| `backend/prompts/video.py` | Added `SCRIPT_FROM_SLIDES` prompt for slide-synced scripts |
| `backend/pipeline/state.py` | Added `ppt_path: str` to `PipelineState` |
| `backend/pipeline/agent_generate.py` | Chained flow: PDF→PPT→Script, `_generate_script_from_slides()`, `_build_fallback_slide_data()` |
| `backend/run_pipeline.py` | Added `"ppt"` to `VALID_FORMATS`, `ppt_path` to initial state |
| `frontend/app.py` | Added PPT to `_collect_output_files()` and download route |
| `frontend/templates/index.html` | PPT checkbox, dependency chain JS, hint labels |

---

## Unreleased — Dev Server, Dependency Upgrades, ChromaDB Fix

**Summary**: Added `make dev` target for development, upgraded langchain/langgraph/chromadb dependencies to latest versions, and fixed ChromaDB version incompatibility issue.

---

### Makefile

- Added `dev` target: `uvicorn frontend.app:app --reload --host 0.0.0.0 --port 8000` (binds to all interfaces for easier testing)

### Dependency Upgrades

Upgraded core dependencies to resolve import errors:
- `langchain-core` → 1.2.14
- `langgraph` → 1.0.9
- `langchain` → 1.2.10
- `langchain-openai` → 1.1.10
- `langchain-text-splitters` → 1.1.1
- `chromadb` → 1.1.1

### ChromaDB Version Fix

The existing `chroma_db/` directory was created by ChromaDB ~0.5.x and was incompatible with the upgraded 1.1.x Rust-based storage engine (`PanicException: range start index out of range`). Fix: cleared stale database with `make clean` — data is rebuilt on next pipeline run since it's derived from uploaded source files.

### Files Changed

| File | Change |
|------|--------|
| `Makefile` | Added `dev` target |
| `README.md` | Added `make dev` docs, ChromaDB troubleshooting |

---

## Unreleased — FastAPI Web Frontend, ProgressCapture, and Frontend Test Suite

**Summary**: Added a minimal FastAPI web UI for uploading PDFs, selecting output formats, tracking pipeline progress in real time, and downloading generated files. Includes `run_job()` programmatic entry point, `ProgressCapture` stdout interception, and 70 new tests.

---

### FastAPI Web Frontend

New `frontend/` package provides a single-page web interface served by FastAPI + uvicorn.

**Server** (`frontend/app.py`):
- `GET /` — serves `index.html` via `HTMLResponse`
- `POST /api/upload` — accepts PDF upload, saves to `uploads/<job_id>/`, returns `{job_id, filename}`
- `POST /api/start` — validates formats, checks HeyGen keys if video requested, launches pipeline via `asyncio.to_thread()`, returns `{status: running}`
- `GET /api/progress/{job_id}` — returns `{status, stage, percent, logs[], elapsed, files[]}`
- `GET /api/download/{job_id}/{file_type}` — `FileResponse` for PDF, zipped scripts/videos
- Uses `asynccontextmanager` lifespan pattern (replaces deprecated `@app.on_event`)
- Single job at a time enforced (prototype scope)

**ProgressCapture class** (thread-safe via `threading.Lock`):
- Redirects `sys.stdout` in the pipeline thread to capture all `print()` output
- Tees to original stdout so console logging still works
- Parses `[Ingest]`, `[Research]`, `[Generate]`, `[Script]`, `[Video]` stage prefixes
- Computes progress % using stage weights: Ingest 15%, Research 50%, Generate 25%, Script 8%, Video 2%
- Interpolates sub-step progress from `Topic X/Y` and `Module X/Y` patterns
- `get_state()` returns capped logs (last 30 lines), elapsed time, file list on completion

**UI** (`frontend/templates/index.html`):
- Three states: Upload & Configure → Processing → Complete
- Drop zone / file picker for PDF upload
- Format checkboxes: PDF (always on), Script (optional), Video (disabled by default with "Requires HeyGen API keys" hint)
- Progress bar with stage label, elapsed/estimated time, scrolling log area
- Polls `/api/progress` every 3s via `fetch()`
- Download buttons for PDF (direct), scripts (.zip), videos (.zip)
- Inline CSS + vanilla JS, no build step, max-width 640px centered layout

---

### Programmatic Pipeline Entry Point

**`backend/run_pipeline.py`** — new `run_job()` function:
- Extracts core pipeline invocation into a reusable function callable by the web frontend
- Validates format strings against `VALID_FORMATS` set
- Checks all three HeyGen env vars if video format requested
- Sets `settings.output_formats` before invoking pipeline
- Generates unique `job_id` per run
- Existing CLI `main()` unchanged

---

### Configuration Fix

**`backend/config.py`**:
- Added `"extra": "ignore"` to `model_config` so unknown `.env` keys (e.g., `gemini_api_key`) don't cause `ValidationError`

---

### New Dependencies

**`pyproject.toml`**:
- `fastapi>=0.115` — Async web framework
- `uvicorn[standard]>=0.34` — ASGI server
- `python-multipart>=0.0.9` — Required for FastAPI `UploadFile`
- `httpx>=0.27` (dev) — Required by FastAPI `TestClient`

---

### Makefile

- Added `serve` target: `uvicorn frontend.app:app --reload --port 8000`
- Port 8000 (macOS uses port 5000 for AirPlay)

---

### Test Suite (70 New Tests)

**`backend/tests/test_run_pipeline.py`** (10 tests):
- `TestRunJobValidation`: rejects invalid formats, accepts all valid formats, video requires all 3 HeyGen keys
- `TestRunJobPipelineInvocation`: sets output_formats on settings, correct initial state shape, returns pipeline result, generates unique job IDs

**`frontend/tests/test_progress_capture.py`** (32 tests):
- `TestProgressCaptureInit`: initial status, percent, stage, logs, result, error
- `TestGetState`: required keys, elapsed time, files on complete, error on error, logs capped at 30
- `TestStageTransitions`: Ingest/Research/Generate/Script/Video parsing, unknown prefix ignored, sequential transitions
- `TestSubStepProgress`: Topic X/Y interpolation for Research/Generate/Ingest, percent capped at 99
- `TestWriteBehavior`: tees to original stdout, appends to logs, multiline splitting, empty/whitespace ignored, flush
- `TestThreadSafety`: concurrent writes (4 threads × 100 writes), concurrent read+write

**`frontend/tests/test_api.py`** (28 tests):
- `TestIndexRoute`: 200 status, HTML content-type, page title, upload elements, format checkboxes, video disabled
- `TestUploadEndpoint`: PDF accepted with job_id, file saved to disk, rejects non-PDF/docx/no-file
- `TestStartEndpoint`: missing job_id, nonexistent job, launches pipeline (mocked), rejects concurrent job, allows after completion, defaults to pdf format
- `TestProgressEndpoint`: unknown job 404, running/complete/error states
- `TestDownloadEndpoint`: unknown job 404, incomplete job 404, PDF download, scripts zip, videos zip, nonexistent type 404, missing file 404

**Total at this release**: 144 tests (74 backend + 70 frontend). See March 2026 hardening entry for the current count of 362 tests.

---

### Files Changed

| File | Change |
|------|--------|
| `frontend/app.py` | New — FastAPI server + ProgressCapture |
| `frontend/templates/index.html` | New — Single-page web UI |
| `frontend/__init__.py` | New — Package init |
| `frontend/tests/__init__.py` | New — Test package init |
| `frontend/tests/test_api.py` | New — 28 endpoint tests |
| `frontend/tests/test_progress_capture.py` | New — 32 ProgressCapture tests |
| `backend/run_pipeline.py` | Added `run_job()` function + `VALID_FORMATS` |
| `backend/config.py` | Added `"extra": "ignore"` to model_config |
| `backend/tests/test_run_pipeline.py` | New — 10 tests for `run_job()` |
| `pyproject.toml` | Added fastapi, uvicorn, python-multipart, httpx; added `frontend/tests` to testpaths |
| `Makefile` | Added `serve` target |

---

## Unreleased — Curriculum/Gap Sections, Parallelization, Domain Scoping, and Test Hardening

**Summary**: PDF chapters now explicitly show curriculum coverage and identified gaps with tagged learning objectives and structured takeaways. Also includes major performance improvement through concurrent execution, domain-scoped prompts, enriched topic extraction, and a comprehensive PDF builder test suite.

---

### Curriculum Coverage & Gap Sections in PDF

Each generated chapter now includes two new sections and revised existing sections to clearly surface what the original slides cover and what gaps exist.

**New sections** (added before Learning Objectives):
- **Curriculum Coverage** — summarizes what the original course materials teach about the topic, drawn only from curriculum content
- **Identified Gaps** — describes gaps between curriculum and industry demands, with explanations of why each gap matters

**Revised sections**:
- **Learning Objectives** — each objective is now tagged as `(Curriculum)` or `(Gap)` to indicate whether it addresses course content or an identified gap
- **Key Takeaways** — increased to 7-10 bullets, structured in three groups: `Curriculum:` (core knowledge), `Gap:` (what to learn beyond the course), `Integration:` (how both connect in practice)

**Files changed**:
- `backend/prompts/generate.py` — complete rewrite of `GENERATE_MODULE` prompt (5 sections → 7 sections)
- `backend/pipeline/agent_generate.py` — now passes `key_techniques` from the topic dict to the prompt
- `backend/tests/test_pdf_builder.py` — added test for the new 7-section markdown format

---

### Parallelization (All Agents)

All three pipeline agents now process work concurrently using `ThreadPoolExecutor`, controlled by a new `max_workers` setting (default: 4).

**Config** (`backend/config.py`):
- Added `max_workers: int = 4` setting for controlling thread pool size across agents

**Agent 1 — Ingest** (`backend/pipeline/agent_ingest.py`):
- File summarization now runs in parallel — each file is summarized concurrently instead of sequentially
- Extracted `_summarize_file()` as a standalone function to support parallel execution

**Agent 2 — Research** (`backend/pipeline/agent_research.py`):
- All topics are researched in parallel instead of one-by-one
- Within each topic, the two web searches (job skills + trends) also run in parallel (nested `ThreadPoolExecutor` with 2 workers)
- Extracted `_research_topic()` as a standalone function
- Result ordering is preserved using index-based slot assignment

**Agent 3 — Generate** (`backend/pipeline/agent_generate.py`):
- All learning modules are generated in parallel
- Extracted `_generate_module()` as a standalone function
- Result ordering preserved so PDF chapters match the original topic order

**Impact**: Previously ~29 minutes for a single slide file with 15 topics (all sequential API calls). Parallelization significantly reduces wall-clock time since most of the runtime is spent waiting on API responses.

---

### Domain Scoping

A new `curriculum_scope` field flows through the entire pipeline to keep all analysis and content generation strictly within the curriculum's domain. This prevents the LLM from drifting into unrelated technologies or tangential topics.

**State** (`backend/pipeline/state.py`):
- Added `curriculum_scope: str` — a one-sentence description of the curriculum's domain boundaries
- Topics now carry richer metadata: `key_techniques` (list of specific methods/algorithms) and `domain_context` (broader subject area framing)

**Pipeline runner** (`backend/run_pipeline.py`):
- `curriculum_scope` initialized as empty string in the starting state

**Ingest prompt** (`backend/prompts/ingest.py`):
- `EXTRACT_TOPICS` now asks the LLM to determine the overall curriculum scope before extracting topics
- Topics must now include `key_techniques` (3-8 specific techniques from the source material) and `domain_context`
- Added explicit instruction: "Your analysis must stay strictly within what the source material actually covers"
- Return format changed from `{"topics": [...]}` to `{"curriculum_scope": "...", "topics": [...]}`

**Research prompt** (`backend/prompts/research.py`):
- Added `SCOPE CONSTRAINT` section that explicitly forbids introducing concepts from outside the curriculum's domain
- Added `{key_techniques}` and `{curriculum_scope}` template variables
- Gap analysis now focuses on: Are the taught techniques still current? What practical skills for THESE techniques does industry expect? What alternative approaches to the SAME PROBLEM does industry prefer?
- Changed wording from generic "industry demands" to "what industry wants WITHIN this specific domain"

**Generate prompt** (`backend/prompts/generate.py`):
- Added scope instruction: "This module is part of a curriculum on '{curriculum_scope}'. All content must stay within this domain."
- All section instructions now reference `{topic_name}` specifically instead of generic phrasing
- Industry Context section explicitly says "Do NOT discuss unrelated industry trends or technologies outside the scope of {topic_name}"
- Added `{curriculum_scope}` template variable

**Agent changes**:
- `agent_ingest.py`: Now extracts `curriculum_scope` from LLM response and passes it in state
- `agent_research.py`: Passes `curriculum_scope` to gap analysis prompt; uses `key_techniques` and `domain_context` from topics for more targeted web searches
- `agent_generate.py`: Passes `curriculum_scope` to module generation prompt

---

### Improved Web Search Queries (Research Agent)

Search queries are now more targeted using the enriched topic metadata:

**Before**:
```
"{topic_name} job requirements skills 2025 2026"
"{topic_name} industry trends applications 2025 2026"
```

**After**:
```
"{technique_str} skills applications in {domain_ctx} 2025 2026"
"{topic_name} latest developments alternatives in {domain_ctx} 2025 2026"
```

Where `technique_str` is the first 4 key techniques and `domain_ctx` is the topic's domain context. This produces more relevant search results that stay within the curriculum's domain.

---

### PDF Builder Fix

**`backend/services/pdf_builder.py`**:
- The PDF title on the cover page is now passed through `_sanitize()` to prevent `UnicodeEncodeError` when the title contains smart quotes or other non-latin-1 characters

---

### Test Suite Expansion

**`backend/tests/test_pdf_builder.py`**: Expanded from 1 basic test to a comprehensive suite covering edge cases that arise from LLM-generated content.

New test categories:
- **Baseline**: Valid PDF with standard modules, correct structure and magic bytes
- **Unicode/encoding**: Smart quotes, em dashes, bullets, accented characters, CJK fallback, emoji fallback, mixed scripts
- **Malformed markdown**: Unclosed formatting, deeply nested headers, raw HTML tags, excessive blank lines
- **Edge cases**: Empty module content, very long content (20k+ chars), single topic, many topics (30+), empty topic names/descriptions
- **Markdown rendering**: Inline bold/italic, numbered lists, code blocks, blockquotes, link formatting
- **Section handling**: Missing sections, extra/unexpected sections, duplicate section headers
- **Special characters**: Backslashes, percent signs, curly braces, angle brackets, null bytes, tabs, form feeds
- **Title edge cases**: Very long titles, titles with special characters
- **Structural**: Module count mismatch (more/fewer modules than topics)

Helper utilities added:
- `_assert_valid_pdf(path, min_size)` — validates file existence, size, and PDF magic bytes
- `_build(tmp_path, topics, modules, title)` — shortcut for building test PDFs

---

### Files Changed

| File | Change |
|------|--------|
| `backend/config.py` | Added `max_workers: int = 4` |
| `backend/pipeline/state.py` | Added `curriculum_scope` field, expanded topic type annotation |
| `backend/run_pipeline.py` | Initialize `curriculum_scope` in starting state |
| `backend/pipeline/agent_ingest.py` | Parallel file summarization, extract `curriculum_scope` |
| `backend/pipeline/agent_research.py` | Parallel topic research with nested parallel web searches |
| `backend/pipeline/agent_generate.py` | Parallel module generation, pass `curriculum_scope` to prompt |
| `backend/prompts/ingest.py` | Richer topic extraction with scope, techniques, domain context |
| `backend/prompts/research.py` | Domain-scoped gap analysis with key techniques |
| `backend/prompts/generate.py` | Domain-scoped module generation |
| `backend/services/pdf_builder.py` | Sanitize title on cover page |
| `backend/tests/test_pdf_builder.py` | Expanded from 1 to 20+ rigorous tests |
