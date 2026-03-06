# CR8 v0.4 → v1.0 — Roadmap & Detailed Plan

## Context
CR8 is at v0.3.0 — clean baseline, 362 tests, ruff clean, no active work. The roadmap (Loop_Intelligence.md) defines three v0.3 features, but the user wants a revised execution plan with higher ambition on frontend polish, security hardening at every step, and commitizen semver (0.4, 0.5, 0.6).

**Key decisions (confirmed):**
- **Backend**: Python/FastAPI stays. No Node.js runtime. Node.js only at build time (Vite → static assets served by FastAPI).
- **Quiz Agent**: Separate LangGraph workflow (on-demand, reads completed pipeline state including `gap_summary`). Not a 4th node in the main pipeline.
- **Database**: Neon free tier (serverless PostgreSQL, 512 MB free forever). Migrate to Cloud SQL later if needed.
- **Versioning**: commitizen semver — 0.4, 0.5, 0.6 for majors; 0.4.1, 0.4.2 for patches.

**Current security gaps to fix along the way**:
- CORS wide open (`allow_origins=["*"]`) — must lock down
- No security headers (CSP, X-Frame-Options, X-Content-Type-Options)
- No SECURITY.md or vulnerability disclosure process
- Password hardcoded as `CR8-AI` in source — needs env-configurable auth
- LangSmith tracing on by default (data sent externally without opt-in)
- No Dependabot or automated dep scanning

---

## v0.4 — Kokoro TTS Local Video Pipeline ✅ COMPLETE (2026-03-04)
> Add Kokoro TTS as a parallel video provider alongside HeyGen (HeyGen untouched)

### Foundation work
- Research notes: `docs/research/kokoro-tts.md`, `moviepy-v2.md`, `pymupdf-slide-export.md`
- Fix stale `feature_list.json` (`agent_readiness_setup` → `"complete"`)
- Create `SECURITY.md` with vulnerability disclosure process

### Architecture
HeyGen stays exactly as-is. Kokoro is a new `provider="kokoro"` branch:
```
VIDEO_PROVIDER=kokoro  →  script_parser → tts_engine (Kokoro) → slide export → MoviePy compose → MP4
VIDEO_PROVIDER=heygen  →  existing HeyGen API path (unchanged, still behind NotImplementedError for now)
```
The `NotImplementedError` in `build_videos()` becomes **provider-conditional** — blocks HeyGen/Synthesia, allows Kokoro through.

### New files
| File | Purpose |
|------|---------|
| [backend/services/tts_engine.py](backend/services/tts_engine.py) | Kokoro TTS wrapper — `TTSEngine.synthesize(text, output_path)` and `synthesize_segments(segments, output_dir)`. Lives in `services/` per AGENTS.md. |
| [backend/services/script_parser.py](backend/services/script_parser.py) | Parse `[SLIDE N]` markers → `list[dict]` with `slide_num` and `text` |
| [backend/tests/test_tts_engine.py](backend/tests/test_tts_engine.py) | Mocked Kokoro tests (no real TTS in CI) |
| [backend/tests/test_script_parser.py](backend/tests/test_script_parser.py) | Pure logic tests — no mocks needed |
| [backend/tests/test_ppt_builder.py](backend/tests/test_ppt_builder.py) | **Debt repayment** — PPT builder is 1295 lines with zero tests |
| [SECURITY.md](SECURITY.md) | Vulnerability disclosure policy |

### Modified files
| File | Change |
|------|--------|
| [video_builder.py](backend/services/video_builder.py) | Add `_build_kokoro_video()` function. Add `"kokoro"` branch in `_process_single_video()`. Make `NotImplementedError` conditional: `if provider not in ("kokoro",): raise`. Keep all HeyGen code untouched. |
| [file_parser.py](backend/services/file_parser.py) | Add `export_slides_as_images(file_path, output_dir) -> list[str]` — PyMuPDF `get_pixmap(dpi=150)` for PDF, LibreOffice headless for PPTX→PDF first |
| [agent_generate.py](backend/pipeline/agent_generate.py) | Both `build_videos()` call sites (~lines 728, 750): pass new Kokoro kwargs. Call `export_slides_as_images()` before video gen when provider is kokoro. |
| [state.py](backend/pipeline/state.py) | Add optional field `slide_images: list[str]` |
| [run_pipeline.py](backend/run_pipeline.py) | `run_job()`: allow video when `provider == "kokoro"`. `main()`: add kokoro branch (no API key check needed). |
| [config.py](backend/config.py) | Add: `kokoro_voice: str = "af_heart"`, `kokoro_lang: str = "a"`, `video_fps: int = 24`. Change `langchain_tracing_v2` default to `False` (opt-in, not opt-out). |
| [.env.example](.env.example) | Add Kokoro vars. Set `LANGCHAIN_TRACING_V2=false`. |
| [pyproject.toml](pyproject.toml) | Add `kokoro>=0.9`, `moviepy>=2.0`, `soundfile>=0.12`. Bump version to `0.4.0`. |
| [Dockerfile](Dockerfile) | Install `ffmpeg`, `espeak-ng`, `poppler-utils` in runtime stage |
| [test_video_builder.py](backend/tests/test_video_builder.py) | Add Kokoro-path tests (mocked TTS + MoviePy). Keep existing HeyGen tests as-is. |
| [test_file_parser.py](backend/tests/test_file_parser.py) | Add `export_slides_as_images` tests |
| [frontend/app.py](frontend/app.py) | Update `ProgressCapture.STAGE_WEIGHTS` for local video timing |

### Security hardening (v0.4)
- **Temp file cleanup**: `tts_engine.py` and video composition must use `tempfile.TemporaryDirectory()` with guaranteed cleanup (context manager), not manual `os.remove()`
- **Path traversal prevention**: `export_slides_as_images()` must validate output_dir is within the expected outputs directory
- **Subprocess safety**: LibreOffice headless call must use `subprocess.run()` with explicit arg list (no shell=True), timeout parameter
- **LangSmith opt-in**: Change `langchain_tracing_v2` default to `False` — no silent data exfiltration
- Create `SECURITY.md`

### Done when
- [x] `VIDEO_PROVIDER=kokoro python -m backend.run_pipeline --format pdf,ppt,script,video test.pdf` produces an MP4
- [x] HeyGen path is completely untouched (existing tests still pass)
- [x] 4 research notes written and indexed (kokoro-tts, moviepy-v2, pymupdf-slide-export, deployment-strategies)
- [x] `make test` passes — **507 tests** (was target ~411), `make lint` clean
- [x] `cz bump --increment MINOR` → v0.4.0

### Actuals (delivered beyond plan)
- **GPU service**: Dual-service Cloud Run deployment (CPU europe-west2 + GPU europe-west1/europe-west4 NVIDIA L4)
- **GCS data transfer**: `GCSVideoClient` for CPU↔GPU slide/video exchange
- **GPU client**: `GPUVideoClient` with identity token auth, progress polling, region fallback
- **Hardware acceleration**: MPS/CUDA for TTS, hardware H.264 encoding (VideoToolbox/NVENC/QSV/AMF)
- **Two-phase pipeline**: Sequential TTS (shared engine, ~3.4 GB peak) → parallel ffmpeg composition
- **PPTX upload**: Drag-drop accepts both PDF and PPTX with magic byte validation
- **Stage-aware ETA**: Per-stage time budgets calibrated from measured benchmark
- **Configurable auth**: `AUTH_PASSWORD` env var replaces hardcoded password
- **Dockerfile.gpu**: 3-stage CUDA build with pre-cached Kokoro model

### Blocker (resolved)
- ~~Cloud Run memory must increase to 4 GiB~~ — Resolved by GPU service architecture: TTS + ffmpeg offloaded to NVIDIA L4, CPU service stays at 4 GiB.

---

## v0.4.2 — CPU Video Service + 3-Tier Fallback (2026-03-06)
> Strip video processing from main instance; add dedicated CPU-video Cloud Run service as Tier 3 fallback.

**ADR:** [ADR-001: Three-Tier Video Fallback Architecture](../docs/adr/ADR-001-three-tier-video-fallback.md)

### Architecture
Video processing is completely removed from the main pipeline instance. All video work goes through a 3-tier fallback chain:
```
Tier 1: GPU Primary   — europe-west4 (NVIDIA L4, ~3 min)
Tier 2: GPU Fallback  — europe-west1 (NVIDIA L4, ~3 min)
Tier 3: CPU Video     — europe-west2 (8 vCPU / 32 GiB, ~25 min)
```
Fallback triggers on infrastructure failures only (ConnectionError, Timeout, 5xx). Job-level errors do NOT trigger fallback.

### Instance Configuration

| Instance | CPU | Memory | GPU | Region | Min/Max |
|----------|-----|--------|-----|--------|---------|
| Main pipeline | 1 vCPU | 2 GiB | — | europe-west2 | 0/1 |
| GPU primary | 4 vCPU | 16 GiB | NVIDIA L4 | europe-west4 | 0/1 |
| GPU fallback | 4 vCPU | 16 GiB | NVIDIA L4 | europe-west1 | 0/1 |
| CPU video | 8 vCPU | 32 GiB | — | europe-west2 | 0/2 |

All instances scale to zero ($0 when idle).

### New files
| File | Purpose |
|------|---------|
| `cpu_video_service/__init__.py` | Package init |
| `cpu_video_service/config.py` | Pydantic settings (device=cpu, max_workers=6) |
| `cpu_video_service/app.py` | FastAPI — same API contract as gpu_service |
| `cpu_video_service/worker.py` | 4-phase job runner (download → TTS → compose → upload) |
| `cpu_video_service/gcs_client.py` | GCS download/upload helpers |
| `cpu_video_service/tests/` | 48 tests (app, worker, gcs_client) |
| `Dockerfile.cpu-video` | 2-stage build (no CUDA), stock ffmpeg |
| `docs/adr/ADR-001-three-tier-video-fallback.md` | Architecture decision record |

### Modified files
| File | Change |
|------|--------|
| `backend/services/gpu_client.py` | Renamed to `VideoServiceClient`, 3-tier fallback, updated timeouts |
| `backend/config.py` | Added `cpu_video_service_url`, `should_use_video_service` property |
| `backend/pipeline/agent_generate.py` | Switched to `should_use_video_service` |
| `Dockerfile` | Stripped ffmpeg, espeak-ng, libreoffice-impress |
| `backend/tests/test_gpu_client.py` | 40 tests covering 3-tier fallback, headers, tier list |
| `.env.example` | Added `CPU_VIDEO_SERVICE_URL` |
| `pyproject.toml` | Added cpu_video_service package |

### Done when
- [x] `ruff check` passes on all new/modified files
- [x] 107 tests pass (48 cpu_video_service + 40 gpu_client + 19 app)
- [x] Code review: 3 blocking issues found and resolved
- [x] ADR-001 written
- [ ] `docker build -f Dockerfile.cpu-video -t cr8-cpu-video .` builds
- [ ] `docker build -f Dockerfile -t cr8-pipeline .` builds without video deps
- [ ] Deploy to Cloud Run and verify fallback chain
- [ ] `cz bump --increment PATCH` → v0.4.2

---

## v0.5 — Polished React Frontend + Quiz + Content Viewers
> Glassmorphism UI, dark mode, inline content viewers, edX-quality quiz, persistent job history, JWT auth with open registration. RAG chatbot deferred to v0.5.1.

### Key Decisions (confirmed 2026-03-05)

| Decision | Rationale |
|----------|-----------|
| **Open registration** (email + password, no invite) | Stakeholders need to self-serve during demos without asking us to create accounts. Removes friction from first impression. Invite-only adds a gate that slows evaluation. |
| **Downloads: PDF, PPT, Video only** (no scripts) | Video scripts are an intermediate pipeline artifact needed for TTS — students don't consume them. Showing scripts clutters the UI and confuses non-technical stakeholders about what the product outputs are. |
| **RAG chatbot deferred to v0.5.1** | Chatbot adds ~2-3 sessions of work and significant backend complexity (ChromaDB RAG, streaming SSE, citation extraction). Shipping React + Quiz first gets the core product in front of stakeholders faster. Chat is a fast follow-up since DB schema is pre-included. |
| **PPT viewer: server-side image carousel** | PPTX can't render natively in browsers. Google Docs Viewer requires public file access (privacy concern for university curriculum). Server-side LibreOffice conversion is reliable, already installed in Dockerfile, and works offline. |
| **TDD approach** (Red → Green → Refactor) | Large refactor (Jinja2 → React, in-memory → PostgreSQL, session → JWT) needs a safety net. Writing tests first catches regressions early, especially when extracting routes from the monolithic app.py. |
| **Job persistence to PostgreSQL** (every ~5s) | Users will close browser tabs, switch devices, or check back hours later. In-memory state is lost on page close. Writing progress to DB means the Dashboard always reflects reality. Acceptable tradeoff: server restart loses running jobs (true durability needs Cloud Tasks, deferred to v0.6+). |
| **JWT over session cookies** | Per-user auth enables job history isolation, quiz attempts per student, and future RBAC (admin vs student). Session cookies can't carry user identity across devices. JWT access + refresh token pattern is industry standard for SPAs. |
| **Neon PostgreSQL free tier** | 512 MB free forever, serverless (scales to zero), connection pooling built-in. No ops burden vs. self-hosted Postgres. Migration path to Cloud SQL when needed. SQLite can't handle concurrent writes from pipeline + API. |
| **React + Vite + Tailwind (TypeScript)** | React is the most common SPA framework — largest hiring pool, most component libraries. Vite is the fastest bundler. Tailwind utility classes + glassmorphism custom utilities = rapid UI iteration. TypeScript catches bugs at build time in a growing frontend. |
| **Glassmorphism design** | Modern 2026 aesthetic that signals product maturity. The frosted glass effect (backdrop-filter + blur) creates visual depth without complexity. Dark mode is expected by students. |

### Phase Breakdown (each phase = patch release)

**v0.5.1: Foundation** — DB + JWT + API restructure + test optimization (Jinja2 still works) **[COMPLETE]**
**v0.5.2: React SPA Shell** — Login + Dashboard + Upload + Progress (replaces Jinja2)
**v0.5.3: Results + Content Viewers** — PDF viewer, PPT carousel, video player
**v0.5.4: Quiz Agent + Quiz UI** — edX-style quiz, red/green results

### Agent & MCP Checkpoints Per Phase

Each phase follows the Wave Protocol from AGENTS.md. Agents run in strict order after each wave of work within a phase. MCP tools are used at specific points.

#### v0.5.1: Foundation [COMPLETE]
**Pre-implementation:**
- `research-assistant` → asyncpg, PyJWT, bcrypt (Context7 for API patterns, Snyk for package health)
**Per-wave (DB layer, auth layer, route restructure, E2E tests):**
1. `test-writer` — write tests for new code (Context7 to verify mock patterns for asyncpg/FastAPI)
2. `code-reviewer` — quality + lint + architecture (skip Snyk per-wave)
3. Fix blocking issues
**Pre-commit:**
4. `docs-writer` — update mk-docs, CHANGELOG, PROGRESS, Loop Intelligence, llms.txt
5. `code-reviewer` with Snyk — `snyk_code_scan` on all new files + `snyk_sca_scan` (new deps added)

**MCP usage:**
- **Context7**: asyncpg connection pool patterns, FastAPI middleware patterns, PyJWT token creation/verification
- **Playwright**: E2E tests against localhost:8080 (login flow, upload, progress)
- **Sequential Thinking**: not needed (no architectural trade-offs beyond existing ADRs)

#### v0.5.2: React SPA Shell
**Pre-implementation:**
- `research-assistant` → React 19, Vite 6, Tailwind v4, React Router v7 (Context7 for all; Snyk package health for each new npm dep)
- `research-assistant` → tailwindcss-glassmorphism patterns, shadcn/ui + Radix primitives, Tanstack Query

**Wave 1: Vite + React scaffold + Tailwind + auth context + test tooling + dev intelligence**
1. Add `pytest-randomly>=0.15` and `pytest-timeout>=2.2` to `pyproject.toml` dev deps; configure `timeout = 30` in `[tool.pytest.ini_options]`
2. **Add CodeGrok MCP** to `.claude/mcp.json` — run initial index on `backend/` + `frontend/` (~2-5 min one-time). See `docs/research/code-intelligence-tools.md`.
3. **Add GitHub Projects V2 MCP** — create "v0.5.2" board, link existing issues. Configure with GitHub PAT in `.claude/mcp.json`.
4. Document new MCPs in `CLAUDE.md` MCP Servers section
5. `test-writer` — Vitest component tests for LoginPage, AuthContext
6. `code-reviewer` — review React patterns, Tailwind config, build integration, pytest config
7. Fix blocking issues

**Wave 2: DashboardPage + UploadPage + job API hooks**
1. `test-writer` — tests for DashboardPage, UploadPage, useJobs hook
2. `code-reviewer` — review API client, file upload handling, drag-drop
3. Fix blocking issues

**Wave 3: ProgressPage + SSE/polling + SPA catch-all in FastAPI**
1. `test-writer` — tests for ProgressPage, useProgress hook, FastAPI SPA mount
2. `code-reviewer` — review SSE/polling, FastAPI static serving, CORS config
3. Fix blocking issues

**Pre-commit:**
4. `docs-writer` — new mk-docs pages for React frontend, update configuration.md, update llms.txt
5. `code-reviewer` with Snyk — `snyk_code_scan` (React + FastAPI changes) + `snyk_sca_scan` (npm + Python deps)

**MCP usage:**
- **Context7**: React 19 hooks/context patterns, Vite config for FastAPI proxy, Tailwind v4 utility classes, React Router v7 createBrowserRouter
- **CodeGrok**: semantic code search for "find all video-related code", "how does auth work" — replaces manual Grep + Read chains, 10x token savings
- **GitHub Projects V2**: query active sprint issues, link PRs to board, filter by phase/status
- **Playwright**: verify each page renders at localhost:8080 after SPA integration — LoginPage, DashboardPage, UploadPage, ProgressPage; test dark mode toggle; test responsive layout
- **Sequential Thinking**: reason through SPA routing strategy (hash vs browser router, FastAPI catch-all)

#### v0.5.3: Results + Content Viewers
**Pre-implementation:**
- `research-assistant` → react-pdf or PDF.js for inline viewing (Context7 + Snyk health check)
- `research-assistant` → HTML5 video player patterns, LibreOffice PPTX→PNG server-side conversion

**Wave 1: ResultsPage shell + tab navigation + download buttons**
1. `test-writer` — tests for ResultsPage, TabNav, DownloadBar
2. `code-reviewer` — review tab routing, download endpoint integration
3. Fix blocking issues

**Wave 2: PDF viewer (iframe) + PPT carousel (server-side PNG) + video player**
1. `test-writer` — tests for PdfViewer, PptViewer, VideoPlayer components + backend `/ppt-images` endpoint
2. `code-reviewer` — review content serving security (path traversal, MIME types), video streaming
3. Fix blocking issues

**Pre-commit:**
4. `docs-writer` — update mk-docs with viewer architecture, new API routes, update llms.txt
5. `code-reviewer` with Snyk — `snyk_code_scan` on content serving endpoints

**MCP usage:**
- **Context7**: FastAPI FileResponse/StreamingResponse for video, react-pdf component API
- **Playwright**: verify PDF renders in iframe, PPT carousel navigates slides, video plays with topic selector, download buttons trigger file downloads — all at localhost:8080
- **Sequential Thinking**: not needed (viewer approach already decided — server-side PNG carousel)

#### v0.5.4: Quiz Agent + Quiz UI
**Pre-implementation:**
- `research-assistant` → LangGraph separate workflow patterns (Context7 for graph compilation, conditional edges)
- `research-assistant` → edX quiz UI patterns (web search — no library, custom implementation)

**Wave 1: Quiz Agent backend — agent_quiz.py + quiz_graph.py + quiz prompt**
1. `test-writer` — tests for quiz agent (mocked LLM), quiz graph execution, prompt output validation
2. `code-reviewer` — review LangGraph workflow, prompt injection safety, structured output parsing
3. Fix blocking issues

**Wave 2: Quiz API routes — generate, fetch, submit, results**
1. `test-writer` — tests for all quiz endpoints (auth, validation, duplicate submission 409)
2. `code-reviewer` — review auth on routes, Pydantic models, DB queries
3. Fix blocking issues

**Wave 3: QuizPage + QuizResultsPage UI**
1. `test-writer` — Vitest tests for QuestionCard, QuizProgressBar, ScoreSummary, per-question feedback
2. `code-reviewer` — review XSS prevention in quiz rendering, accessibility (keyboard navigation)
3. Fix blocking issues

**Pre-commit (final for v0.5.4):**
4. `docs-writer` — full docs pass: mk-docs quiz pages, CHANGELOG, Loop Intelligence, PROGRESS, todo.md, llms.txt
5. `code-reviewer` with Snyk — full `snyk_code_scan` + `snyk_sca_scan` on entire codebase
6. `research-assistant` — final dependency audit (all new deps added across v0.5.2-v0.5.4)

### Foundation work
- **MCP Phase 1+2 (config-only): COMPLETE** (2026-03-04, updated 2026-03-05) — Context7, Playwright, Sequential Thinking installed and wired into agents. GitHub MCP removed (unreliable). See `docs/research/mcp-dev-tools.md` and `PM-Docs/MCP_Integration_Plan.md`.
- **Code Intelligence MCP (v0.5.2):** CodeGrok for semantic code search (10x token savings). Setup: `.claude/mcp.json` + one-time index. See `docs/research/code-intelligence-tools.md`.
- **GitHub Projects V2 MCP (v0.5.2):** Sprint board for active phases, linked to repo issues. See `docs/research/code-intelligence-tools.md`.
- **MCP Phase 2 (code change): deferred here** — FastAPI-MCP mount in `frontend/app.py`. Use `fastmcp>=3.1` instead of `fastapi-mcp>=0.1` (see `PM-Docs/MCP_Integration_Plan.md` Research Findings).
- ~~ADR-001: LangGraph pipeline architecture~~ → Repurposed as [ADR-001: Three-Tier Video Fallback](../docs/adr/ADR-001-three-tier-video-fallback.md) (completed v0.4.2)
- ADR-002: PostgreSQL for quiz storage (why Neon free tier, schema design, migration path)
- ADR-003: React frontend (why React + Vite + Tailwind, FastAPI integration)
- ADR-004: JWT auth (why JWT over session cookies, token strategy)
- Research notes: `asyncpg-neon-postgres.md`, `python-jose-jwt.md`, `react-vite-fastapi.md`, `tailwindcss-glassmorphism.md`, `edx-quiz-patterns.md`

### Frontend Design System
**Glassmorphism / Frosted Glass theme:**
- `backdrop-filter: blur(16px)` + `background: rgba(255, 255, 255, 0.1)` on card surfaces
- Subtle border: `border: 1px solid rgba(255, 255, 255, 0.18)`
- Layered depth with soft box shadows
- **Dark mode**: DEFERRED to v0.5.1 — light mode only for POC demo (halves CSS + testing work)
- Color palette: deep navy/charcoal backgrounds, soft blue/purple accent gradients, high-contrast text
- Responsive: mobile-first, works on tablet + desktop
- **Tailwind CSS v4** with custom glassmorphism utility classes
- **Component library**: Use shadcn/ui or Radix primitives for headless components (buttons, dialogs, tabs, cards) + Tailwind glassmorphism styling. Do NOT build every component from scratch.
- **Data fetching**: Use Tanstack Query (React Query) for API calls — built-in caching, refetching, loading states. Eliminates hand-written useJobs/useProgress hooks.
- Accessible: WCAG 2.1 AA contrast ratios

### Test Optimization (v0.5.1 includes this — between Foundation and React SPA)
> Quick wins applied immediately; deeper tooling research informs v0.5.2+ testing strategy.

**Already applied:**
- `pytest-xdist` added for parallel execution (`make test-parallel` runs `-n auto`)
- `make test-fast` added for TDD loop (`-x -q --tb=short`)
- gpu_client test suite optimized: 150s -> 0.27s (mocked time.sleep + _get_identity_token)
- `make build-frontend` and `make e2e` targets added to Makefile

**Add in v0.5.2, Wave 1 (alongside Vite scaffold):**
- `pytest-randomly>=0.15` — randomize test order to catch implicit dependencies between tests
- `pytest-timeout>=2.2` — automatic per-test timeouts (default 30s, `timeout_method = "thread"` in pyproject.toml); mark slow tests with `@pytest.mark.timeout(120)`
- Add to `pyproject.toml` dev deps and `[tool.pytest.ini_options]`: `timeout = 30`, `timeout_method = "thread"`
- Research note: `docs/research/pytest-tdd-optimization.md`

**Add in v0.5.2, Wave 3 (after components stabilize):**
- Vitest for React component tests (LoginPage, DashboardPage, UploadPage)
- Playwright E2E regression suite (`make e2e`) as pre-commit gate

**Add in v0.6 (with GitHub Actions CI):**
- `pytest-cov --cov-fail-under=80` as CI gate — coverage must not drop below 80%
- `pytest --randomly-seed=last -p no:sugar` for CI (reproducible random order, no fancy output)

**Skipped (not aligned with CR8's mocked test pattern):**
- `pytest-benchmark` — benchmarks measure mock overhead, not real performance; revisit in v0.5.3+ with E2E perf tests
- `mutmut` (mutation testing) — mocks short-circuit mutations; CR8's eval harness (L1 structural + L2 LLM judges) provides better quality assurance

### Pages
| Page | Purpose |
|------|---------|
| `LoginPage.tsx` | Frosted glass card, email+password, "How it works" (3 steps with icons: Upload → Generate → Learn). Toggle between Sign In / Create Account. |
| `DashboardPage.tsx` | Job history list (past creations), "+ New Generation" CTA, status badges (Complete/Running/Error/Cancelled), empty state. |
| `UploadPage.tsx` | Drag-drop PDF/PPTX, format checkboxes: PDF (always on), PPT, Video (auto-selects PPT). No Script checkbox — scripts are internal. |
| `ProgressPage.tsx` | Stage cards (Ingest/Research/Generate/Video) as horizontal pipeline visualization, progress bar, ETA, collapsible log viewer, Stop Pipeline button. |
| `ResultsPage.tsx` | 3 tabs: PDF (iframe viewer), Slides (image carousel), Video (HTML5 player + topic selector). Download buttons for PDF/PPT/Videos. "Take Quiz" CTA. Tabs only shown for generated formats. |
| `QuizPage.tsx` | One question at a time (edX style), difficulty badge (green/amber/red), Bloom's level pill, "From: Module N" source reference, prev/next navigation. No timer. Submit on last question. |
| `QuizResultsPage.tsx` | Circular score gauge, difficulty breakdown (Easy/Medium/Hard), per-question green/red cards with feedback text, "Review Content" link. One attempt only — no retake button. |

### Job Persistence — Close Browser / Switch Device
- ProgressCapture writes `{status, stage, percent}` to PostgreSQL every ~5 seconds
- User closes browser → job keeps running → DB has latest progress
- User returns (same or different device) → Dashboard shows "Running 62%" or "Complete"
- **Limitation (POC):** Server restart = background thread lost. On startup, mark "running" jobs as "error". True durability (Cloud Tasks) deferred to v0.6+.

### Quiz Agent (separate LangGraph workflow)
On-demand workflow that reads completed pipeline state (`gap_summary`, `topics`, `modules_md`). NOT a 4th node in the main pipeline — triggered via `POST /api/quiz/generate` after pipeline finishes.
- **Input**: module markdown + `gap_summary` + topics + `curriculum_scope`
- **Output**: structured quiz JSON — question, 4 options, correct answer, difficulty (easy/medium/hard), Bloom's taxonomy level, source section reference, feedback for correct + incorrect
- **Gap-aware**: At least 40% of questions target identified knowledge gaps
- Difficulty distribution: 30% easy, 50% medium, 20% hard
- One-attempt-only quizzes — no retakes, red/green results display
- Can regenerate quizzes independently without re-running the full pipeline
- Model: `openai_model_mini` (moderate reasoning, good for structured generation)

### Database Schema (Neon PostgreSQL)

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(100),
    role VARCHAR(20) DEFAULT 'student' CHECK (role IN ('student', 'admin')),
    created_at TIMESTAMPTZ DEFAULT now(),
    last_login_at TIMESTAMPTZ
);

CREATE TABLE jobs (
    id VARCHAR(12) PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    formats TEXT[] NOT NULL,
    status VARCHAR(20) DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'complete', 'error', 'cancelled')),
    stage VARCHAR(30),
    percent INTEGER DEFAULT 0,
    error_text TEXT,
    result_meta JSONB,
    topics JSONB,
    gap_summary JSONB,
    modules_md JSONB,
    created_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE quizzes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id VARCHAR(12) REFERENCES jobs(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE quiz_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quiz_id UUID REFERENCES quizzes(id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    question_type VARCHAR(20) DEFAULT 'mcq',
    options JSONB NOT NULL,
    correct_index INTEGER NOT NULL,
    difficulty VARCHAR(10) CHECK (difficulty IN ('easy', 'medium', 'hard')),
    blooms_level VARCHAR(20),
    source_section VARCHAR(255),
    feedback_correct TEXT,
    feedback_incorrect TEXT,
    sort_order INTEGER DEFAULT 0
);

CREATE TABLE quiz_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quiz_id UUID REFERENCES quizzes(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    score DECIMAL(5,2),
    total_questions INTEGER,
    started_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ,
    UNIQUE(quiz_id, user_id)
);

CREATE TABLE quiz_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    attempt_id UUID REFERENCES quiz_attempts(id) ON DELETE CASCADE,
    question_id UUID REFERENCES quiz_questions(id) ON DELETE CASCADE,
    selected_index INTEGER NOT NULL,
    is_correct BOOLEAN NOT NULL,
    time_spent_s INTEGER
);

-- v0.5.1 chatbot tables (schema included now, no migration later)
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id VARCHAR(12) REFERENCES jobs(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role VARCHAR(10) NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    citations JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### API Routes

**Auth (open registration):**
| Method | Path | Auth | Request | Response |
|--------|------|------|---------|----------|
| POST | `/api/auth/register` | None | `{email, password, display_name?}` | `{user_id, email}` 201 |
| POST | `/api/auth/login` | None | `{email, password}` | `{access_token, refresh_token, expires_in}` |
| POST | `/api/auth/refresh` | Cookie | — | `{access_token, expires_in}` |
| GET | `/api/auth/me` | Bearer | — | `{id, email, display_name, role}` |
| POST | `/api/auth/logout` | Bearer | — | 204 |

**Jobs (extended):**
| Method | Path | Auth | Request | Response |
|--------|------|------|---------|----------|
| POST | `/api/upload` | Bearer | Multipart file | `{job_id, filename}` |
| POST | `/api/start` | Bearer | `{job_id, formats[]}` | `{status: "running"}` |
| GET | `/api/progress/{id}` | Bearer | — | `{status, stage, percent, ...}` |
| POST | `/api/cancel/{id}` | Bearer | — | `{status: "cancelling"}` |
| GET | `/api/download/{id}/{type}` | Bearer | — | FileResponse (pdf, ppt, videos only — no scripts) |
| GET | `/api/jobs` | Bearer | `?limit=20&offset=0` | `{jobs: [...], total}` |
| GET | `/api/jobs/{id}` | Bearer | — | Full job detail |
| GET | `/api/jobs/{id}/view/pdf` | Bearer | — | Inline PDF |
| GET | `/api/jobs/{id}/view/video/{topic}` | Bearer | — | Stream video |
| GET | `/api/jobs/{id}/ppt-images` | Bearer | — | Slide PNG array |

**Quiz:**
| Method | Path | Auth | Request | Response |
|--------|------|------|---------|----------|
| POST | `/api/quiz/generate` | Bearer | `{job_id}` | `{quiz_id, question_count}` |
| GET | `/api/quiz/{quiz_id}` | Bearer | — | `{quiz_id, title, questions[], existing_attempt?}` |
| POST | `/api/quiz/{quiz_id}/submit` | Bearer | `{responses: [{question_id, selected_index}]}` | `{attempt_id, score, results[]}` |
| GET | `/api/quiz/{quiz_id}/results` | Bearer | — | `{score, total, per_question_results[]}` |
| GET | `/api/quiz/by-job/{job_id}` | Bearer | — | `{quizzes: [...]}` |

### New files
| File | Purpose |
|------|---------|
| `backend/db/__init__.py`, `schema.sql`, `connection.py`, `migrations/001_initial.sql` | PostgreSQL schema + asyncpg pool |
| `backend/services/db_client.py` | Async CRUD (users, jobs, quizzes, attempts, responses) |
| `backend/services/auth_service.py` | JWT create/verify, password hash/verify (python-jose HS256) |
| `frontend/auth_routes.py` | `/api/auth/*` endpoints |
| `frontend/job_routes.py` | Extracted from app.py — upload, start, progress, cancel, download, list, view |
| `frontend/quiz_routes.py` | `/api/quiz/*` endpoints |
| `frontend/middleware.py` | JWT auth dependency, security headers middleware |
| `backend/pipeline/agent_quiz.py` | Quiz Agent: loads job data, calls LLM, validates, stores questions |
| `backend/pipeline/quiz_graph.py` | LangGraph graph: quiz_generate → quiz_validate → END |
| `backend/prompts/quiz.py` | Quiz generation prompt with difficulty/Bloom's/gap constraints |
| `frontend/react-app/` | Vite + React 19 + Tailwind v4 + TypeScript SPA |
| `src/pages/` | LoginPage, DashboardPage, UploadPage, ProgressPage, ResultsPage, QuizPage, QuizResultsPage |
| `src/components/` | GlassCard, Navbar, DarkModeToggle, FileDropzone, ProgressBar, StageCard, JobCard, TabNav, PdfViewer, PptViewer, VideoPlayer, DownloadBar, QuestionCard, QuizProgressBar, ScoreSummary, ProtectedRoute |
| `src/api/` | client.ts (JWT wrapper), auth.ts, jobs.ts, quiz.ts |
| `src/context/` | AuthContext.tsx, ThemeContext.tsx |
| `src/hooks/` | useProgress.ts, useJobs.ts |
| `src/styles/` | globals.css, glass.css |
| Tests | `test_db_client.py` (~15), `test_auth_service.py` (~10), `test_auth_routes.py` (~12), `test_job_routes.py` (~8), `test_quiz_agent.py` (~10), `test_quiz_routes.py` (~12), React component tests (~40 via Vitest) |

### Modified files
| File | Change |
|------|--------|
| [app.py](frontend/app.py) | Major refactor: extract routes into auth_routes, job_routes, quiz_routes. Add security headers middleware. CORS from `ALLOWED_ORIGINS`. asyncpg pool in lifespan. SPA catch-all. ProgressCapture syncs to DB every ~5s. On startup, mark stale "running" jobs as "error". |
| [config.py](backend/config.py) | Add: `database_url`, `jwt_secret`, `jwt_algorithm: str = "HS256"`, `jwt_access_expiry_minutes: int = 480`, `jwt_refresh_expiry_days: int = 7`, `allowed_origins` |
| [state.py](backend/pipeline/state.py) | Add: `modules_md: NotRequired[list[str]]` |
| [agent_generate.py](backend/pipeline/agent_generate.py) | Collect module markdown into `state["modules_md"]` |
| [run_pipeline.py](backend/run_pipeline.py) | Persist topics, gap_summary, modules_md to jobs table after pipeline |
| [pyproject.toml](pyproject.toml) | Add `asyncpg>=0.29`, `python-jose[cryptography]>=3.3`. Bump to `0.5.0`. |
| [Dockerfile](Dockerfile) | Multi-stage: `FROM node:20-slim AS frontend-builder` for React build. Copy `dist/` to FastAPI static dir. |
| [.env.example](.env.example) | Add `DATABASE_URL`, `JWT_SECRET`, `ALLOWED_ORIGINS` |

### Security hardening (v0.5)
- **JWT auth**: Access token (8hr, Bearer header) + refresh token (7d, httpOnly cookie)
- **CORS lockdown**: `ALLOWED_ORIGINS` env var replaces `allow_origins=["*"]`
- **Security headers middleware**: `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Content-Security-Policy`, `Referrer-Policy: strict-origin-when-cross-origin`
- **SQL injection prevention**: asyncpg parameterized queries only — no string interpolation
- **Quiz submission validation**: Pydantic models for all request bodies, UNIQUE constraint + 409 on duplicate
- **Rate limiting**: 5 attempts/15 min on login (kept from v0.4)
- **React XSS prevention**: JSX escaping + CSP headers
- **No scripts exposed**: video scripts are internal artifacts, not downloadable

### Development approach: TDD
Every feature follows Red → Green → Refactor. Tests written before implementation code. `make test` + `make lint` must pass after every file pair.

### Done when
- [ ] React SPA serves from FastAPI with frosted glass design in both light and dark mode
- [ ] Student can: register, log in, upload PDF, watch pipeline progress, view content inline, download PDF/PPT/Video, take quiz, see red/green results
- [ ] Dashboard shows job history — close browser, come back, jobs still visible
- [ ] Quiz Agent generates valid MCQs from any completed pipeline job
- [ ] PostgreSQL stores users, jobs, quizzes persistently
- [ ] CORS locked down, security headers present, JWT auth working
- [ ] `make test` passes (~610 tests), `make lint` clean
- [ ] `cz bump --increment MINOR` → v0.5.0

### POC Recommendations (v0.5)

**Scope reduction for faster stakeholder demo:**
1. **Ship v0.5.2+v0.5.3 before v0.5.4** — A working React UI with content viewers is more impressive in demos than a quiz with no polished frontend. Quiz can follow 1-2 sessions later.
2. **Skip Vitest initially** — React component tests add overhead during rapid UI iteration. Write them in v0.5.4 once components stabilize. Backend pytest remains mandatory.
3. **Use shadcn/ui or Radix primitives** — Don't build GlassCard, TabNav, ProgressBar from scratch. Use headless components + Tailwind for glassmorphism styling. Saves 2-3 sessions of UI work.
4. **Defer dark mode to v0.5.1** — Light mode glassmorphism is sufficient for the POC demo. Dark mode doubles CSS work and testing surface.
5. **Consider Tanstack Query over raw fetch** — Caching, refetching, and loading states are built in. Eliminates hand-written `useJobs`/`useProgress` hooks. Context7 has docs for it.
6. **WebSocket for progress instead of polling** — FastAPI supports WebSocket natively. Eliminates 5-second polling interval, gives real-time feel. Falls back to GET `/api/progress` for simplicity.
7. **Pre-build the DB schema NOW** — Run `schema.sql` against Neon immediately and verify the migration path. Don't discover schema issues during v0.5.4 quiz work.
8. **Add `make build-frontend`** — Makefile target for `cd frontend/react-app && npm run build && cp -r dist/ ../static/`. Makes the build reproducible and CI-ready.
9. **Pin ALL frontend deps in package.json** — Use exact versions (no `^` or `~`). React ecosystem moves fast; `^19.0.0` today might resolve to a breaking `19.1.0` next week.
10. **Playwright E2E suite as regression gate** — After v0.5.2, add a `make e2e` target running 5-10 core Playwright scenarios (login → upload → progress → results → download). Run before every commit.
11. **Token optimization discipline** — Use `/clear` between backend/frontend work sessions. Use Plan mode before any 5+ file change. Keep CLAUDE.md <500 lines (already done). Expected savings: 40-60% token reduction per session. See `docs/research/code-intelligence-tools.md`.
12. **CodeGrok for code search** — Add CodeGrok MCP in Wave 1 alongside Vite scaffold. Semantic code search replaces manual Grep+Read chains. 10x token savings per query, 30-minute setup, MIT licensed, fully local.

**Architecture risks to address early:**
- **SPA + FastAPI static serving** — Test the catch-all route early. React Router's browser history mode requires FastAPI to serve `index.html` for all non-API paths. Get this working in Wave 1 of v0.5.2.
- **JWT token refresh** — The refresh flow (httpOnly cookie → new access token) is tricky to get right with React. Research and implement in v0.5.2 Wave 1, not as an afterthought.
- **File upload size limits** — Current upload has no size limit. Add `MAX_UPLOAD_SIZE_MB=50` to config before React upload page.
- **CORS in development** — Vite dev server runs on port 5173, FastAPI on 8080. Need proxy config in `vite.config.ts` during development, then switch to same-origin serving in production.

### v0.5.1 — RAG Chatbot (fast follow-up)
- Chatbot sidebar on ResultsPage, RAG over ChromaDB + generated modules
- Streaming responses via SSE, citations shown as chips
- Chat history persisted in PostgreSQL (schema already included in v0.5.0)
- New files: `backend/services/chat_service.py`, `backend/prompts/chat.py`, `frontend/chat_routes.py`, `src/pages/ChatbotPage.tsx`, `src/components/ChatMessage.tsx`, `src/components/CitationChip.tsx`

---

## v0.6 — Admin Dashboard + Data Tracking Infrastructure
> Analytics, user management, feedback loop, monitoring

### Foundation work
- ADR-004: Feedback loop architecture (quiz data → content regeneration, thresholds, regression prevention)
- ADR-005: Observability stack (structured logging, metrics, health checks)
- Research notes: `recharts.md`, `structured-logging-python.md`
- Backfill remaining research notes: `fpdf2.md`, `python-pptx.md`, `chromadb.md`
- **Code intelligence upgrade:** Evaluate code-graph-mcp for call graphs + dependency analysis (requires Python 3.12 upgrade decision). Evaluate Axon MCP if codebase exceeds 30K LoC. Review CodeGrok token savings metrics from v0.5 usage.

### Admin Dashboard (React)
| Page | What it shows |
|------|--------------|
| `AdminOverview.jsx` | Total students, quizzes completed, avg scores, active jobs — glassmorphism stat cards |
| `TopicHeatmap.jsx` | Per-topic, per-section performance heatmap (Recharts) — identifies weak content |
| `QuestionAnalytics.jsx` | Per-question success rate, most-chosen wrong answers, difficulty calibration |
| `StudentTrends.jsx` | Score trends over time, cohort comparison |
| `QuizEditor.jsx` | Add/edit/delete questions, set difficulty, customize feedback text |
| `UserManagement.jsx` | View students, assign roles (student/admin), deactivate accounts |
| `SystemHealth.jsx` | Pipeline job history, error rates, API latency, resource usage |

### Feedback Loop (closes the adaptive learning loop)
```
PostgreSQL quiz data → feedback_analyser.py (50+ completions, avg < 60% = weak)
  → agent_generate.py (feedback_context injection)
    → eval framework (L1+L2 regression check)
      → replace content only if no regression
```

### New files
| File | Purpose |
|------|---------|
| `backend/services/feedback_analyser.py` | Query PostgreSQL for per-topic aggregates, flag weak sections |
| `backend/pipeline/regeneration.py` | Orchestrate: analyse → regenerate → eval → conditional replace |
| `backend/prompts/feedback.py` | Feedback injection template for generation prompt |
| `frontend/react-app/src/pages/Admin*.jsx` | Dashboard pages listed above |
| `frontend/react-app/src/components/HeatMap.jsx` | Recharts-based topic heatmap |
| `frontend/react-app/src/components/ScoreChart.jsx` | Bar/line charts for trends |
| `frontend/admin_routes.py` | Admin API: `/api/admin/dashboard`, `/overview`, `/questions/{id}`, `/users`, `/regenerate` |
| `backend/middleware/audit_log.py` | Structured audit logging middleware |
| Tests | `test_feedback_analyser.py`, `test_regeneration.py`, `test_admin_routes.py` |

### Modified files
| File | Change |
|------|--------|
| [agent_generate.py](backend/pipeline/agent_generate.py) | `_generate_module()` accepts optional `feedback_context: dict`, prepends feedback to prompt |
| [postgres_client.py](backend/services/postgres_client.py) | Add analytics queries, admin CRUD, materialized view refresh, audit log writes |
| [app.py](frontend/app.py) | Mount admin_routes, add audit logging middleware, enhanced health check endpoint |
| [config.py](backend/config.py) | Add `feedback_min_completions=50`, `feedback_weakness_threshold=0.60`, `log_level`, `audit_log_enabled` |
| [pyproject.toml](pyproject.toml) | Add `recharts` (frontend), `structlog` (backend). Bump to `0.6.0`. |
| `docker-compose.yml` | Add PostgreSQL service, volume mounts, health checks |

### Security hardening (v0.6)
- **Role-based access control (RBAC)**: Admin endpoints gated by JWT `role: "admin"` claim. Students cannot access admin routes.
- **Audit logging**: All admin actions (question edits, user management, regeneration triggers) logged with timestamp, user_id, action, target — stored in PostgreSQL `audit_log` table
- **Structured logging**: Replace print/logging with `structlog` — JSON output, no PII in logs, correlation IDs per request
- **Data retention policy**: Document how long quiz data is stored, add `DELETE /api/admin/users/{id}/data` for GDPR-style data deletion
- **Regeneration safety**: Feedback-driven regeneration runs eval framework (L1+L2) — content only replaced if no regression. Admin must approve regenerated content before it goes live.
- **Health check hardening**: `/health` endpoint checks PostgreSQL connectivity, disk space, memory. Returns 503 if degraded.
- **Rate limiting on admin API**: Prevent abuse of regeneration endpoint (expensive LLM calls)
- **Input sanitization on quiz editor**: Admin-provided question text sanitized before storage and rendering

### Prompt v3 Iteration (moved from v0.5 — pairs with feedback loop)
- New `generate_v3.py` in `backend/evals/prompt_registry/variants/`
- **Target improvements:** deeper pedagogical content (cite specific skills gaps with concrete examples), better URL grounding for "Further Reading" (only verified URLs from research context), stronger practice/assessment integration (at least 2 practice questions per module)
- **Validation:** A/B comparison against v2 on cs224n dataset using existing eval framework (L1 structural + L2 LLM judges). Content only ships if no regression.
- Feedback loop data (per-topic weakness scores from quiz results) injected into v3 prompt via `feedback_context`

### SCORM Export (moved from v0.7 — procurement enabler)
- ZIP package with `imsmanifest.xml`, self-contained HTML quiz, all generated content (PDF, PPT, video links)
- Direct LMS import — Canvas, Moodle, Blackboard all support SCORM 1.2
- **Why SCORM 1.2 over 2004:** widest LMS support, simpler implementation, sufficient data model for MCQ quizzes. SCORM 2004 upgrade deferred unless a university partner specifically requires it.
- New file: `backend/services/scorm_builder.py`

### Evidence Baseline (moved from v0.5 — pairs with admin analytics)
- Internal study: 2-3 educators rate a batch of pipeline outputs against a structured rubric
- Output: one-page "evidence card" with preliminary learning quality scores
- Conducted via admin dashboard (educator accounts with `role: "admin"`)
- **Why now:** universities will ask "how do you know this works?" — preliminary internal data beats nothing, opens co-research conversations

### GitHub Actions CI
- Workflow: `ruff check` → `pytest --randomly-seed=last -n auto --cov --cov-fail-under=80` → `pip-audit` (dependency vulnerability scan)
- Coverage gating: `--cov-fail-under=80` — PR cannot merge if coverage drops below 80%
- Test randomization: `--randomly-seed=last` for reproducible random order in CI (no `pytest-sugar` in CI — use `-p no:sugar`)
- Triggered on push to main and PRs
- Dependabot config for automated dependency updates
- New files: `.github/workflows/ci.yml`, `.github/dependabot.yml`, `.github/PULL_REQUEST_TEMPLATE.md`

### Done when
- Admin dashboard shows topic heatmap, question analytics, student trends, system health
- Admin can edit/delete/add quiz questions through polished UI
- Feedback loop works end-to-end: quiz data → analysis → regeneration → eval → conditional replace
- Prompt v3 passes A/B eval against v2 (no regression)
- SCORM ZIP exports and imports into Moodle/Canvas
- Evidence card produced from educator rubric ratings
- GitHub Actions CI runs on all PRs
- Audit log captures all admin actions
- Structured logging throughout backend
- Full stack deploys: React + FastAPI + PostgreSQL (Cloud SQL) + Kokoro video
- `make test` passes, `make lint` clean
- `cz bump --increment MINOR` → v0.6.0

---

## v0.7 — Student Engagement & Competitive Features
> Mind maps, flashcards, RAG chat, student dashboard. Closes the engagement gap with NoteGPT while leveraging CR8's curriculum-grounded advantage.

### Why v0.7
NoteGPT (B2C, $19.92/mo) offers mind maps, flashcards, and RAG chat. Universities expect visual summaries and active recall tools. These features close the engagement gap while leveraging CR8's advantage — competitors generate from generic prompts, CR8 generates from actual university materials + industry research data.

### Features

| Feature | Description | CR8 Advantage |
|---------|-------------|---------------|
| **Mind maps** | Mermaid.js from module JSON → SVG/PNG. Topic nodes linked to gap analysis. | Curriculum-grounded, not generic |
| **Flashcards + SM-2** | Spaced repetition (SM-2 algorithm), Bloom's taxonomy tagged, Anki `.apkg` export | Quiz failure rates auto-seed difficulty; gap-aware |
| **RAG chat** | ChromaDB retrieval + GPT-5-mini streaming. Students ask questions about course content. Citations shown as chips. | ChromaDB already populated by pipeline — zero extra ingestion |
| **Student dashboard** | Topic mastery radar chart, flashcard progress, recommended study areas, quiz history | Institutional + individual views; data stays with university |

### New files (estimated)
| File | Purpose |
|------|---------|
| `backend/services/mindmap_builder.py` | Module JSON → Mermaid.js syntax → SVG/PNG render |
| `backend/services/flashcard_builder.py` | Module + quiz data → SM-2 flashcard set, `.apkg` export |
| `backend/services/chat_service.py` | ChromaDB RAG + streaming LLM, citation extraction |
| `backend/prompts/chat.py` | RAG chat system prompt with citation constraints |
| `frontend/react-app/src/pages/StudentDashboard.tsx` | Mastery radar, flashcard progress, study recommendations |
| `frontend/react-app/src/pages/MindMapPage.tsx` | Interactive mind map viewer (Mermaid.js rendered) |
| `frontend/react-app/src/pages/FlashcardPage.tsx` | SM-2 flashcard review interface, Anki export button |
| `frontend/react-app/src/pages/ChatbotPage.tsx` | RAG chat sidebar, streaming messages, citation chips |
| `frontend/react-app/src/components/ChatMessage.tsx` | Message bubble with citation chips |
| `frontend/react-app/src/components/MasteryRadar.tsx` | Recharts radar chart for topic mastery |
| `frontend/chat_routes.py` | `/api/chat/*` endpoints |
| `frontend/flashcard_routes.py` | `/api/flashcards/*` endpoints |

### Database additions
```sql
-- Chat tables (schema pre-included in v0.5.0 — already in DB)
-- chat_sessions, chat_messages — no migration needed

-- Flashcard tables (new migration)
CREATE TABLE flashcard_decks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id VARCHAR(12) REFERENCES jobs(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE flashcards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    deck_id UUID REFERENCES flashcard_decks(id) ON DELETE CASCADE,
    front TEXT NOT NULL,
    back TEXT NOT NULL,
    blooms_level VARCHAR(20),
    source_section VARCHAR(255),
    -- SM-2 scheduling fields
    ease_factor DECIMAL(3,2) DEFAULT 2.50,
    interval_days INTEGER DEFAULT 1,
    repetitions INTEGER DEFAULT 0,
    next_review_at TIMESTAMPTZ DEFAULT now(),
    sort_order INTEGER DEFAULT 0
);
```

### Done when
- [ ] Mind maps render from any completed pipeline job
- [ ] Flashcards with SM-2 scheduling, Anki `.apkg` export works
- [ ] RAG chat answers questions with citations from course content
- [ ] Student dashboard shows mastery radar and study recommendations
- [ ] `make test` passes, `make lint` clean
- [ ] `cz bump --increment MINOR` → v0.7.0

---

## v0.8 — Production Readiness
> Multi-user job queuing, TTS upgrade, eval dataset expansion, content enhancements. Makes the product robust enough for a real university pilot.

### Multi-User Job Queuing
Replace the global single-job lock with Cloud Tasks + GCS-based state. The current architecture blocks all users when one job is running — multiple university stakeholders demoing simultaneously will reveal this immediately.

- **Approach:** Submit jobs to Cloud Tasks queue → worker reads from queue → state stored in PostgreSQL → frontend polls for progress
- **Context:** GCP Cloud Tasks is serverless, pay-per-use ($0.40/million tasks), integrates natively with Cloud Run. No Kubernetes needed.
- New files: `backend/services/task_queue.py`, `backend/workers/pipeline_worker.py`

### TTS Upgrade
Evaluate next-gen open-source TTS models as primary provider, keeping Kokoro as CPU fallback.

| Model | License | Params | Key Feature | Status |
|-------|---------|--------|-------------|--------|
| **Chatterbox** | MIT | 300M | Voice cloning from 2s sample, best open-source naturalness (2025) | Candidate |
| **CosyVoice 3** | Apache 2.0 | — | Multilingual (50+ languages), zero-shot voice cloning | Candidate |
| **Kokoro** | Apache 2.0 | 82M | Current provider, CPU-friendly, good quality | Fallback |

- Research note required before implementation: `docs/research/tts-upgrade.md`
- Must pass A/B listening test vs Kokoro before shipping

### Eval Dataset Expansion
Capture 3-5 domain datasets beyond `cs224n` using `capture_dataset.py`. Validates that prompt v3 generalises across disciplines — critical for selling to multi-faculty universities.

| Domain | Target Dataset |
|--------|---------------|
| Engineering | Circuits, thermodynamics |
| Health Sciences | Pharmacology, anatomy |
| Business | Finance, operations management |

### Content Enhancements
| Enhancement | Description |
|-------------|-------------|
| **PPT citations** | In-slide references linking to source curriculum pages |
| **Custom templates** | `.pptx` template support for institutional branding |
| **Multi-file batch** | Process multiple PDFs with combined gap analysis across all documents |
| **AI diagrams** | LLM-generated diagrams and charts from curriculum data |

### Done when
- [ ] Multiple jobs run concurrently without blocking
- [ ] TTS upgrade passes A/B quality test vs Kokoro
- [ ] 3+ eval datasets captured and prompt v3 evaluated across all
- [ ] At least 2 content enhancements shipped
- [ ] `make test` passes, `make lint` clean
- [ ] `cz bump --increment MINOR` → v0.8.0

---

## v0.9 — LMS & Integration
> LTI 1.3, avatar video, accessibility audit, DPIA/DPA. Makes the product deployable inside university LMS ecosystems and legally compliant for pilot contracts.

### LTI 1.3 Integration
Standard for connecting learning tools to LMS platforms (Canvas, Moodle, Blackboard).

- **SSO:** OAuth 2.0 / SAML 2.0 via institution's IdP — students log in with university credentials
- **Grade passback:** xAPI statements sent back to LMS gradebook
- **Launch flow:** LTI 1.3 launch from within LMS → CR8 opens in iframe/new tab with authenticated session
- **Context:** LTI 1.3 is the IMS Global standard (now 1EdTech). Canvas and Moodle support it natively. Blackboard supports LTI 1.3 via REST API.
- **First deliverable:** 2-page technical brief for IT procurement teams (does not need to be fully built before pilot, but must be plausibly planned)

### Avatar Video Overlay
Talking head composited over slide videos for a more engaging lecture experience.

| Option | Source | Quality | Speed | GPU Req |
|--------|--------|---------|-------|---------|
| **SadTalker** | CVPR 2023 | Realistic head motion from audio | Moderate | T4+ |
| **MuseTalk** | 2024 | Faster, lower quality | Fast | T4+ |

- Optional per-job: `avatar=true` flag adds talking head to corner of slide video
- Runs on existing GPU video service infrastructure (NVIDIA L4)
- Research note required: `docs/research/avatar-overlay.md`

### Accessibility Audit (WCAG 2.1 AA)
UK universities have legal obligations under the Equality Act 2010 and Public Sector Bodies Accessibility Regulations 2018.

| Area | Requirements |
|------|-------------|
| Screen reader | All interactive elements labelled, ARIA attributes |
| Colour contrast | 4.5:1 for normal text, 3:1 for large text |
| Keyboard navigation | All features accessible without mouse |
| Video captions | Auto-generated captions on all videos (from TTS script) |
| Transcripts | Downloadable text transcript for each video |

### DPIA + DPA
Non-negotiable before any university pilot contract.

- **DPIA** (Data Protection Impact Assessment) — Required by UK GDPR for high-risk processing. Covers: curriculum content handling, student quiz data, model training opt-outs.
- **DPA** (Data Processing Agreement) — UK GDPR Article 28 compliant. Covers: data residency (UK/EU), subprocessors (OpenAI, GCP), retention periods, breach notification.
- **Action:** Engage UK-based data privacy solicitor. Budget: ~£3-5K.

### Done when
- [ ] LTI 1.3 technical brief written and reviewed by 1+ university IT contact
- [ ] Avatar overlay works on at least one video format
- [ ] WCAG 2.1 AA audit completed, critical issues resolved
- [ ] DPIA and DPA drafted by solicitor
- [ ] `make test` passes, `make lint` clean
- [ ] `cz bump --increment MINOR` → v0.9.0

---

## v1.0 — University Pilot Release
> No new features — stabilisation and validation. The "ready for a real pilot" milestone.

### Acceptance criteria
- [ ] All v0.5-v0.9 features stable and deployed on Cloud Run
- [ ] Full CI/CD pipeline: GitHub Actions → staging → production
- [ ] Published evidence card (educator rubric ratings from v0.6)
- [ ] LMS integration verified with at least one Canvas/Moodle instance
- [ ] DPIA and DPA signed off by solicitor
- [ ] Runbook for university IT teams (deployment, auth, data handling)
- [ ] Load testing: 10 concurrent users, 3 simultaneous pipeline jobs
- [ ] Security: Snyk SCA + code scan clean, pip-audit clean, no critical CVEs
- [ ] `cz bump --increment MINOR` → v1.0.0

---

## Post-1.0 Phase 1 — Adaptive Intelligence (3-6 months post v1.0)
> The adaptive learning loop: quiz data drives content personalisation

### PPO + DKVMN Hybrid
- **DKVMN** (Dynamic Key-Value Memory Networks, Zhang et al. 2017) — models student knowledge as key-value memory updated after each quiz response. Tracks per-concept mastery.
- **PPO** (Proximal Policy Optimization, Schulman et al. 2017) — optimises content selection policy. Given a student's knowledge state, selects the next content piece that maximises learning gain.
- **Minimum data requirement:** ~100+ quiz completions per topic for meaningful signal. This is why adaptive intelligence is post-1.0 — it needs pilot data.

### ALEKS-Style Diagnostic
- 20-30 question adaptive diagnostic for new students
- Estimates initial knowledge state before quiz data accumulates (cold start problem)
- Routes students to appropriate difficulty levels immediately

### Multi-Agent Expansion
5 additional agents beyond the current 3 (Ingest, Research, Generate):

| Agent | Purpose |
|-------|---------|
| **Assessment** | Generates adaptive assessments based on knowledge state |
| **Analytics** | Computes learning metrics, cohort comparisons, trend analysis |
| **QA** | Validates generated content quality (automated L1+L2 checks) |
| **Adaptation** | Selects and modifies content based on student performance |
| **Content** | Fine-grained generation (flashcards, summaries, practice problems) |

---

## Post-1.0 Phase 2 — Production Scale (6-12 months post v1.0)
> Enterprise infrastructure for multi-university deployment

### Infrastructure
- Cloud Run → Kubernetes (GKE or AWS EKS) for multi-tenancy
- Event streaming (Kafka) for pipeline orchestration and analytics
- CDN for video delivery (Cloud CDN or CloudFront) with adaptive bitrate
- Multi-region deployment for latency and compliance

### Validation
- Published efficacy study with university partner (peer-reviewed if possible)
- International expansion beyond UK HEIs
- SOC 2 Type I certification (if targeting US universities)

---

## Budget Reference

| Phase | Timeline | Indicative Budget |
|-------|----------|------------------|
| POC (v0.4.x — current) | Now | API costs ~$50-100/month + GPU Cloud Run ~$15-30/month |
| MVP (v0.5-v0.7) | 0-6 months | ~£30-40K (salaries + infra) |
| Scale (v0.8-v1.0) | 6-12 months | ~£150-200K |
| Production (Post-1.0) | 12-18+ months | ~£400-600K/year |

---

## Cross-Cutting: LangSmith Deep Integration (woven into all updates)

### Current State
- `LANGCHAIN_TRACING_V2=true` and `langchain_project` are in config, but **`LANGCHAIN_API_KEY` is missing entirely**
- Config values are Pydantic fields but **never applied as OS env vars** — auto-tracing silently fails unless set externally
- 11 `run_name` annotations exist on LLM calls — this is good but it's the ONLY instrumentation
- Tavily, ChromaDB, file parser, PDF/PPT builders, eval judges — all **invisible** to LangSmith
- `EvalResult.langsmith_run_id` field exists but is always `null`
- LangSmith Datasets, Prompt Hub, Annotation Queues, Online Evaluation — **none used**
- ThreadPoolExecutor parallel calls may produce orphan traces (broken context propagation)

### v0.4 — LangSmith Foundations
| Change | File |
|--------|------|
| Add `langchain_api_key: str = ""` to config | [config.py](backend/config.py) |
| Apply LangSmith env vars at import time (`os.environ[...]`) | [config.py](backend/config.py) |
| Add `LANGCHAIN_API_KEY` to `.env.example` | [.env.example](.env.example) |
| Attach `job_id`, `output_formats`, `file_count` metadata to `pipeline.invoke()` | [run_pipeline.py](backend/run_pipeline.py) |
| Wrap `tts_engine.py` and `script_parser.py` with `@traceable` | New files |
| Wrap `export_slides_as_images()` with `@traceable(run_type="tool")` | [file_parser.py](backend/services/file_parser.py) |

### v0.5 — LangSmith Enrichment
| Change | File |
|--------|------|
| Add model tier + severity metadata to every `llm.invoke()` call | All 3 agent files |
| Wrap Tavily `search()` with `@traceable(run_type="tool")` | [web_search.py](backend/services/web_search.py) |
| Wrap ChromaDB `query()` with `@traceable(run_type="retriever")` | [chromadb_store.py](backend/services/chromadb_store.py) |
| Wrap `ingest_node`, `research_node`, `generate_node` with `@traceable(run_type="chain")` | All 3 agent files |
| Fix ThreadPoolExecutor context propagation (`get_current_run_tree`) | All 3 agent files |
| Upload production prompts to LangSmith Prompt Hub | [backend/prompts/](backend/prompts/) |
| Mirror eval datasets to LangSmith Datasets | [backend/evals/](backend/evals/) |

### v0.6 — LangSmith Advanced
| Change | File |
|--------|------|
| Wrap eval judge calls with `@traceable(run_type="llm", project_name="cr8-evals")` | [base_judge.py](backend/evals/judges/base_judge.py) |
| Populate `langsmith_run_id` in `EvalResult` | [runner.py](backend/evals/harness/runner.py) |
| Submit eval scores as LangSmith feedback on original pipeline runs | [scorer.py](backend/evals/harness/scorer.py) |
| Configure Annotation Queues for failed validations and critical-severity runs | LangSmith UI |
| Configure Online Evaluation automations (structural checks on production traces) | LangSmith UI |
| Attach token count + estimated cost metadata to each LLM span | All agent files |

---

## Cross-Cutting: Agentic Guide Compliance Gaps (fix alongside updates)

### v0.4 Fixes
| Gap | Fix |
|-----|-----|
| No SECURITY.md | Create at project root |
| `feature_list.json` stale | Fix `agent_readiness_setup` → `"complete"` |
| `backend/evals/` missing README.md | Create README.md |
| PostToolUse hook swallows failures (`\|\| true`) | Change to `ruff check --fix` or at minimum remove `\|\| true` |
| CLAUDE.md Skills section only lists 1 of 4 skills | Add `commit-ready`, `coverage-report`, `new-feature` |

### v0.5 Fixes
| Gap | Fix |
|-----|-----|
| No `.github/` directory | Create with `copilot-instructions.md` (symlink to AGENTS.md), Dependabot config, PR template |
| No CI/CD | Add GitHub Actions workflow: ruff + pytest + pip-audit |
| CORS wide open | Lock down (already in plan) |
| Hardcoded password | Env-configurable (already in plan) |
| Negative instructions in CLAUDE.md | Rewrite 5-6 "don't/never" → positive framing |

### v0.6 Fixes
| Gap | Fix |
|-----|-----|
| Stop hook doesn't run tests | Add `make test` to Stop hook (or at least `pytest -x -q`) |
| No SAST scanning | Add CodeQL or Bandit to CI workflow |

---

## Cross-Cutting: Token Optimization & Code Intelligence

> Research: `docs/research/code-intelligence-tools.md`, `docs/research/gitlab-knowledge-graph.md`
> Summary: `PM-Docs/CODEBASE-INTELLIGENCE-SUMMARY.md`

### v0.5.2 — Add Tools
| Change | File | Impact |
|--------|------|--------|
| Add CodeGrok MCP (semantic code search) | `.claude/mcp.json` | 10x token savings per code query |
| Add GitHub Projects V2 MCP (sprint tracking) | `.claude/mcp.json` | Replace markdown-grep with queryable board |
| Document new MCPs | `CLAUDE.md` | Agent awareness |
| Add token optimization guidelines | `mk-docs/getting-started/developer-workflow.md` | Team discipline |

### v0.5 Post-Launch — Upgrade Tracking
| Change | File | Impact |
|--------|------|--------|
| Create Notion feature database | Notion (external) | 70% faster feature queries vs markdown |
| Export PROGRESS.md to Notion | Notion + `PROGRESS.md` | Single source of truth for features |

### v0.6 — Evaluate Deeper Tools
| Change | File | Impact |
|--------|------|--------|
| Evaluate code-graph-mcp (needs Python 3.12) | `.claude/mcp.json` | Call graphs + dependency analysis |
| Evaluate Axon MCP (if codebase >30K LoC) | `.claude/mcp.json` | Full knowledge graph with impact analysis |
| Review token savings metrics from v0.5 | `PM-Docs/token-usage-report.md` | Data-driven tool decisions |

### Token Optimization Behaviours (Immediate — No Tools)
| Behaviour | When | Expected Savings |
|-----------|------|-----------------|
| `/clear` between phases | Switching backend ↔ frontend work | 30% per session |
| Plan mode before multi-file changes | Any change touching 5+ files | 40-60% per task |
| Extended thinking control | Disable for trivial edits | 10-20% per edit |
| Keep CLAUDE.md <500 lines | Always (currently 90 lines) | 10% per response |
| Multi-session architecture | Backend / Frontend / Docs as separate sessions | 40-50% total |

### Rejected Tools (with rationale)
| Tool | Reason |
|------|--------|
| GitLab Knowledge Graph | Python cross-file refs incomplete; requires platform migration from GitHub |
| Linear MCP | $20/person/month; overkill for 2-person team (revisit at v1.0+ / 5+ people) |
| CodePathfinder | AGPL license incompatible with CR8's deployment model |
| CodeIndexer / Milvus | Requires separate vector DB infrastructure; overkill for ~15K LoC |
| Plane | Extra self-hosted infrastructure; Notion is simpler |

---

## Versioning Scheme

```
v0.3.0  ← clean baseline (362 tests)
v0.4.0  ← Kokoro TTS video pipeline (507 tests)
  v0.4.1  ← agent scaffolding, bugfixes
  v0.4.2  ← CPU video service, 3-tier fallback (626 tests)
v0.5.0  ← React frontend + Quiz platform (IN PROGRESS)
  v0.5.1  ← dark mode, polish
v0.6.0  ← Admin dashboard + feedback loop + Prompt v3 + SCORM
v0.7.0  ← Student engagement (mind maps, flashcards, RAG chat)
v0.8.0  ← Production readiness (job queuing, TTS upgrade, eval datasets)
v0.9.0  ← LMS & integration (LTI 1.3, avatar, WCAG, DPIA)
v1.0.0  ← University pilot release (stabilisation, no new features)
Post-1.0 Phase 1 ← Adaptive intelligence (PPO+DKVMN, multi-agent)
Post-1.0 Phase 2 ← Production scale (Kubernetes, multi-region)
```

All bumps via `cz bump` — auto-updates `pyproject.toml` version, creates git tag `v{version}`, updates `CHANGELOG.md`.

## Security Cumulative Progress

| Gap | Fixed in |
|-----|----------|
| LangSmith tracing default on | v0.4 (change to opt-in) |
| No SECURITY.md | v0.4 |
| Temp file cleanup | v0.4 |
| Hardcoded password | v0.4 (env-configurable AUTH_PASSWORD) |
| CORS wide open (`*`) | v0.5 (configurable whitelist) |
| No security headers | v0.5 (CSP, X-Frame-Options, etc.) |
| No dep scanning | v0.5 (pip-audit / Dependabot) |
| No audit logging | v0.6 |
| No structured logging | v0.6 |
| No RBAC | v0.6 |
| No data retention policy | v0.6 |
| No SAST scanning | v0.6 (CodeQL/Bandit) |
| No CI/CD pipeline | v0.6 (GitHub Actions) |
| No WCAG compliance | v0.9 |
| No DPIA/DPA | v0.9 |

## Documentation Strategy
- **`PM-Docs/Loop_Intelligence.md`** — Strategic roadmap for strategy agent + coding agent context. Keep under 400 lines. Refresh after each minor version bump.
- **`PM-Docs/roadmap.md`** (this file) — File-level implementation specs, schemas, API routes, done-when checklists.
- **`PROGRESS.md`** — Agent-facing session state. Update at the end of each coding session. Keep concise.
- **`feature_list.json`** — Machine-readable status. Update after each `cz bump`.
- **`CHANGELOG.md`** — Auto-generated by `cz bump`. No manual edits.
- **Notion Feature Database** (v0.5+) — Queryable feature tracker (Name | Status | Phase | Owner | Blocker | PR). Replaces manual search through markdown. `PROGRESS.md` remains as session handoff cache. See `PM-Docs/CODEBASE-INTELLIGENCE-SUMMARY.md`.

## Verification
After each update: `./scripts/init.sh` (ruff + full test suite + docs build), then `cz bump`. Update `PROGRESS.md`, `feature_list.json`, and Loop_Intelligence.md task checkboxes at the end of each update.
