# Changelog

All notable changes to CR8 are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html)

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

## v0.5.0 (2026-03-04)

### Feat

- add 3 dev workflow skills — commit-ready, coverage-report, new-feature
- agent-readiness setup, docs migration, and March 2026 hardening
- March 2026 hardening — 10 bug fixes, 362-test suite, updated docs
- add authentication, security hardening, and security docs

### Fix

- resolve bugs in frontend, backend, and AI pipeline
