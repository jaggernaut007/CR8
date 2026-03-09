# Changelog

All notable changes to CR8 are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html)

---

## [0.5.4] — 2026-03-09 — Quiz Agent + Quiz UI (MCQ, Bloom's Taxonomy, One-Attempt)

### Added — Quiz Pipeline (`backend/pipeline/`)
- `backend/prompts/quiz.py` — `GENERATE_QUIZ` prompt constant; instructs the LLM to produce multiple-choice questions with Bloom's taxonomy level, difficulty rating, correct index, and four distractors per question
- `backend/pipeline/quiz_state.py` — `QuizState` TypedDict: `job_id`, `topics`, `quiz_id`, `questions`, `error`
- `backend/pipeline/agent_quiz.py` — LangGraph node that calls the LLM quiz generator, parses questions, and persists them via `db_client`
- `backend/pipeline/quiz_graph.py` — Standalone LangGraph graph (separate from the main 3-agent pipeline); single node: `agent_quiz`

### Added — Quiz API (`frontend/quiz_routes.py`)
Replaces the 4 previous 501 stub routes with 5 real endpoints:

| Endpoint | Description |
|----------|-------------|
| `POST /api/quiz/start` | Trigger quiz generation for a completed job; returns `{quiz_id}` |
| `GET /api/quiz/{quiz_id}/question/{n}` | Fetch the nth question (0-based index); returns question text and options |
| `POST /api/quiz/{quiz_id}/answer` | Submit an answer; returns `{correct, explanation}` for immediate red/green feedback |
| `GET /api/quiz/{quiz_id}/results` | Final score and per-question breakdown after all questions are answered |
| `GET /api/quiz/attempts` | List all quiz attempts for the authenticated user |

- `frontend/quiz_models.py` — Pydantic models: `StartQuizRequest`, `SubmitAnswerRequest`, `QuizQuestion`, `QuizResult`, `AttemptSummary`

### Added — Database (`backend/services/db_client.py`, `backend/db/schema.sql`)
- 8 new async CRUD functions: `create_quiz`, `get_quiz`, `list_quizzes`, `create_question`, `list_questions`, `create_attempt`, `record_answer`, `get_attempt_results`
- `update_job_result` gains optional `pipeline_data` parameter for structured output metadata
- `backend/db/schema.sql` — `curriculum_scope TEXT` column added to `quizzes` table

### Added — React Quiz UI (`frontend/react-app/src/`)
- `src/api/quiz.ts` — `startQuiz()`, `getQuestion()`, `submitAnswer()`, `getResults()`, `listAttempts()` API functions
- `src/components/quiz/QuestionCard.tsx` — MCQ question card with red/green answer highlighting post-submission
- `src/components/quiz/QuizProgressBar.tsx` — Question N of M progress indicator
- `src/components/quiz/ScoreSummary.tsx` — Final score display with pass/fail styling
- `src/pages/QuizPage.tsx` — Full one-attempt quiz flow: question → answer → next → redirect to results
- `src/pages/QuizResultsPage.tsx` — Score breakdown with per-question correct/incorrect review
- `src/App.tsx` — 2 new routes: `/quiz/:quizId` and `/quiz/:quizId/results`
- `src/pages/ResultsPage.tsx` — `QuizSection` added above download buttons (entry point to start a quiz)

### Added — Playwright E2E Tests
- `e2e/quiz.spec.ts` — 7 new scenarios: start quiz, fetch question, submit answer, view results, progress bar rendering, score summary, QuizSection on ResultsPage

### Test Suite
- 135 new pytest tests (quiz pipeline agent, db_client CRUD, quiz routes, Pydantic models, pipeline data persistence, job validation): 928 → 1063
- 43 new Vitest component tests (QuestionCard, QuizProgressBar, ScoreSummary, QuizPage, QuizResultsPage): 81 → 124
- 7 new Playwright E2E tests (`quiz.spec.ts`): 10 → 17

Total: **1063 pytest** + **124 Vitest** + **17 Playwright E2E** = **1204 tests**

---

## Unreleased — Security Hardening + Crash Fixes (Code Review Wave)

### Security
- `backend/config.py` — Settings validator now fails fast if `JWT_SECRET` is present but shorter than 32 characters, or `OPENAI_API_KEY` is present but shorter than 8 characters. Prevents misconfigured deployments reaching production.
- `frontend/auth_routes.py` — Rate limiting (`check_rate_limit`) now applied to `POST /api/auth/register` in addition to login. Prevents account-creation enumeration and brute-force via registration endpoint.
- `frontend/job_routes.py` — `GET /api/jobs/{job_id}` now enforces ownership: returns 404 when the job's `user_id` does not match the authenticated caller. Previously any authenticated user could fetch any job by ID.
- `frontend/job_routes.py` — `POST /api/start` now validates the `formats` list against an explicit allowlist (`{"pdf", "ppt", "script", "video"}`). Non-list values or unknown format strings return 422.
- `frontend/job_routes.py` — `GET /api/jobs` pagination limit capped at 100. Prevents unbounded result sets from very large `limit` values.
- `backend/services/gcs_client.py` — `job_id` path sanitised before GCS key construction to prevent path traversal via crafted job IDs.

### Data Integrity
- `backend/services/db_client.py` — `completed_at` now set when a job transitions to `complete` or `error` status.
- `backend/services/db_client.py` — Stale-job timeout detection uses `created_at` (immutable) instead of `updated_at`. Prevents perpetually extending the timeout window on long-running or stuck jobs.
- `backend/db/schema.sql` — `ON DELETE CASCADE` added to the `jobs.user_id` foreign key so deleting a user removes their jobs automatically.
- `backend/db/schema.sql` — Index added on `quiz_questions(quiz_id, sort_order)` to speed up ordered question listing.

### Bug Fixes
- `backend/services/video_builder.py` — MoviePy clips now closed in a `try/finally` block inside `_compose_video()`. Prevents file-handle leaks and excess RAM retention when composition fails or is cancelled.
- `backend/services/video_builder.py` — Return type annotation corrected to `list[str | None]` (was `list[str]`). Failed topics produce `None` entries; the old annotation was inaccurate.
- `backend/services/gpu_client.py` — `_do_submit()` now raises `RuntimeError` when the service response is missing `video_job_id` instead of silently returning `None` and crashing later in polling.
- `backend/services/web_search.py` — Tavily API exceptions are caught by `search()` and return `[]` instead of propagating and crashing the Research agent. Error is logged with `exc_info=True`.

### Observability
- `backend/pipeline/agent_ingest.py`, `agent_research.py`, `agent_generate.py` — All `except` blocks that previously only `print()`-ed the error now also call `logger.exception()` so errors appear in structured logs on Cloud Run.
- `backend/services/video_builder.py` — Exception handlers now use `logger.error(..., exc_info=True)` instead of manual `traceback.format_exc()`. Unused `traceback` import removed.

### Code Quality
- `backend/services/ppt_builder.py` — Duplicated PPT fallback code extracted into `_ppt_monolithic_fallback()` helper, eliminating ~60 lines of duplicated logic.
- `backend/services/ppt_builder.py` — Hardcoded `"75%"` figure removed from fallback slide data; replaced with `"Data unavailable"` to avoid surfacing misleading statistics.

### Test Suite
Total: **853 pytest** + **81 Vitest** + **10 Playwright E2E** (unchanged — security and crash fixes covered by existing test suite; no new public interfaces added).

---

## [0.5.3] — 2026-03-09 — Content Viewers (PDF iframe, PPT carousel, HTML5 video player)

### Added — Backend View Endpoints (`frontend/view_routes.py`)
- `GET /api/view/{job_id}/pdf` — serve generated PDF inline (`Content-Disposition: inline`) for iframe embedding
- `GET /api/view/{job_id}/slides` — JSON listing of slide image URLs and total count
- `GET /api/view/{job_id}/slide/{index}` — serve individual slide PNG by 1-based index
- `GET /api/view/{job_id}/videos` — JSON listing of video display names and stream URLs
- `GET /api/view/{job_id}/video/{index}` — stream MP4 by 0-based index; Starlette `FileResponse` handles HTTP Range requests natively for HTML5 seeking
- All view endpoints validate `job_id` format and require job status `complete`

### Added — React Viewer Components
- `ContentTabs` — tab bar switching between PDF / Slides / Video panels
- `PdfViewer` — iframe embedding browser-native PDF rendering (zero new npm deps)
- `PptCarousel` — slide image carousel with prev/next navigation, slide counter, and keyboard arrow key navigation
- `VideoPlayer` — HTML5 `<video>` element with topic selector dropdown
- `ResultsPage` — viewer panels displayed above download buttons

### Changed — Security Headers
- `SecurityHeadersMiddleware`: `X-Frame-Options` changed from `DENY` to `SAMEORIGIN` (allows same-origin iframe for PDF viewer)
- `Content-Security-Policy` extended with `media-src 'self'` (HTML5 video) and `frame-src 'self'` (PDF iframe)

### Fixed — Security
- `frontend/view_routes.py` — CWE-23 path traversal fix: `job_id` validated against `JOB_ID_RE` (8-character hex pattern); all resolved file paths are checked against the outputs root with `Path.resolve()` before serving. Any path escaping the outputs directory returns HTTP 400.

### Test Suite
- 39 new pytest tests in `frontend/tests/test_view_routes.py` (Wave 1); backend total: 795 → 834
- 19 additional pytest tests added post-wave (path traversal edge cases + agent-generated coverage); backend total: 834 → 853
- 27 new Vitest component tests (ContentTabs, PdfViewer, PptCarousel, VideoPlayer + keyboard nav); Vitest total: 42 → 69
- 12 additional Vitest tests added post-wave; Vitest total: 69 → 81
- 5 new Playwright E2E tests in `frontend/react-app/e2e/results.spec.ts`; Playwright total: 5 → 10

Total: **853 pytest** + **81 Vitest** + **10 Playwright E2E** = **944 tests**

---

## [0.5.2] — 2026-03-09 — React SPA Shell (Vite + Tailwind v4 + Tanstack Query + Vitest)

### Added — React SPA Frontend
- `frontend/react-app/` — React 19 + Vite 7 + Tailwind v4 SPA with glassmorphism design system
- `frontend/react-app/src/pages/LoginPage.tsx` — JWT login form with error display and redirect on success
- `frontend/react-app/src/pages/DashboardPage.tsx` — authenticated landing page with recent jobs list
- `frontend/react-app/src/pages/UploadPage.tsx` — drag-and-drop PDF/PPTX upload with format selector
- `frontend/react-app/src/pages/ProgressPage.tsx` — real-time polling via Tanstack Query (2 s interval, stage + percent + log stream)
- `frontend/react-app/src/pages/ResultsPage.tsx` — download buttons for PDF, PPT, scripts, and video ZIP
- `frontend/react-app/src/api/client.ts` — JWT-aware fetch client (attaches `Authorization: Bearer`, auto-refresh on 401)
- `frontend/react-app/src/api/auth.ts` — `login()`, `logout()`, `getMe()` API functions
- `frontend/react-app/src/api/jobs.ts` — centralised types (`Job`, `ProgressResponse`, `UploadResponse`) + API functions for all job routes
- `frontend/react-app/src/context/AuthContext.tsx` — React context providing `user`, `login`, `logout`, `isLoading`
- `frontend/react-app/src/components/Navbar.tsx` — responsive navigation with user display and logout
- `frontend/react-app/src/components/ProtectedRoute.tsx` — React Router guard; redirects to `/login` if unauthenticated
- `frontend/react-app/src/test/setup.ts` — Vitest global setup (jsdom environment, `@testing-library/jest-dom` matchers)
- `frontend/react-app/src/test/test-utils.tsx` — factory-pattern mock auth (`makeUser()`, `renderWithAuth()`, `renderWithQueryClient()`)
- `frontend/react-app/e2e/auth.spec.ts` — 5 Playwright E2E scenarios covering login, protected route guard, logout, and token persistence

### Changed — Test Suite
- 42 Vitest component tests added covering all pages and shared components (LoginPage, DashboardPage, UploadPage, ProgressPage, ResultsPage, Navbar, ProtectedRoute, AuthContext)
- 5 Playwright E2E auth flow tests added for the React SPA
- 7 stale Jinja2 backend tests removed (the Jinja2 UI is superseded by the SPA catch-all); backend test count: 802 → 795
- `/assets/` path prefix added to `AuthMiddleware` allowlist to serve Vite static assets without auth challenge
- `data-testid` attributes added to key interactive elements for reliable E2E selection
- Drag-and-drop upload area test coverage added in Vitest suite

### Changed — SPA Activation
- `frontend/app.py` catch-all (`/{full_path:path}`) now serves the compiled React SPA from `frontend/static/index.html` when the build is present; falls back to Jinja2 404 when absent
- `make build-frontend` compiles the Vite app into `frontend/static/` (runs `npm ci && npm run build` in `frontend/react-app/`)

### Test Suite
Total: **795 pytest** (backend) + **42 Vitest** (component) + **5 Playwright E2E** = 842 tests. Backend reduction: 7 stale Jinja2 tests removed.

---

## [0.5.1] — 2026-03-06 — Foundation: DB + JWT Auth + Route Restructure + Test Optimization

### Added — Database & Auth
- `backend/db/` — asyncpg database layer with 8 tables (users, jobs, quizzes, quiz_attempts, quiz_answers, chat_sessions, chat_messages) + triggers
- `backend/services/db_client.py` — 12 async CRUD functions for user, job, and quiz operations
- `backend/services/auth_service.py` — JWT auth service (PyJWT + bcrypt): register, login, refresh, verify with type enforcement on token claims
- `frontend/middleware.py` — AuthMiddleware, SecurityHeadersMiddleware, rate limiter, session store
- `frontend/auth_routes.py` — JWT register/login/refresh/me/logout + legacy session auth
- `frontend/job_routes.py` — upload, start, progress, cancel, download, jobs list
- `frontend/quiz_routes.py` — 4 stub routes returning 501 (Phase 4)
- `.claude/mcp.json` — Neon MCP config for dev-time database management

### Changed — uv Migration & Route Restructure
- Package manager migrated from pip/venv to `uv` (Astral, v0.10.8); `uv.lock` committed
- `frontend/app.py` split from 693→320 lines (routes extracted to auth_routes, job_routes, quiz_routes)
- SPA catch-all: detects `frontend/static/index.html` at import; serves React SPA or Jinja2 fallback
- `MAX_UPLOAD_SIZE_MB=50` configurable in `backend/config.py` (was hardcoded 20MB)
- Schema expanded: 6→8 tables (added `chat_sessions`, `chat_messages`), `display_name`, `blooms_level`, `correct_index`, `UNIQUE(quiz_id, user_id)`

### Changed — Test Optimization
- Test speed: 171s → 41.55s (4.1x) via pytest-xdist (`-n auto`) + autouse fixtures
- gpu_client tests: 150s → 0.27s (555x) — mocked `time.sleep` and `_get_identity_token`
- New Makefile targets: `test-fast`, `test-parallel`, `build-frontend`, `e2e`
- All docs/agents updated from pip→uv commands

### Added — Research & Agents
- `docs/research/agent-lightning.md` — APO/RL research note
- `docs/research/code-intelligence-tools.md` — code intelligence tools comparison
- `docs/research/pytest-tdd-optimization.md` — pytest speed optimisation
- `docs/research/gitlab-knowledge-graph.md` — GitLab knowledge graph research
- .claude/agents: expanded docs-writer (6 layers), research-assistant (security assessment)
- docs/research/RESEARCH-TEMPLATE.md: added Security Assessment section

### Test Suite
Total: **802 tests passing** (was 626). New: db_client (19), auth_service (12), middleware (80+), auth_routes (49), quiz_routes (12), job_helpers (43).

---

## [0.4.2] — 2026-03-06 — CPU Video Service, 3-Tier Fallback Chain

**Summary**: Adds a CPU-only video microservice (`cpu_video_service/`) as a Tier 3 fallback, completing the 3-tier chain: GPU Primary (europe-west4) → GPU Fallback (europe-west1) → CPU Video (europe-west2). `VideoServiceClient` replaces `GPUVideoClient` (alias kept) and now routes across all three tiers automatically on infrastructure failures. Main container Dockerfile stripped of video dependencies. 626 tests.

### Added
- `cpu_video_service/` — NEW: standalone FastAPI microservice running Kokoro TTS + ffmpeg on CPU. Deployed to Cloud Run with 8 vCPU / 32 GiB. Same API contract as `gpu_service/` (`/health`, `POST /api/v1/video-jobs`, `GET /api/v1/video-jobs/{id}`, `POST /api/v1/video-jobs/{id}/cancel`)
- `cpu_video_service/worker.py` — 4-phase pipeline: GCS download → sequential CPU TTS → parallel libx264 compose → GCS upload. Supports graceful cancellation at phase boundaries
- `cpu_video_service/gcs_client.py` — `CPUGCSClient`: `download_manifest()`, `download_slides()`, `upload_videos()`, `upload_status()`
- `cpu_video_service/config.py` — Pydantic settings: `gcs_bucket`, `kokoro_voice`, `kokoro_lang`, `video_fps`, `video_max_workers`, `max_concurrent_jobs`
- `cpu_video_service/tests/` — 78 tests (19 app, 37 worker, 22 GCS client)
- `Dockerfile.cpu-video` — 2-stage CPU build (no CUDA dependencies)
- `docs/adr/ADR-001-three-tier-video-fallback.md` — Architecture decision record for the fallback design
- `backend/config.py` — `cpu_video_service_url` setting; `should_use_video_service` property (returns `True` when any video service URL is configured)

### Changed
- `backend/services/gpu_client.py` — `GPUVideoClient` renamed to `VideoServiceClient` (backward-compatible alias retained). Now supports 3-tier fallback via `_build_tier_list()`. Updated timeouts: health check 10s, submit 60s. `_try_next_tier()` advances through tiers on `ConnectionError`, `Timeout`, or `HTTPError` (5xx)
- `backend/pipeline/agent_generate.py` — uses `should_use_video_service` (was `should_use_gpu_service`)
- `Dockerfile` — stripped `ffmpeg`, `espeak-ng`, `libreoffice-impress` (video deps moved to `Dockerfile.gpu` and `Dockerfile.cpu-video`; main container no longer runs video locally)

### Test Suite
Total: **626 tests passing** (was 507). New tests cover `cpu_video_service` app/worker/GCS client, and expanded `test_gpu_client.py` (37 tests, was 12) to cover 3-tier fallback and `_try_next_tier()`.

---

## [0.4.1] — 2026-03-05

### Fixed
- move logger placement in `frontend/app.py` to fix E402, update stale test counts

---

## [0.4.0] — 2026-03-04 — Kokoro Video Pipeline, GPU Service, Dual-Service Deployment

**Summary**: Open-source Kokoro TTS video pipeline replaces the HeyGen placeholder. Videos can run locally (CPU/MPS/CUDA) or be offloaded to an NVIDIA L4 GPU microservice on Cloud Run via GCS. Dual-service deployment script, hardware-accelerated encoding, stage-aware ETA, security hardening, and 507-test suite.

### Added — Kokoro Video Pipeline
- `backend/services/script_parser.py` — NEW: parses `[SLIDE N]` markers from video scripts into per-segment lists
- `backend/services/tts_engine.py` — NEW: Kokoro TTS wrapper with lazy `KPipeline`, 24kHz audio, GPU-aware device selection (MPS/CUDA/CPU)
- `backend/services/video_builder.py` — Two-phase pipeline: sequential TTS (shared engine, ~3.4 GB peak) → parallel ffmpeg composition (`VIDEO_MAX_WORKERS=12`). Hardware H.264 encoding (VideoToolbox/NVENC/QSV/AMF/libx264). Per-worker thread control.
- `backend/services/gpu_utils.py` — NEW: `get_torch_device()` (CUDA > MPS > CPU), `get_ffmpeg_encoder()` (probes ffmpeg for hardware encoder support)
- `backend/services/file_parser.py` — `export_slides_as_images()`: PDF via PyMuPDF, PPTX via LibreOffice CLI → pdftoppm
- `backend/config.py` — `kokoro_voice`, `kokoro_lang`, `video_fps`, `video_device`, `video_max_workers`, `hf_token`, `slide_export_dpi` settings
- `VIDEO_PROVIDER=kokoro` — fully open-source, zero-cost video pipeline
- `slide_images: NotRequired[list[str]]` field in `PipelineState`

### Added — Cloud Run GPU Service
- `backend/services/gcs_client.py` — NEW: `GCSVideoClient` for CPU↔GPU data transfer via GCS
- `backend/services/gpu_client.py` — NEW: `GPUVideoClient` HTTP client with identity token auth, progress polling, fallback to secondary GPU region
- `gpu_service/` — NEW: FastAPI GPU microservice (`app.py`, `worker.py`, `config.py`, `gcs_client.py`) running Kokoro TTS + ffmpeg on NVIDIA L4
- `Dockerfile.gpu` — NEW: 3-stage CUDA build (ffmpeg with NVENC → Python deps + pre-cached Kokoro model → runtime)
- `backend/pipeline/agent_generate.py` — `_build_videos_dispatch()`: routes to primary GPU → fallback GPU → local CPU
- `backend/config.py` — `gpu_service_url`, `gpu_fallback_url`, `gcs_bucket` settings; `should_use_gpu_service` computed property
- `deploy.sh` — Multi-service deployment: CPU (europe-west2) + GPU (europe-west4 primary, europe-west1 fallback)

### Added — Frontend & UX
- PPTX upload support — magic byte validation for both PDF and PPTX
- Video checkbox enabled, labelled "Kokoro TTS" (was disabled/HeyGen)
- Yellow warning box for video errors/warnings on completion
- Stage-aware ETA with per-stage time budgets (measured from e2e benchmark)
- `AUTH_PASSWORD` env var for configurable login password (was hardcoded)

### Added — Infrastructure
- `Dockerfile` — `libreoffice-impress` for PPTX→PNG slide export; `ffmpeg`, `espeak-ng`, `poppler-utils`
- `SECURITY.md` — vulnerability disclosure policy
- `backend/evals/README.md` — evaluation framework documentation
- `docs/research/` — research notes for kokoro-tts, moviepy-v2, pymupdf-slide-export, deployment-strategies
- `google-cloud-storage>=2.14`, `kokoro>=0.9`, `moviepy>=2.0`, `soundfile>=0.12` dependencies
- Structured console logging across all backend services
- LangSmith tracing with job metadata (`job_id`, `output_formats`, `file_count`)

### Changed
- `_validate_video_provider()` extracted as shared function (CLI + web use identical logic)
- `logging.basicConfig()` guarded to prevent duplicate entries
- `STAGE_TIME_BUDGETS` calibrated from measured benchmark (Ingest 51s, Research 150s, Generate 140s, Script 14s, Video 1690s)

### Removed
- `_build_kokoro_video()` — superseded by two-phase `_build_kokoro_videos()` pipeline

### Fixed
- `_get_slide_images()` — videos now use generated PPT slides (was falling back to original PDF)

### Test Suite
Total: **507 tests passing** (was 362). Covers GCS/GPU clients, video dispatch, GPU service worker/endpoints, script parser, TTS engine, file parser slide export, PPTX upload, video UI, stage-aware ETA, and video provider validation.

---

## [0.3.0] — 2026-03-03

### Added
- 3 new Claude Code skills in `.claude/skills/`:
  - `/commit-ready` — full CONTRIBUTING.md pre-commit checklist gate (lint, tests, docs, PROGRESS, code review)
  - `/coverage-report` — pytest-cov analysis, ranks modules below 80%, routes weakest to test-writer
  - `/new-feature` — scaffolds services/agents/endpoints with ordered checklist and agent routing
- `pytest-cov>=5.0` added to dev dependencies
- 6 new Claude Code subagents in `.claude/agents/`:
  - `adr-writer` (opus) — writes Architecture Decision Records before structural changes
  - `eval-judge` (opus) — produces SHIP/HOLD/ITERATE verdicts from eval comparison reports
  - `prompt-optimizer` (opus) — iterates on prompts in `backend/prompts/` using eval feedback
  - `test-writer` (sonnet) — writes pytest tests following CR8 mock conventions
  - `debug-detective` (sonnet) — diagnoses and fixes failing tests
  - `docs-writer` (sonnet) — updates `mk-docs/` pages for staged code changes before commits
- Subagent routing table in `AGENTS.md` for automatic dispatch without user prompting
- Commitizen semantic versioning (`commitizen>=3.0`) with conventional-commit format
- `[tool.commitizen]` configuration in `pyproject.toml`
- Pre-commit lint gate (blocks commits with ruff failures) in `.claude/hooks.json`
- Docs-staleness warning hook (warns when backend files staged without doc updates)
- `.claude/hooks/pre-commit-docs-check.sh` — shell script for docs staleness check
- Commitizen usage docs in `mk-docs/getting-started/developer-workflow.md`

---

## [0.2.0] — 2026-03-03

### Added
- Agent-readiness scaffolding: `AGENTS.md`, `PROGRESS.md`, `CLAUDE.local.md`, `feature_list.json`
- `scripts/init.sh` smoke test (ruff + 362 tests + docs build)
- `.claude/agents/code-reviewer.md` (sonnet) and `research-assistant.md` (haiku)
- `.claude/rules/api-standards.md` and `test_standards.md`
- Pre-commit ruff lint hook (Stop + PostToolUse) in `.claude/hooks.json`
- MkDocs documentation site (49 pages, Material theme, `mk-docs/` directory)
- `mk-docs/llms.txt` — machine-readable docs index
- `docs/research/INDEX.md` and `docs/agentic-guide.md`
- `backend/CLAUDE.md` and `frontend/CLAUDE.md` (lazy-loaded subdirectory rules)
- `CONTRIBUTING.md` and directory READMEs

### Fixed
- 34 pre-existing ruff lint errors resolved across codebase

---

## [0.1.0] — 2026-03

### Added
- 3-agent LangGraph pipeline: Ingest → Research → Generate
- Output formats: PDF, PPT, video script, HeyGen AI avatar video
- FastAPI web server (`frontend/`) with bcrypt session authentication on all routes
- 362-test suite with zero real API calls (~27s runtime)
- Evaluation framework: L1 structural judges + L2 LLM judges + A/B comparison CLI
- Docker containerisation + GCP Cloud Run deployment configuration
- Multi-model routing: nano/mini/premium tiers with task-specific temperature presets
- Parallel execution across all three pipeline agents (`ThreadPoolExecutor`)
- Domain-scoped prompts with `curriculum_scope` flowing through entire pipeline
- ChromaDB result caching, map-reduce summarization for long files
- Module validation with retry (up to 2 retries for failed generations)
- Rich PDF rendering: bold, italic, code blocks with Courier font on gray background
- PPT gap analysis builder with 6 slide types and CR8 design tokens
- Slide-synced video script generation (`SCRIPT_FROM_SLIDES` prompt)
