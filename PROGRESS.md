# PROGRESS.md
<!-- Agent cross-session memory. Read at the start of every session.
     Updated at the end of every session using the session-handoff skill. -->

## Current Status
**Last updated:** 2026-03-09
**Overall project phase:** v0.5.3 complete — post-release security hardening and crash fixes applied
**Current version:** v0.5.3

## What's Working
- Full 3-agent pipeline end-to-end (Ingest → Research → Generate)
- All output formats: PDF, PPT, video script
- **Kokoro TTS local video pipeline** (`VIDEO_PROVIDER=kokoro`) — slides + voiceover MP4
- **3-tier video service fallback** — GPU Primary (europe-west4) → GPU Fallback (europe-west1) → CPU Video (europe-west2). Tier fallback triggers on infrastructure failures only (ConnectionError, Timeout, 5xx)
- **`VideoServiceClient`** (renamed from `GPUVideoClient`, alias kept) — submits to first reachable tier, stays on that tier for polling
- **CPU Video Service** (`cpu_video_service/`) — standalone FastAPI microservice running Kokoro TTS on CPU + ffmpeg libx264. 8 vCPU / 32 GiB Cloud Run. Same API contract as GPU service
- **GCS data transfer** — `GCSVideoClient` (upload slide PNGs + manifest, download MP4s, cleanup)
- **`should_use_video_service`** property on `Settings` — replaces `should_use_gpu_service` for dispatch decisions
- **Main Dockerfile stripped of video deps** — `ffmpeg`, `espeak-ng`, `libreoffice-impress` removed from main container; video runs in dedicated service containers
- **Video checkbox enabled in UI** (Kokoro TTS, was previously disabled/labelled HeyGen)
- **PPTX upload support** — drag-drop zone accepts both PDF and PPTX; magic byte validation
- **Structured console logging** — `logging.basicConfig()` guarded in `config.py`; all backend services log with timestamps
- **Video error/warning surfacing** — `ProgressCapture` captures `[Video] ERROR:` and `[Video] WARNING:` lines; UI shows yellow warning box on completion
- **Configurable login password** — `AUTH_PASSWORD` env var (default: `CR8-AI`); no longer hardcoded
- **Unified video provider validation** — `_validate_video_provider()` shared between CLI and web
- 853-test suite — all passing, ruff clean, pytest-xdist parallel (~42s)
- **Video slides from generated PPT** (was: original PDF) — fixed `_get_slide_images()` bug
- **Two-phase video pipeline** — sequential TTS (shared engine) → parallel ffmpeg composition
- **GPU acceleration** — MPS/CUDA for TTS, hardware H.264 encoding (VideoToolbox/NVENC/QSV/AMF), per-worker thread control
- **Stage-aware ETA** — per-stage time budgets replace linear extrapolation
- Authentication (bcrypt session auth on all protected routes)
- Docker + GCP Cloud Run deployment
- Evaluation framework (L1 structural + L2 LLM judges, A/B comparison CLI)
- MkDocs documentation site (55 pages, Material theme)
- Agent-readiness scaffolding complete (AGENTS.md, skills, hooks, rules, subagents)
- **docs-writer agent expanded** — now covers 6 documentation layers (mk-docs, CHANGELOG, Loop Intelligence, AGENTS.md counts, PROGRESS.md, llms.txt); Playwright MCP for visual page verification; Sequential Thinking MCP for planning large updates
- **Security hardening (post-v0.5.3)** — Settings validator rejects weak JWT_SECRET/OPENAI_API_KEY at startup; rate limiting on /register; job ownership enforcement on GET /api/jobs/{id}; formats allowlist on /api/start; pagination cap on /api/jobs; GCS path sanitisation
- **Crash resilience** — MoviePy clips released in try/finally; Tavily errors return [] instead of crashing Research agent; GPU client validates video_job_id in submit response
- **Observability** — All pipeline agent exception handlers now call logger.exception(); video_builder uses exc_info=True throughout
- **research-assistant agent now security-aware** — mandatory security assessment on new dependencies (CVE scan, license audit, maintenance health, dependency tree, supply chain risk); Sequential Thinking for evaluating trade-offs
- **RESEARCH-TEMPLATE.md security section** — standardised Security Assessment table with SAFE/WARNING/BLOCK verdict; research notes without a security section are now considered incomplete
- LangSmith tracing opt-in with metadata (job_id, output_formats, file_count)
- SECURITY.md vulnerability disclosure policy
- `slide_images` field is `NotRequired[list[str]]` in `PipelineState` — correctly optional
- `docs/adr/ADR-001-three-tier-video-fallback.md` — architecture decision record

## v0.5.3 Sprint (2026-03-09 Session)
> Content Viewers — inline PDF, PPT slide carousel, HTML5 video player

### Wave 1: Backend View Endpoints (COMPLETE)
- `frontend/view_routes.py` — 5 new endpoints:
  - `GET /api/view/{job_id}/pdf` — inline PDF for iframe (`Content-Disposition: inline`)
  - `GET /api/view/{job_id}/slides` — slide image listing JSON
  - `GET /api/view/{job_id}/slide/{index}` — individual slide PNG
  - `GET /api/view/{job_id}/videos` — video listing JSON
  - `GET /api/view/{job_id}/video/{index}` — MP4 streaming with Range support
- `SecurityHeadersMiddleware` update — `SAMEORIGIN`, `media-src 'self'`, `frame-src 'self'`
- `frontend/tests/test_view_routes.py` — 39 new pytest tests (795 → 834 backend total)

### Wave 2: React Viewer Components (COMPLETE)
- `PdfViewer` — iframe-based, browser native PDF rendering
- `PptCarousel` — slide image navigation with prev/next + counter
- `VideoPlayer` — HTML5 `<video>` with topic selector dropdown
- `ContentTabs` — tab bar switching between PDF/Slides/Video
- `ResultsPage` — viewer panels integrated above download buttons
- 24 new Vitest component tests (42 → 66 Vitest total)

### Wave 3: Polish + E2E (COMPLETE)
- Keyboard navigation — arrow keys for PPT carousel
- 5 new Playwright E2E tests in `frontend/react-app/e2e/results.spec.ts` (5 → 10 total)
- 3 new Vitest keyboard navigation tests (66 → 69 Vitest total)

### Post-Wave: Path Traversal Security Fix (COMPLETE)
- `frontend/view_routes.py` — CWE-23 path traversal fix: `job_id` validated against `JOB_ID_RE` (8-char hex), all file paths resolved with `Path.resolve()` and checked against the outputs root before serving
- Additional agent-generated tests for path validation edge cases

### Test Counts (v0.5.3 final)
- **853 pytest** backend tests (was 795, +39 view route tests + 19 additional post-wave tests)
- **81 Vitest** component tests (was 42, +27 viewer component + keyboard nav tests + 12 additional)
- **10 Playwright** E2E tests (was 5, +5 content viewer tests)

---

## Security Hardening + Crash Fixes (2026-03-09 Code Review Session)
> Comprehensive code review found 16 critical issues and 51 warnings; all fixes applied.

### Security Fixes (COMPLETE)
- `backend/config.py` — Settings validator (`_validate_required_secrets`) fails fast on weak `JWT_SECRET` (< 32 chars) or invalid `OPENAI_API_KEY` (< 8 chars)
- `frontend/auth_routes.py` — Rate limiting now covers `/register` endpoint (was login-only); prevents account-enumeration brute force
- `frontend/job_routes.py` — `GET /api/jobs/{job_id}` enforces job ownership; unauthenticated or cross-user access returns 404
- `frontend/job_routes.py` — `POST /api/start` validates `formats` against explicit allowlist `{"pdf", "ppt", "script", "video"}`
- `frontend/job_routes.py` — Pagination `limit` capped at 100 on `GET /api/jobs`
- `backend/services/gcs_client.py` — `job_id` sanitised before GCS key construction (path traversal prevention)

### Data Integrity Fixes (COMPLETE)
- `backend/services/db_client.py` — `completed_at` now set on job completion/error
- `backend/services/db_client.py` — Stale-job timeout uses `created_at` (immutable) not `updated_at`
- `backend/db/schema.sql` — `ON DELETE CASCADE` on `jobs.user_id` FK
- `backend/db/schema.sql` — Index on `quiz_questions(quiz_id, sort_order)`

### Crash Fixes (COMPLETE)
- `backend/services/video_builder.py` — MoviePy clips closed in `try/finally` in `_compose_video()` (file handle + RAM leak fix)
- `backend/services/video_builder.py` — Return type corrected to `list[str | None]`
- `backend/services/gpu_client.py` — `_do_submit()` raises `RuntimeError` on missing `video_job_id` in response (was silent `None` crash)
- `backend/services/web_search.py` — Tavily exceptions caught, returns `[]` instead of crashing Research agent

### Observability (COMPLETE)
- All pipeline agent `except` blocks now call `logger.exception()` alongside print
- `video_builder.py` — `exc_info=True` replaces manual `traceback.format_exc()`; unused `traceback` import removed

### Code Quality (COMPLETE)
- `backend/services/ppt_builder.py` — `_ppt_monolithic_fallback()` helper extracted (eliminates ~60 lines of duplication)
- `backend/services/ppt_builder.py` — Hardcoded `"75%"` fake statistic replaced with `"Data unavailable"`

### Test Counts (unchanged)
- **853 pytest** + **81 Vitest** + **10 Playwright E2E** — all pass after fixes

---

## v0.5.2 Sprint (2026-03-09 Session)

### Wave 1: React SPA Scaffold
- **React 19 + Vite 7 + Tailwind v4** with glassmorphism design system
- **Pages**: LoginPage, DashboardPage, UploadPage, ProgressPage, ResultsPage
- **Auth**: JWT-aware fetch client, AuthContext with memory-only tokens, silent refresh
- **Routing**: React Router v7, ProtectedRoute guard, SPA catch-all in FastAPI

### Wave 2: Job API + Data Wiring
- **`api/jobs.ts`** — centralized types and API functions (DRY extraction from pages)
- **ResultsPage** rebuilt — download buttons, status icons, same-origin cookie auth
- **All pages** wired to real API via Tanstack Query

### Wave 3: Test Infrastructure + Review Fixes
- **Vitest 4** — 42 component tests across 5 pages (2.8s)
- **Playwright E2E** — 5 auth flow tests against localhost:8080 (14s)
- **Test utils** — factory-pattern mock auth, QueryClient wrapper, BrowserRouter
- **Auth middleware fix** — `/assets/` added to public paths (SPA JS/CSS was blocked)
- **Stale Jinja2 tests** replaced with SPA-aware assertion (802 → 795 backend tests)
- **Code review fixes**: data-testid on error divs, drag-drop test, cancel failure test, cancelled badge test, login navigation test

### Test Counts
- **42 Vitest** component tests (React)
- **5 Playwright** E2E tests
- **795 pytest** backend tests (7 stale Jinja2 template tests replaced with 1 flexible test)

---

## v0.5.1 Sprint (2026-03-06 Session)

### New Capabilities
- **uv package manager** — migrated from pip/venv to uv (Astral). `uv.lock` committed
- **Database layer** — asyncpg + Neon PostgreSQL, 8 tables (users, jobs, quizzes, quiz_attempts, quiz_answers, chat_sessions, chat_messages + triggers), 12 CRUD functions
- **JWT auth service** — PyJWT + bcrypt, register/login/refresh/me/logout, type enforcement on token claims
- **Frontend route restructure** — app.py split from 693→320 lines into middleware.py, auth_routes.py, job_routes.py, quiz_routes.py
- **SPA catch-all** — detects `frontend/static/index.html` at import; serves React SPA or falls back to Jinja2
- **Configurable upload** — `MAX_UPLOAD_SIZE_MB=50` (was hardcoded 20MB)
- **Test speed** — 171s → 41.55s (4.1x) via pytest-xdist + autouse fixtures; gpu_client 150s → 0.27s (555x)
- **New Makefile targets** — test-fast, test-parallel, build-frontend, e2e

### New Files
- `backend/db/` — __init__.py, schema.sql, connection.py
- `backend/services/db_client.py` — async CRUD (user, job, quiz)
- `backend/services/auth_service.py` — JWT tokens + bcrypt passwords
- `frontend/middleware.py`, `frontend/auth_routes.py`, `frontend/job_routes.py`, `frontend/quiz_routes.py`
- `frontend/tests/test_middleware.py`, `test_auth_routes.py`, `test_job_helpers.py`, `test_quiz_routes.py`
- `backend/tests/test_db_client.py`, `test_auth_service.py`
- `docs/research/agent-lightning.md`, `code-intelligence-tools.md`, `pytest-tdd-optimization.md`, `gitlab-knowledge-graph.md`
- `.claude/mcp.json` — Neon MCP config

### Test Count
- 802 tests (was 626) — new tests for DB client, auth service, middleware, auth routes, quiz routes, job helpers

---

## v0.4.2 Sprint (2026-03-06 Session)

### New Files
- `cpu_video_service/__init__.py`, `app.py`, `worker.py`, `gcs_client.py`, `config.py`
- `cpu_video_service/tests/test_app.py` (19 tests), `test_worker.py` (37 tests), `test_gcs_client.py` (22 tests)
- `Dockerfile.cpu-video` — 2-stage CPU build
- `docs/adr/ADR-001-three-tier-video-fallback.md`

### Modified Files
- `backend/services/gpu_client.py` — `GPUVideoClient` → `VideoServiceClient` (alias kept); `_build_tier_list()` adds CPU tier; updated timeouts (health: 10s, submit: 60s); `_try_next_tier()` for infrastructure-failure fallback
- `backend/config.py` — `cpu_video_service_url` setting; `should_use_video_service` property
- `backend/pipeline/agent_generate.py` — uses `should_use_video_service` instead of `should_use_gpu_service`
- `Dockerfile` — stripped `ffmpeg`, `espeak-ng`, `libreoffice-impress` (video deps)

### Architecture
```
CPU service (europe-west2, 2 vCPU, 4 GiB)
  Pipeline: Ingest → Research → Generate
  Slide export → GCS upload
    ↓ (tier 1)
  GPU Primary (europe-west4, 4 vCPU, 16 GiB, L4)
    or ↓ (tier 2, if tier 1 unreachable)
  GPU Fallback (europe-west1, 4 vCPU, 16 GiB, L4)
    or ↓ (tier 3, if both GPU tiers unreachable)
  CPU Video (europe-west2, 8 vCPU, 32 GiB)
  All: Kokoro TTS + ffmpeg → upload MP4s → CPU service downloads
```

### Test Count
- 626 tests (was 507) — new tests for `cpu_video_service` app/worker/GCS client (78), and expanded `test_gpu_client.py` (37, was 12)

---

## GPU Service Sprint (2026-03-04 Session)

### New Files
- `backend/services/gcs_client.py` — `GCSVideoClient`: `upload_job_inputs()`, `download_videos()`, `cleanup_job()`
- `backend/services/gpu_client.py` — `GPUVideoClient`: `submit_job()`, `poll_until_complete()`, `is_available()`, identity token auth
- `gpu_service/` — FastAPI GPU microservice (`app.py`, `worker.py`, `config.py`, `gcs_client.py`)
- `Dockerfile.gpu` — CUDA-based container for GPU service
- `docs/research/deployment-strategies.md` — CPU vs GPU cost analysis, cold-start, multi-service auth

### Modified Files
- `backend/pipeline/agent_generate.py` — `_build_videos_dispatch()`: GPU path (GCS upload → submit → poll → download) or local `build_videos()` fallback
- `backend/config.py` — `gpu_service_url`, `gcs_bucket` settings; `should_use_gpu_service` computed property
- `pyproject.toml` — `google-cloud-storage>=2.0` dependency; `gpu_service` in testpaths
- `deploy.sh` — dual-service deployment
- `.env.example` — `GPU_SERVICE_URL=` and `GCS_BUCKET=cr8-jobs`

### Test Count
- 507 tests (was 427) — new tests for `GCSVideoClient`, `GPUVideoClient`, `_build_videos_dispatch`, `gpu_service` worker/endpoints, `gpu_utils`, and additional coverage

---

## GPU Acceleration Sprint (2026-03-04 Session)

### New Files
- `backend/services/gpu_utils.py` — central GPU/hardware detection: `get_torch_device()` (CUDA > MPS > CPU), `get_ffmpeg_encoder()` (VideoToolbox > NVENC > QSV > AMF > libx264)

### Measured E2E Benchmark (2026-03-04, M&A PDF, 33 slides, 5 topics, MPS GPU)
| Stage | Duration |
|-------|----------|
| Ingest (PDF parse + ChromaDB) | 51s |
| Research (Tavily + OpenAI) | 2m 29s |
| Generate (PDF + PPT + Scripts) | 2m 19s |
| Slide Export (PPTX → 33 PNGs) | 14s |
| TTS Synthesis (Kokoro 82M on MPS) | 7m 7s |
| ffmpeg Composition (5 parallel, h264_videotoolbox) | ~21m |
| **Total** | **~34 min** |
| Output | 5 videos, 423MB total, 21.9 min total duration, 2000x1125 @ 24fps |

---

## Known Broken / Blocked
- HeyGen/Synthesia providers raise NotImplementedError (by design until implemented)
- Main Dockerfile no longer includes video deps — video must route to a remote service; local video requires a different Dockerfile configuration

## Next Steps (Prioritised)
1. **v0.5.4** — Quiz Agent + Quiz UI (edX-style, one-attempt, red/green feedback) ← **NEXT**
2. **v0.6** — Admin dashboard + feedback loop + structured logging + RBAC + audit logging

## Recent Decisions
| Date | Decision | Rationale | ADR |
|------|----------|-----------|-----|
| 2026-03-09 | Content viewers use native browser capabilities | No external PDF.js or video player library — iframe for PDF, `<img>` carousel for PPT, HTML5 `<video>` for MP4. Zero new npm dependencies. | — |
| 2026-03-09 | Separate view_routes.py module | Content serving is distinct from job CRUD — separate module keeps job_routes.py focused | — |
| 2026-03-06 | CPU video service as Tier 3 fallback | Infrastructure failures on GPU (cold-start, region outage) should not fail video jobs; a CPU fallback with 8 vCPU / 32 GiB provides adequate throughput at ~20-30 min/job | ADR-001 |
| 2026-03-06 | Fallback on infrastructure errors only | Job-level errors (bad input, Kokoro failure) should not silently retry on a different tier — the error would recur and waste compute | ADR-001 |
| 2026-03-06 | VideoServiceClient replaces GPUVideoClient | The client now routes to GPU or CPU tiers; keeping the GPU-specific name was misleading | — |
| 2026-03-06 | Strip video deps from main Dockerfile | With dedicated video service containers, the main CPU container no longer needs 3+ GB of video tooling; reduces image size and attack surface | — |
| 2026-03-04 | GPU service for video (europe-west4, NVIDIA L4) | TTS + ffmpeg are GPU-bound; offloading removes RAM pressure from CPU container | — |
| 2026-03-04 | GCS for CPU↔service data transfer | Cloud Run services don't share a filesystem; GCS is the natural shared store | — |
| 2026-03-04 | Identity token auth for GPU service | Cloud Run service-to-service auth via OIDC identity tokens is the standard GCP pattern | — |
| 2026-03-04 | `should_use_gpu_service` computed property | Keep dispatch logic out of `agent_generate.py` | — |
| 2026-03-04 | AUTH_PASSWORD env var (default: CR8-AI) | Hardcoded passwords are a security risk | — |
| 2026-03-04 | Unified _validate_video_provider() | CLI and web paths had diverged; shared function ensures identical validation | — |
| 2026-03-04 | slide_images as NotRequired | Field only populated for Kokoro jobs; NotRequired is semantically correct | — |
| 2026-03-04 | Guard logging.basicConfig() | Prevents duplicate log entries on reload | — |

## Environment Notes
- Dev server: `make dev` → http://localhost:8080
- Docs preview: `make docs-serve` → http://localhost:8000
- Tests: `make test` → 853 pytest + 81 Vitest + 10 Playwright E2E
- Requires: `.env` file with OPENAI_API_KEY, TAVILY_API_KEY (copy from `.env.example`)
