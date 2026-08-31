# Changelog

All notable changes to CR8 are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html)

---

## [Unreleased]

### Changed — Secrets management (Doppler)
- Secrets moved from **GCP Secret Manager** to **Doppler**, injected as environment variables at deploy time
- `deploy.sh` — replaced `--set-secrets` (CPU + GPU services) with a generated mode `600` `--env-vars-file`; reads secret values from the environment (run via `doppler run -- ./deploy.sh <PROJECT_ID>`); aborts early if a required secret is missing
- `deploy.sh --setup` — prints Doppler setup steps instead of `gcloud secrets create`; drops `secretmanager.googleapis.com` from enabled APIs and the `secretmanager.secretAccessor` IAM grants
- `.github/workflows/deploy.yml` — fetches secrets via `dopplerhq/secrets-fetch-action` (needs a `DOPPLER_TOKEN` repo secret scoped to the `prd` config); deploys with `--env-vars-file`
- `.env.example` — documents the `doppler run -- make dev` path; `.env` remains the supported local fallback
- Docs updated: `mk-docs/deployment/gcp-cloud-run.md`, `mk-docs/deployment/index.md`, `mk-docs/security.md`, `SECURITY.md`, `AGENTS.md`

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

## Unreleased — agent_generate.py refactor (51 ruff violations → 0)

### Changed
- `backend/pipeline/agent_generate.py`: eliminated all 51 ruff violations. Added module docstring. Replaced 33 `print()` calls with `logger.info()` / `logger.warning()` using lazy `%s` formatting. Extracted `_GenerateCtx` and `_ScriptCtx` context classes to reduce argument counts across 5 functions (PLR0913). Decomposed `generate_node` (~115 statements) into 12 focused helpers: `_init_generate_ctx`, `_generate_all_modules`, `_build_pdf_and_ppt`, `_build_pdf_ppt_parallel`, `_build_pdf_only`, `_build_ppt_only`, `_handle_scripts_videos`, `_handle_ppt_aligned_path`, `_handle_fallback_path`, `_render_videos`, `_save_raw_outputs`, `_merge_slide_data`. Also extracted `_invoke_with_retry` from `_generate_module` and `_collect_slide_sources` from `_get_slide_images`. Fixed `zip()` without `strict=True` (B905). Removed unused `i` param from `_convert_to_script`.
- `backend/services/file_parser.py`: added module docstring; replaced `elif` after `return` with `if` (RET505); merged `startswith` tuple + `in` comparisons (PIE810/SIM109).

### Tests
- `backend/tests/test_pipeline_agents.py`: updated `_ppt_monolithic_fallback` calls to pass `_GenerateCtx`; fixed section comment headers (ERA001) and unused variable (RUF059).
- `backend/tests/test_agent_generate.py`: removed unused imports (F401); fixed ambiguous character (RUF003) and unused variable (RUF059); updated all `_generate_module` calls to pass `_GenerateCtx`.
- `backend/tests/test_file_parser.py`: merged nested `with` statements (SIM117).

---

## Unreleased — Test coverage expansion + path traversal hardening

### Added
- `backend/tests/test_agent_generate.py` (44 tests, new file): `_VideoJobInputs` field storage and defaults (including `ppt_path`); `_build_chroma_cache` ChromaDB routing and placeholder text; `_validate_module` length gate and missing-section reporting; `_generate_module` severity-based model routing, retry logic, and best-effort fallback after max retries; `generate_node` dual PDF+PPT parallel path and PPT-only/monolithic-fallback paths
- `backend/tests/test_file_parser.py` (expanded to 24 total): direct unit tests for `_validate_output_dir` covering symlink traversal, dotdot escape, system-tmp root as allowed base, cwd as allowed base, error message content, and root-path rejection; DPI accuracy assertion (144 DPI on widescreen produces 1920×1080)
- `frontend/tests/test_auth_routes.py` (expanded to 71 total): additional coverage of register, login, refresh, me, and logout edge cases

### Changed
- `backend/services/file_parser.py`: added `_validate_output_dir()` — resolves `output_dir` via `os.path.realpath()` (symlink-aware) and rejects any path not under cwd or the system temp directory; `export_slides_as_images()` now calls this guard before any file operations; DPI default corrected from 150 to 144 (produces exactly 1920×1080 on standard 13.333"×7.5" widescreen slides); PPTX export no longer depends on `pdftoppm` — LibreOffice converts to PDF, then PyMuPDF renders each page

---

## Unreleased — Video Cloud Run Fix + UI Re-run Features

### Added
- `frontend/react-app/src/pages/ResultsPage.tsx`: `AddVideoSection` component — when a completed job was generated without video format, a "Generate Video" button appears and re-runs the pipeline with video included. Calls `POST /api/start` with the existing job ID and extended formats list, then redirects to the progress page.
- `frontend/react-app/src/pages/DashboardPage.tsx`: `JobCard` component gains a "Re-run" button for jobs in `error` or `cancelled` status. Calls `POST /api/start` with the original formats and redirects to the progress page on success.
- `frontend/job_routes.py`: `_persist_job_start()` now handles re-runs — if a job already exists in the DB (identified by `short_id`), it updates `output_formats`, resets `status` to `running`, and clears `progress_pct` / `current_stage` instead of failing on a duplicate insert.

### Fixed
- `backend/pipeline/agent_generate.py`: `_get_slide_images()` catches `FileNotFoundError` from `export_slides_as_images()` and returns `[]` with a warning log instead of raising. This prevents video jobs from crashing on the CPU pipeline container (Cloud Run), which does not have LibreOffice installed.
- `backend/services/gcs_client.py`: `upload_job_inputs()` accepts an optional `pptx_path` parameter. When no local slide images are available and a PPTX path is provided, the PPTX is uploaded to GCS so the remote GPU / CPU-video worker can convert it to PNGs.
- `backend/pipeline/agent_generate.py`: `_VideoJobInputs` dataclass gains a `ppt_path` field. `_build_videos_gpu()` checks whether slide images are absent and a `ppt_path` is set; if so, it passes the PPTX to `GCSVideoClient.upload_job_inputs()` for remote export. The GCS manifest includes `pptx_name` for the remote worker.
- `Dockerfile.gpu` and `Dockerfile.cpu-video`: Added `pymupdf` Python dependency and copied `backend/services/file_parser.py` so GPU and CPU-video workers can perform PPTX-to-PNG conversion using PyMuPDF and LibreOffice.
- `Dockerfile.cpu-video`: Added `libreoffice-impress` system package so the CPU-video worker can convert PPTX to PNGs when remote slide export is requested.
- `gpu_service/worker.py` and `cpu_video_service/worker.py`: Added PPTX detection and export step before TTS synthesis. When the manifest includes `pptx_name`, the worker downloads the PPTX from GCS and calls `export_slides_as_images()` to produce PNGs locally. Guard added to prevent importing `scripts` as a module name.
- `gpu_service/gcs_client.py` and `cpu_video_service/gcs_client.py`: Added `download_pptx(job_id, pptx_name, local_dir)` method to support the new PPTX remote export flow.

---

## Unreleased — E2E Bug Fixes (Post-v0.5.4 Session)

### Bug Fixes

- `frontend/job_routes.py`: Added `_normalize_job()` helper to transform DB job rows into the shape the React frontend expects — renames `output_formats` → `formats[]`, `file_names` → `filename` (first element), maps `short_id`/`progress_pct`/`current_stage` to their frontend field names. `list_jobs` and `get_job` both apply the transform.
- `frontend/job_routes.py`: `GET /api/jobs/{job_id}` now resolves 8-character hex IDs via `get_job_by_short_id()` before falling back to UUID lookup. Fixes the React frontend's use of `short_id` in URLs.
- `frontend/job_routes.py`: Pipeline result persistence now extracts `pdf_path`, `ppt_path`, `video_dir`, and `slide_images` from the top-level result dict and stores them in the `result_meta` JSONB column, so view routes can serve files after a server restart.
- `frontend/middleware.py`: `AuthMiddleware` now exempts `/api/view/` paths from the auth check. Iframes, `<video>`, and `<img>` tags cannot send Bearer headers; the unguessable `short_id` acts as a capability token for content viewer access.
- `frontend/view_routes.py`: `_get_completed_result()` is now `async` and includes a DB fallback — checks in-memory `ProgressCapture` first, then queries `result_meta` from the database for jobs that survived a server restart. Handles `result_meta` arriving as a JSON string or dict from asyncpg. All view route handlers updated to `await` the result.
- `frontend/quiz_routes.py`: `POST /api/quiz/generate` now checks for an existing quiz before triggering generation. If a quiz already exists for the job, the existing `quiz_id` is returned immediately (HTTP 200 with `"existing": true`) rather than generating a duplicate.
- `frontend/react-app/src/pages/ResultsPage.tsx`: Quiz list entries now display an `"(Attempt N)"` label when multiple quiz attempts exist for a job, making it clear which attempt is which.

---


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

## v0.5.5 (2026-03-09)

### Feat

- v0.5.4 — Quiz Agent + Quiz UI (TDD, 3 waves)
- add keyboard navigation to PPT carousel + E2E tests for viewers (v0.5.3 Wave 3)
- add content viewer components — PDF iframe, PPT carousel, video player (v0.5.3 Wave 2)
- add content view endpoints + CSP update for inline viewers (v0.5.3 Wave 1)
- add Vitest + Playwright test infrastructure, fix /assets/ auth (v0.5.2 Wave 3)
- add jobs API module, wire pages to real data, build ResultsPage (v0.5.2 Wave 2)
- scaffold React SPA with glassmorphism design system (v0.5.2 Wave 1)

### Fix

- E2E bug fixes for dashboard, PDF viewer, quiz idempotency, and DB fallback
- E2E bug fixes for quiz pipeline, DB serialization, and auth keys
- security hardening, data integrity fixes, and observability improvements
- add path traversal guard to view endpoints (CWE-23)

## v0.5.1 (2026-03-06)

## v0.4.1 (2026-03-05)

### Fix

- move logger placement in frontend/app.py to fix E402, update stale test counts

## v0.4.0 (2026-03-04)

### Feat

- Kokoro TTS video pipeline, Cloud Run GPU service, dual-service deployment
- add 3 dev workflow skills — commit-ready, coverage-report, new-feature
- agent-readiness setup, docs migration, and March 2026 hardening
- March 2026 hardening — 10 bug fixes, 362-test suite, updated docs
- add authentication, security hardening, and security docs

### Fix

- resolve bugs in frontend, backend, and AI pipeline
