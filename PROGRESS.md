# PROGRESS.md
<!-- Agent cross-session memory. Read at the start of every session.
     Updated at the end of every session using the session-handoff skill. -->

## Current Status
**Last updated:** 2026-03-04
**Overall project phase:** Cloud Run GPU service implemented — dual-service deployment, GCS data transfer, 507 tests
**Current version:** v0.4.0

## What's Working
- Full 3-agent pipeline end-to-end (Ingest → Research → Generate)
- All output formats: PDF, PPT, video script
- **Kokoro TTS local video pipeline** (`VIDEO_PROVIDER=kokoro`) — slides + voiceover MP4
- **GPU service video offload** — when `GPU_SERVICE_URL` is set, TTS + ffmpeg run on NVIDIA L4 in europe-west1; CPU service uploads slides to GCS and downloads finished MP4s
- **GCS data transfer** — `GCSVideoClient` (upload slide PNGs + manifest, download MP4s, cleanup)
- **GPU HTTP client** — `GPUVideoClient` (submit job, poll with progress lines, identity token auth)
- **Dual-service deployment** — `deploy.sh` builds and deploys CPU service (europe-west2) + GPU service (europe-west1) separately
- **Video checkbox enabled in UI** (Kokoro TTS, was previously disabled/labelled HeyGen)
- **PPTX upload support** — drag-drop zone accepts both PDF and PPTX; magic byte validation
- **Structured console logging** — `logging.basicConfig()` guarded in `config.py`; all backend services log with timestamps
- **Video error/warning surfacing** — `ProgressCapture` captures `[Video] ERROR:` and `[Video] WARNING:` lines; UI shows yellow warning box on completion
- **Configurable login password** — `AUTH_PASSWORD` env var (default: `CR8-AI`); no longer hardcoded
- **Unified video provider validation** — `_validate_video_provider()` shared between CLI and web; covers heygen, synthesia, kokoro, and unknown providers
- 507-test suite — all passing, ruff clean
- **Video slides from generated PPT** (was: original PDF) — fixed `_get_slide_images()` bug
- **Two-phase video pipeline** — sequential TTS (shared engine) → parallel ffmpeg composition
- **GPU acceleration** — MPS/CUDA for TTS, hardware H.264 encoding (VideoToolbox/NVENC/QSV/AMF), per-worker thread control
- **Stage-aware ETA** — per-stage time budgets replace linear extrapolation
- Authentication (bcrypt session auth on all protected routes)
- Docker + GCP Cloud Run deployment
- Evaluation framework (L1 structural + L2 LLM judges, A/B comparison CLI)
- MkDocs documentation site (49 pages, Material theme)
- Agent-readiness scaffolding complete (AGENTS.md, skills, hooks, rules, subagents)
- LangSmith tracing opt-in with metadata (job_id, output_formats, file_count)
- SECURITY.md vulnerability disclosure policy
- `slide_images` field is `NotRequired[list[str]]` in `PipelineState` — correctly optional

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

### Architecture
```
CPU service (europe-west2, 2 vCPU, 4 GiB)   GPU service (europe-west1, 4 vCPU, 16 GiB, L4)
─────────────────────────────────────────    ──────────────────────────────────────────────
Pipeline: Ingest → Research → Generate        POST /api/v1/video-jobs (receive job)
Slide export → GCS upload ──────────────────> Download slides from GCS
Poll /api/v1/video-jobs/{id} <──────────────── Kokoro TTS + ffmpeg on NVIDIA L4
Download MP4s from GCS <──────────────────── Upload MP4s to GCS
```

### Test Count
- 507 tests (was 427) — new tests for `GCSVideoClient`, `GPUVideoClient`, `_build_videos_dispatch`, `gpu_service` worker/endpoints, `gpu_utils`, and additional coverage

---

## GPU Acceleration Sprint (2026-03-04 Session)

### New Files
- `backend/services/gpu_utils.py` — central GPU/hardware detection: `get_torch_device()` (CUDA > MPS > CPU), `get_ffmpeg_encoder()` (VideoToolbox > NVENC > QSV > AMF > libx264)

### Performance
- `backend/services/tts_engine.py` — Kokoro TTS loads on GPU (MPS/CUDA) via `get_torch_device(settings.video_device)`
- `backend/services/video_builder.py` — hardware H.264 encoder auto-detected; per-worker `-threads` flag prevents CPU contention
- `frontend/app.py` — ETA time budgets calibrated from measured e2e benchmark (see below)

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

### Config
- `backend/config.py` — `video_device: str = "auto"` (auto | cpu | mps | cuda)
- `.env.example` — `VIDEO_DEVICE=auto`

### Tests
- `backend/tests/test_tts_engine.py` — soundfile mock fixed for locally-installed package (`@patch("soundfile.write")`)
- `frontend/tests/test_progress_capture.py` — Video budget assertion updated (1200→3600)
- All 427 tests passing (before GPU service sprint)

---

## Hardening Sprint Changes (2026-03-04 Session)

### Security
- `frontend/app.py` — `AUTH_PASSWORD` env var (default: `CR8-AI`) replaces hardcoded password
- `.env.example` — `AUTH_PASSWORD=CR8-AI` entry added with production guidance

### Correctness / Architecture
- `backend/run_pipeline.py` — `_validate_video_provider()` shared function used by both `main()` and `run_job()`; now covers heygen, synthesia, kokoro, and unknown providers with proper error messages
- `backend/pipeline/state.py` — `slide_images` changed to `NotRequired[list[str]]` (correctly optional)
- `backend/config.py` — `logging.basicConfig()` guarded with `if not logging.root.handlers:` to prevent duplicate entries

### Dead Code Removal
- `backend/services/video_builder.py` — removed `_build_kokoro_video()` (superseded by two-phase `_build_kokoro_videos()`); removed unused `tempfile` and `TTSEngine` TYPE_CHECKING imports

### Import Cleanup
- `backend/pipeline/agent_generate.py` — `export_slides_as_images` moved from deferred inline import to top-level import

### Observability
- `backend/services/tts_engine.py` — `logger.debug()` added alongside `print()` in `synthesize_segments()`

### Tests
- `backend/tests/test_run_pipeline.py` — heygen/synthesia tests updated to check for missing keys; unknown provider test added. Total: 9 tests (was 8)
- `frontend/tests/test_api.py` — `AUTH_PASSWORD` env var set before module import

### Test count: 427 (was 426)

---

## v0.4+ Changes (2026-03-04 Session)

### Bug Fixes
- `backend/pipeline/agent_generate.py` — `_get_slide_images()` now accepts explicit `ppt_path` param; videos use generated PPT slides instead of original PDF

### Performance
- `backend/services/video_builder.py` — Two-phase pipeline: sequential TTS (shared engine) → parallel ffmpeg (`VIDEO_MAX_WORKERS=12`). `preset='fast'` ~2x faster.
- `backend/config.py` — `hf_token` env propagation, `video_max_workers` default → 12

### Frontend
- `frontend/app.py` — `STAGE_TIME_BUDGETS`, `stage_start_time`, new progress API fields
- `frontend/templates/index.html` — `computeETA()` with per-stage budgets

### Infrastructure
- `Dockerfile` — `libreoffice-impress` added
- `.env.example` — `HF_TOKEN=`, `VIDEO_MAX_WORKERS=12`

### Tests & Docs
- 7 new stage-budget tests, video builder tests rewritten. Total: 426 (was 404)
- All docs updated: test counts, VIDEO_MAX_WORKERS, video pipeline descriptions, system deps

---

## v0.4 Changes (Prior Sprint)
### New Files
- `backend/services/script_parser.py` — parses `[SLIDE N]` markers from video scripts
- `backend/services/tts_engine.py` — Kokoro TTS wrapper (lazy KPipeline, path validation)
- `backend/tests/test_script_parser.py` (10 tests)
- `backend/tests/test_tts_engine.py` (10 tests, soundfile stubbed via sys.modules)
- `SECURITY.md`, `backend/evals/README.md`
- `docs/research/kokoro-tts.md`, `docs/research/moviepy-v2.md`, `docs/research/pymupdf-slide-export.md`

### Modified Files
- `backend/config.py` — kokoro_voice, kokoro_lang, video_fps, langchain_api_key, tracing opt-in; `logging.basicConfig()` at module import
- `backend/pipeline/state.py` — added `slide_images: list[str]`
- `backend/services/file_parser.py` — `export_slides_as_images()` (PDF via PyMuPDF, PPTX via LibreOffice); `logging` added
- `backend/services/video_builder.py` — `_build_kokoro_video()`, provider-conditional dispatch; `logging` + `@traceable` on `build_videos`, `_build_kokoro_video`, `_build_kokoro_videos`; early RuntimeError if slide_images empty
- `backend/services/tts_engine.py` — `logging` added; logs model load, synthesis duration, empty-audio guard
- `backend/services/script_parser.py` — `logging` added; logs segment counts, warns on missing markers
- `backend/pipeline/agent_generate.py` — `_video_kwargs()`, `_get_slide_images()` helpers
- `backend/run_pipeline.py` — kokoro provider allowed, LangSmith metadata on invoke
- `frontend/app.py` — STAGE_WEIGHTS rebalanced (Video: 2→25%); upload endpoint accepts PDF + PPTX with magic byte validation; `/api/start` finds both `.pdf` and `.pptx` files; ProgressCapture captures `[Video] ERROR/WARNING:` into `warnings` list
- `frontend/templates/index.html` — drop zone says "PDF or PPTX", file input accepts `.pdf,.pptx`, JS validation updated; video checkbox enabled, label changed from "HeyGen" to "Kokoro TTS"; yellow warning box on completion when video errors occur
- `frontend/tests/test_api.py` — 11 new tests: 6 for PPTX upload, 4 for video UI/pipeline, 1 for empty slide_images guard
- `backend/tests/test_video_builder.py` — 2 existing tests fixed to provide slide_images; 1 new test for empty slide guard
- `Dockerfile` — added ffmpeg, espeak-ng, poppler-utils
- `pyproject.toml` — added kokoro>=0.9, moviepy>=2.0, soundfile>=0.12
- `.env.example` — kokoro vars, LANGCHAIN_API_KEY, VIDEO_PROVIDER=kokoro
- `feature_list.json` — status corrections
- `.claude/hooks.json` — removed `|| true` from PostToolUse
- `CLAUDE.md` — updated Skills section

### Task Completion (T-001 through T-023)
- T-001 through T-023: **ALL DONE** (including T-011 E2E test — passed)

## Known Broken / Blocked
- Cloud Run memory must increase to 4 GiB before deploying Kokoro locally (GPU service removes this constraint)
- HeyGen/Synthesia providers raise NotImplementedError (by design until implemented)

## Next Steps (Prioritised)
1. **v0.5** — Glassmorphism React frontend + Quiz platform + Neon PostgreSQL + JWT auth
3. **v0.6** — Admin dashboard + feedback loop + structured logging + RBAC

## Recent Decisions
| Date | Decision | Rationale | ADR |
|------|----------|-----------|-----|
| 2026-03-04 | GPU service for video (europe-west1, NVIDIA L4) | TTS + ffmpeg are GPU-bound; offloading to a separate service removes RAM pressure from the CPU container and cuts video time from ~28 min to ~2-3 min | — |
| 2026-03-04 | GCS for CPU↔GPU data transfer | Cloud Run services don't share a filesystem; GCS is the natural shared store for slide PNGs and completed MP4s | — |
| 2026-03-04 | Identity token auth for GPU service | Cloud Run service-to-service auth via OIDC identity tokens is the standard GCP pattern; no extra credential management | — |
| 2026-03-04 | `should_use_gpu_service` computed property | Keep dispatch logic out of `agent_generate.py`; a single boolean check keeps the routing clean | — |
| 2026-03-04 | AUTH_PASSWORD env var (default: CR8-AI) | Hardcoded passwords are a security risk; env var allows secure injection via secrets manager in production | — |
| 2026-03-04 | Unified _validate_video_provider() | CLI and web paths had diverged; shared function ensures identical error messages and validation rules regardless of entry point | — |
| 2026-03-04 | slide_images as NotRequired | Field is only populated for Kokoro video jobs; marking it NotRequired is semantically correct and avoids false required-field errors | — |
| 2026-03-04 | Guard logging.basicConfig() | Prevents duplicate log entries when config.py is reloaded or another library configures logging first | — |
| 2026-03-04 | Remove _build_kokoro_video() | Function was superseded by _build_kokoro_videos() (two-phase pipeline); dead code removed to reduce confusion | — |
| 2026-03 | Keep HeyGen, add Kokoro in parallel | Don't break existing code; local TTS is zero-cost alternative | Pending ADR-001 |
| 2026-03 | Lazy imports for kokoro/soundfile/moviepy | Not installed in dev/CI — only loaded when VIDEO_PROVIDER=kokoro | — |
| 2026-03 | sys.modules stubbing in tests | Allows testing tts_engine without installing soundfile | — |
| 2026-03 | LangSmith tracing default → opt-in | Was sending data externally by default without explicit consent | — |

## Environment Notes
- Dev server: `make dev` → http://localhost:8080
- Docs preview: `make docs-serve` → http://localhost:8000
- Tests: `make test` → all 507 pass
- Requires: `.env` file with OPENAI_API_KEY, TAVILY_API_KEY (copy from `.env.example`)
