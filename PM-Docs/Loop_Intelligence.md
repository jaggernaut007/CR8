# CR8 Loop Intelligence — Implementation & Strategy Brief v0.4

## This document is the link between the codebase and the business strategy. It summarises the current technical implementation so the strategic roadmap can be built without needing to read through all the code.

**Last Updated**: 2026-03-04 (GPU acceleration: MPS/CUDA TTS, hardware H.264 encoding, thread control, ETA calibration)
**Previous Version**: Loop Intelligence 0.3 (2026-03-03)
**Version Delta**: Restructured into v0.4→v0.6 roadmap; HeyGen kept (Kokoro added in parallel); Neon PostgreSQL; glassmorphism React frontend; LangSmith deep integration; security hardening at every step; commitizen semver; PPTX upload support added; video UI enabled with Kokoro TTS; web UI login password now configurable via AUTH_PASSWORD env var; GPU acceleration for TTS (MPS/CUDA) and video encoding (VideoToolbox/NVENC/QSV/AMF)

---

## What CR8 Is

CR8 is a multi-agent AI pipeline that transforms university curriculum materials (PDFs, slides) into market-enriched learning guides, quizzes, and slide-narrated videos. The core thesis: **curriculum in, industry-contextualised learning content out — then measure learning, and feed data back to improve content.**

```
Curriculum PDFs → [Ingest Agent] → [Research Agent] → [Generate Agent] →
  ├── Learning Guide PDF
  ├── Gap Analysis PPT
  ├── Video Script (with [SLIDE N] markers)
  ├── Narrated Slide Video (NEW in v0.3 — open-source TTS + ffmpeg)
  └── Interactive Quiz (NEW in v0.3 — tests comprehension, records data)
       └── Feedback Loop → Agent improves future content
```

Built with LangGraph, OpenAI, ChromaDB, Tavily, fpdf2, FastAPI. Prototype operational as CLI + web app on GCP Cloud Run.

---

## Current Implementation Status (as of v0.4)

The content generation prototype is **complete and deployed**.

### The 3-Agent Pipeline (Working)

**Ingest Agent** — Parses uploaded curriculum files (PDF/PPTX), uses GPT-5-nano to summarise each file in parallel (map-reduce for files >15K chars), extracts 10-25 structured topics (with key techniques, domain context, and curriculum scope boundary), chunks and embeds into ChromaDB `curriculum` collection.

**Research Agent** — Takes each topic, runs two parallel Tavily web searches per topic (job skills/applications + industry trends/alternatives), retrieves matching curriculum chunks from ChromaDB, feeds to GPT-5-mini for structured gap analysis (JSON mode) with severity rating (critical/moderate/minor). All topics researched concurrently via ThreadPoolExecutor.

**Generate Agent** — Retrieves context from both ChromaDB collections, looks up gap analysis, uses severity-based model routing (critical → GPT-5.1, moderate/minor → GPT-5-mini). Generates learning modules in markdown with 7 sections. All modules generate in parallel, then compile into chained output: PDF → PPT → Video Script → Video.

### Web UI (Working)

FastAPI web frontend with drag-and-drop PDF and PPTX upload (magic byte validation for both formats), format selection with dependency chain, real-time progress tracking (polling every 3s), file download. Video generation checkbox is enabled and labelled Kokoro TTS — no third-party API keys required. Video errors and warnings are captured during generation and displayed to the user as a yellow notice below the download buttons. Login password is configurable via the AUTH_PASSWORD environment variable (default: CR8-AI); should be set to a strong secret in any internet-facing deployment.

### Deployment (Working)

Dockerised on GCP Cloud Run (europe-west2). Single container, Gunicorn + Uvicorn, ephemeral ChromaDB, secrets from GCP Secret Manager. Scales to zero (~£0 idle cost). Config: 2 GiB RAM (⚠️ **must increase to 4 GiB for video pipeline** — see Section B.8), 2 vCPU, 3600s timeout, max 1 instance.

### Test Coverage

507 tests passing. Zero real API calls. Covers: GCS/GPU clients, video dispatch, GPU service worker/endpoints, gpu_utils, script parser (10), Kokoro TTS (10), slide export (6), video builder (rewritten for two-phase pipeline + GPU dispatch), progress capture (39, +7 for stage time budgets), PPTX upload, video UI, video provider validation. All backend services emit structured console logs with timestamps.

---

## What's New in v0.3: Three Major Additions

### 1. Narrated Slide Video Pipeline (Open-Source, Parallel to HeyGen)

**Problem**: v0.2 video pipeline used HeyGen API (avatar-only on white background, no slide integration). Expensive, vendor-locked, and didn't actually show slides.

**v0.4 Approach**: **HeyGen code stays untouched.** Kokoro TTS is added as a parallel `VIDEO_PROVIDER=kokoro` option. Two-phase implementation. Phase 1 (v0.4) delivers slides + voiceover using fully open-source tools alongside the existing HeyGen path. Phase 2 (future) adds an AI avatar overlay.

#### Phase 1: Slides + Voiceover (Current Sprint)

```
PPT/PDF → slide PNGs → Script → Kokoro TTS → WAV audio per segment →
  MoviePy/ffmpeg composites slide images + audio → Final MP4
```

**Components:**

| Component | Tool | Why This Tool | License |
|-----------|------|---------------|---------|
| Slide export (PDF) | PyMuPDF | Already in codebase via `file_parser.py` | AGPL |
| Slide export (PPTX) | LibreOffice CLI | PPTX → PDF → PNG via pdftoppm | MPL 2.0 |
| Text-to-Speech | Kokoro (82M params) | Runs on CPU, pip install, near-commercial quality, 24kHz. **Requires espeak-ng system dep + ~3.4 GB peak RAM** | Apache 2.0 |
| Video composition | MoviePy v2 | Python-native, `CompositeVideoClip`, easy integration with existing pipeline | MIT |
| Audio/video encoding | ffmpeg | Required by MoviePy, standard | LGPL |

**Implementation in codebase:**

- `file_parser.py` — extend with `export_slides_as_images()` function (PyMuPDF for PDF, LibreOffice CLI for PPTX → intermediate PDF → pdftoppm → PNGs)
- `tts_engine.py` — NEW file. Wraps Kokoro TTS. Input: script text per `[SLIDE N]` segment. Output: WAV files per segment.
- `video_builder.py` — REWRITE. Currently submits to HeyGen API. New version:
  1. Parse script by `[SLIDE N]` markers (already implemented in Script Agent)
  2. For each segment: generate audio via `tts_engine.py`, get duration
  3. Create `ImageClip` from slide PNG, set duration = audio duration
  4. Overlay audio track
  5. Concatenate all segment clips
  6. Write final MP4 (H.264, AAC audio, 1080p)
- `requirements.txt` — add `kokoro>=0.9.4`, `moviepy>=2.0`, `soundfile>=0.12`, `Pillow>=10.0`

**Output spec (measured 2026-03-04, M&A PDF, 33 slides, 5 topics):**
- Resolution: 2000×1125 (matches PPT slide aspect ratio)
- Codec: H.264 (h264_videotoolbox on Mac) + AAC
- Duration per video: 4.2-4.6 min (total: 21.9 min across 5 videos)
- File size per video: 73-95 MB (total: 423 MB)
- Embeddable: standard MP4, plays in any browser `<video>` tag
- Downloadable: served via FastAPI file download endpoint

**Cost**: £0 per video (no API calls). Only compute cost on Cloud Run.

**GPU Acceleration (added 2026-03-04):**

The video pipeline now supports hardware acceleration on both TTS and encoding:

| Component | CPU Fallback | GPU Accelerated |
|-----------|-------------|-----------------|
| Kokoro TTS | PyTorch on CPU | MPS (Apple Silicon), CUDA (NVIDIA) |
| Video encoding | `libx264` (software) | `h264_videotoolbox` (macOS), `h264_nvenc` (NVIDIA), `h264_qsv` (Intel), `h264_amf` (AMD) |

Device detection is handled by `backend/services/gpu_utils.py`. Set `VIDEO_DEVICE=auto` (default) to auto-detect, or force `cpu` for CPU-only mode. Hardware encoders are 5-10x faster than software. Per-worker thread control (`-threads cpu_count // max_workers`) prevents CPU contention during parallel ffmpeg composition.

**Measured E2E benchmark (Mac MPS GPU, 2026-03-04):**

| Stage | Duration |
|-------|----------|
| Ingest + Research + Generate | 5m 39s |
| TTS Synthesis (Kokoro MPS, sequential) | 7m 7s |
| ffmpeg Composition (5 parallel, VideoToolbox) | ~21m |
| **Total pipeline** | **~34 min** |

Bottleneck: ffmpeg raw-frame piping at 2000x1125 takes 62% of total time.

#### Phase 2: Add Avatar Overlay (Future Sprint)

```
Same pipeline + SadTalker/MuseTalk generates talking head from presenter image + audio →
  MoviePy composites avatar in corner over slide background → Final MP4
```

**Deferred components:**

| Component | Tool | Hardware Needed |
|-----------|------|-----------------|
| Talking head generation | SadTalker (single image + audio → video) | GPU (T4 minimum) |
| Higher quality lip sync | MuseTalk v1.5 (real-time, 30fps+) | V100 GPU |
| Full HeyGen replacement | HeyGem (Duix.Heygem, open-source) | GPU (Windows-focused) |

**Why deferred**: All avatar tools require GPU. Current Cloud Run deployment is CPU-only (2 vCPU). Avatar adds significant complexity for marginal MVP value. Phase 2 coincides with Kubernetes migration where GPU nodes are available.

---

### 2. Interactive Quiz Platform

**Problem**: No way to measure whether generated content actually teaches students anything. No data feedback loop. No engagement measurement.

**v0.3 Approach**: Build a quiz-based web application that tests comprehension of the generated content (PDF, PPT, video script), records student performance data, and feeds insights back to the content generation agent.

#### Architecture

```
Generated Content (PDF/PPT/Script) → [Quiz Generation Agent] → Quiz Questions →
  Student takes quiz → Performance data → Database →
    ├── Admin Dashboard (visualise performance)
    └── Feedback Loop → Agent analyses weak areas → Improves future content
```

#### Quiz Specifications

**Question Generation:**
- NEW agent: **Quiz Agent** — takes generated learning modules (markdown) as input, produces structured quiz questions (JSON)
- Question types: multiple choice (4 options), true/false, fill-in-the-blank
- Questions derived from: PDF content, PPT gap analysis, video script content
- Questions tagged by: topic, difficulty level (easy/medium/hard), Bloom's taxonomy level, source section
- Admin can add, remove, or edit questions post-generation
- Admin can set difficulty levels and customise feedback per question

**Quiz UX:**
- Web-based (React frontend, FastAPI backend)
- One attempt only — quiz cannot be retaken
- On completion: correct answers shown in green, incorrect in red
- Personalised feedback based on performance (e.g., "You struggled with industry context — review Section 4 of the learning guide")
- Timer optional (admin-configurable)

**Data Collection:**
- Per-question: student answer, correct/incorrect, time spent, difficulty level
- Per-quiz: total score, completion time, topic-level breakdown
- Per-student: cumulative performance across quizzes, trend over time
- Stored in: PostgreSQL (persistent, replaces ephemeral ChromaDB for quiz data)

**Admin Dashboard:**
- Visualise: class-level performance heatmap (which topics are students weakest on?)
- Visualise: individual student performance over time
- Visualise: question-level analytics (which questions have lowest correct rate?)
- Filter by: course, topic, difficulty level, date range
- Export: CSV/PDF reports

#### Tech Stack (Quiz Platform)

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | React + Tailwind CSS | Quiz interface + admin dashboard |
| Backend API | FastAPI | Quiz endpoints, auth, data API |
| Database | PostgreSQL | Student responses, quiz data, analytics |
| Quiz generation | GPT-5-mini | Generate questions from learning module content |
| Charting | Recharts or Chart.js | Admin dashboard visualisations |
| Auth | JWT (python-jose + passlib) | Student + admin authentication (see Section G.3) |

---

### 3. Content Improvement Feedback Loop

**Problem**: Content generation is currently open-loop — the agent generates content but never learns whether it was effective.

**v0.3 Approach**: Close the loop. Use quiz performance data to identify content weaknesses and feed them back into the generation pipeline.

#### Feedback Loop Architecture

```
Quiz Performance Data (PostgreSQL) →
  [Analytics Agent] analyses:
    - Which topics have lowest quiz scores?
    - Which gap analysis areas are students still failing on?
    - Which difficulty levels show unexpected failure rates?
  →
  [Generate Agent] receives feedback context:
    - "Students scored 45% on Industry Context for Topic 7 — expand this section"
    - "Students consistently miss questions about alternative technologies — add more examples"
  →
  Regenerated content with targeted improvements
```

#### Implementation

- `feedback_analyser.py` — NEW file. Queries PostgreSQL for quiz performance aggregates per topic/section. Produces structured feedback JSON:
  ```json
  {
    "topic": "Neural Network Optimisation",
    "weak_sections": ["Industry Context", "Key Takeaways"],
    "avg_score": 0.45,
    "recommendation": "Expand industry context with concrete company examples. Add more practice-oriented takeaways.",
    "question_failure_rate": {"q3": 0.72, "q7": 0.68}
  }
  ```
- `generate_agent.py` — modify to accept optional `feedback_context` parameter. When present, inject into GENERATE_MODULE prompt as additional guidance.
- Feedback is **per-topic, per-section** — not global. The agent improves specific weak areas without degrading strong ones.
- Eval framework (L1 + L2) validates that regenerated content scores equal or higher than original (regression prevention).

---

## Updated Tech Stack Summary

| Layer | Technology | Purpose | Status |
|-------|-----------|---------|--------|
| Pipeline orchestration | LangGraph | State machine for agent coordination | Working |
| LLM (extraction) | OpenAI GPT-5-nano | Summarisation, topic extraction | Working |
| LLM (analysis) | OpenAI GPT-5-mini | Gap analysis, quiz generation, module gen | Working |
| LLM (generation) | OpenAI GPT-5.1 | Critical module generation, video scripts | Working |
| Model routing | Severity-based (3-tier) | Nano/mini/premium with task-specific temps | Working |
| Vector store | ChromaDB | Semantic search over curriculum and research | Working |
| Embeddings | all-MiniLM-L6-v2 | Local, free, no API cost | Working |
| Web search | Tavily API | Industry trends and job requirements | Working |
| PDF extraction | PyMuPDF + python-pptx | Extract text from PDFs and slides | Working |
| **Slide image export** | **PyMuPDF + LibreOffice CLI** | **Export slides as PNG for video** | **NEW — Phase 1** |
| **TTS** | **Kokoro (82M, Apache 2.0)** | **Script → audio narration (CPU)** | **NEW — Phase 1** |
| **Video composition** | **MoviePy v2 + ffmpeg** | **Slides + audio → MP4** | **NEW — Phase 1** |
| Video (avatar, future) | SadTalker / MuseTalk | Talking head overlay (GPU) | Phase 2 |
| PDF generation | fpdf2 | Compile learning guide PDF | Working |
| PPT generation | python-pptx | Gap analysis PowerPoint | Working |
| **Quiz generation** | **GPT-5-mini** | **Generate quiz questions from content** | **NEW** |
| **Quiz frontend** | **React + Tailwind** | **Student quiz UI + admin dashboard** | **NEW** |
| **Quiz database** | **PostgreSQL** | **Student responses, analytics** | **NEW** |
| **Feedback analysis** | **feedback_analyser.py** | **Quiz data → content improvement signals** | **NEW** |
| Web framework | FastAPI + uvicorn | Async HTTP server | Working |
| Concurrency | ThreadPoolExecutor | Parallel agent execution (max_workers=8) | Working |
| Eval framework | DeepSeek-V3 + structural checks | Two-layer quality evaluation | Working |
| **Auth (quiz)** | **JWT (python-jose)** | **Student + admin auth for quiz system** | **NEW — v0.5** |
| Observability | LangSmith | Trace every LLM call + `@traceable` on services | Working → **Deep integration v0.4-v0.6** |
| **Structured logging** | **structlog** | **JSON logs, correlation IDs, no PII** | **NEW — v0.6** |
| **Admin charts** | **Recharts** | **Dashboard visualisations** | **NEW — v0.6** |
| **Mind maps** | **Mermaid.js + mermaid-py** | **Visual topic maps from module JSON** | **NEW — v0.7** |
| **Flashcard engine** | **supermemo2 (SM-2)** | **Spaced repetition scheduling** | **NEW — v0.7** |
| **RAG chat** | **ChromaDB + GPT-5-mini** | **Student Q&A on course content** | **NEW — v0.7** |
| **Student dashboard** | **React + Recharts** | **Progress visualisation** | **NEW — v0.7** |
| **SCORM export** | **Python zipfile + Jinja2** | **LMS-compatible course bundles** | **NEW — v0.7** |
| Deployment | Docker + GCP Cloud Run | Containerised, scales to zero | Working |

---

## Updated Strategic Roadmap

### Versioning
Commitizen semver. Major feature bumps: 0.4, 0.5, 0.6. Patches: 0.4.1, 0.4.2. All via `cz bump`.

### v0.4 — Kokoro TTS Video Pipeline (Current)
1. **Kokoro TTS parallel to HeyGen** — `VIDEO_PROVIDER=kokoro` adds local slides + voiceover pipeline. HeyGen code untouched.
2. **LangSmith foundations** — Fix missing API key, env var propagation, job metadata on traces.
3. **Security baseline** — SECURITY.md, LangSmith opt-in, temp file safety, subprocess hardening.
4. **Agentic compliance** — Fix stale files, evals README, CLAUDE.md skills, hook fixes.

### v0.5 — React Frontend + Quiz Platform
1. **Glassmorphism React SPA** — Frosted glass UI, dark mode, Tailwind, mobile-responsive. Replaces Jinja2 prototype.
2. **Quiz platform** — Quiz Agent (separate LangGraph workflow), Neon PostgreSQL, JWT auth, one-attempt quizzes.
3. **LangSmith enrichment** — `@traceable` on all services, Prompt Hub, Datasets integration.
4. **Security hardening** — CORS lockdown, security headers, env-configurable password, CI/CD with pip-audit.
5. **Infrastructure** — `.github/` setup, Dependabot, GitHub Actions.

### v0.6 — Admin Dashboard + Feedback Loop
1. **Admin dashboard** — Recharts analytics, topic heatmaps, question analytics, user management, quiz editor.
2. **Feedback loop** — Quiz data → content regeneration with eval regression prevention.
3. **LangSmith advanced** — Eval judge tracing, Annotation Queues, Online Evaluation, cost tracking.
4. **Observability** — Structured logging (structlog), audit logging, RBAC, data retention policy.
5. **Full deploy** — React + FastAPI + Neon PostgreSQL + Kokoro video on Cloud Run.

### v0.7 — Student Engagement & Competitive Features
1. **Mind map generation** — Mermaid.js mindmap from module JSON → SVG/PNG via `mermaid-py`. New LangGraph node.
2. **Flashcard engine** — SM-2 spaced repetition (`supermemo2` package), PostgreSQL scheduling tables, React review UI, Anki `.apkg` export.
3. **RAG chat endpoint** — ChromaDB retrieval + GPT-5-mini streaming response. FastAPI WebSocket + React chat UI.
4. **Student progress dashboard** — React + Recharts: topic mastery radar, flashcard progress, recommended study areas.
5. **SCORM course bundle export** — ZIP with `imsmanifest.xml`, self-contained HTML quiz, all generated content. LMS-ready.
6. **Competitive positioning** — Marketing materials, demo scripts, pilot comparison framework vs NoteGPT/GravityWrite.

### Phase 2 — Scale & Enrich (3-6 months post v0.7)
1. **Avatar overlay** — SadTalker/MuseTalk talking head (requires GPU/Kubernetes).
2. **LMS integration** — LTI 1.3 for Canvas, Moodle, Blackboard. Validate SCORM bundles across platforms.
3. **TTS upgrade** — Chatterbox or CosyVoice 3 on GPU.
4. **Expand eval datasets** — Engineering, business, health courses.

### Phase 3 — Adaptive Intelligence (6-12 months)
1. **PPO + DKVMN hybrid** — RL-based adaptive content selection from quiz data.
2. **Cold start** — ALEKS-style diagnostic (20-30 questions).
3. **Multi-agent expansion** — Assessment, Analytics, QA, Adaptation agents.
4. **Infrastructure** — Cloud Run → Kubernetes, ChromaDB → PostgreSQL + DynamoDB.

### Phase 4 — Production Scale (12-18+ months)
1. Multi-region Kubernetes, CDN for video (CloudFront)
2. Event streaming (Kafka), WCAG 2.1 AA
3. Published efficacy study, international expansion

### Detailed Implementation Plan
See: **`PM-Docs/v0.4-v0.6-detailed-plan.md`** — file-level specs, LangSmith integration matrix, security gap tracker, agentic guide compliance checklist.

---

## Key Dependencies & Risks (Updated)

**API Cost Structure** — Pipeline remains API-heavy for content generation. Video pipeline is now £0 cost (open-source). Quiz generation adds ~$0.01-0.02 per quiz via GPT-5-mini.

**Content Quality Ceiling** — Now addressable via feedback loop. Quiz data provides quantitative signal for which content sections need improvement.

**Video Quality** — Kokoro TTS is near-commercial quality but not as polished as ElevenLabs. Acceptable for MVP. Upgrade path to Chatterbox/CosyVoice exists for Phase 3.

**Quiz Data Cold Start** — Feedback loop requires sufficient quiz data (target: 100+ students per topic). Until then, content improvement relies on manual educator feedback and eval framework.

**PostgreSQL Migration** — Quiz platform requires persistent database. This is the first step away from ephemeral ChromaDB. Must plan migration carefully.

**Single-Job Constraint** — Still enforced. Scaling to concurrent users requires job queuing. Quiz platform is independent and can handle concurrent users from day one.

---

## Competitive Landscape & Positioning

### Why This Matters for Implementation

The following competitive context informs feature prioritisation for v0.5-v0.7. Two emerging tools — **NoteGPT** and **GravityWrite** — occupy adjacent spaces in AI-assisted education. Neither is a direct competitor, but both influence user expectations and procurement conversations.

### NoteGPT (Threat: Medium)

B2C AI study tool. Summarises YouTube/PDFs into notes, flashcards, mind maps, quizzes. Pricing: Free (15 quotas) → $19.92/mo unlimited. **What CR8 should adopt**: mind maps, flashcards with SM-2 spaced repetition, RAG chat. **What CR8 already beats**: curriculum grounding, institutional data ownership, feedback loop, B2B model, video generation.

### GravityWrite (Threat: Low)

Generic AI content mill with 250+ templates including education (curriculum designer, quiz generator). Template-based, not curriculum-aware. No assessment, no video, no feedback loop. **What CR8 should adopt**: nothing — GravityWrite's approach is fundamentally different. **Positioning**: demo-first sales showing the qualitative gap between template output and curriculum-grounded generation.

### CR8 Competitive Moat (5 Pillars)

1. **Curriculum-grounded generation** — ingests actual university PDFs/slides, not generic prompts
2. **Live industry research** — Tavily web search enriches content with current job market data
3. **Closed-loop improvement** — quiz data feeds back into generation (no competitor has this)
4. **Institutional data ownership** — student performance data belongs to the university
5. **B2B model** — sells to institutions (£10-50K/year contracts) not individual students ($7-20/mo)

### Features to Build (Competitive Response)

| Feature | Competitive Source | CR8 Advantage | Target Version |
|---------|-------------------|---------------|----------------|
| Mind maps (Mermaid.js) | NoteGPT | Curriculum-grounded, gap-analysis-enriched | v0.7 |
| Flashcards + SM-2 spaced repetition | NoteGPT | Quiz data seeds difficulty, Bloom's tagged | v0.7 |
| RAG chat (ask questions about content) | Gap in all competitors | ChromaDB already exists | v0.7 |
| Student progress dashboard | Gap in all competitors | Institutional + individual views | v0.7 |
| SCORM course bundle export | Gap in all competitors | Direct LMS import, procurement enabler | v0.7 |

See Section H (Coding Agent Guide) for full technical implementation specs.

---

## Immediate To-Do List (Ordered by Priority)

### v0.4 — Kokoro TTS Video Pipeline + LangSmith Foundations + Security

**Architecture**: HeyGen stays as-is. Kokoro added as `VIDEO_PROVIDER=kokoro` parallel provider.
**Versioning**: `cz bump --increment MINOR` → v0.4.0

#### Core Feature
- [x] **T-001**: Research notes — `kokoro-tts.md`, `moviepy-v2.md`, `pymupdf-slide-export.md` in `docs/research/`
- [x] **T-002**: Create `backend/services/script_parser.py` — parse `[SLIDE N]` markers → segment list
- [x] **T-003**: Create `backend/services/tts_engine.py` — Kokoro TTS wrapper (`synthesize()`, `synthesize_segments()`)
- [x] **T-004**: Add `export_slides_as_images()` to `file_parser.py` — PyMuPDF for PDF, LibreOffice CLI for PPTX
- [x] **T-005**: Modify `video_builder.py` — add `_build_kokoro_video()`, add `"kokoro"` branch in `build_videos()`, make `NotImplementedError` provider-conditional
- [x] **T-006**: Update `agent_generate.py` — pass Kokoro kwargs to both `build_videos()` call sites, call `export_slides_as_images()` when provider is kokoro
- [x] **T-007**: Update `state.py` (add `slide_images`), `config.py` (kokoro settings), `run_pipeline.py` (allow kokoro provider)
- [x] **T-008**: Update `pyproject.toml` (add kokoro, moviepy, soundfile), `.env.example`, `Dockerfile` (ffmpeg, espeak-ng, poppler-utils)
- [x] **T-009**: Update `ProgressCapture.STAGE_WEIGHTS` in `frontend/app.py`
- [x] **T-010**: Write tests — `test_script_parser.py`, `test_tts_engine.py` (mocked), update `test_video_builder.py` + `test_file_parser.py` + `test_progress_capture.py`
- [x] **T-011**: E2E test: `VIDEO_PROVIDER=kokoro python -m backend.run_pipeline --format pdf,ppt,script,video test.pdf`

#### LangSmith Foundations
- [x] **T-012**: Add `langchain_api_key` to `config.py`, apply LangSmith env vars at import time
- [x] **T-013**: Attach `job_id`, `output_formats`, `file_count` metadata to `pipeline.invoke()` in `run_pipeline.py`
- [x] **T-014**: Wrap new files (`tts_engine.py`, `script_parser.py`, `export_slides_as_images`) with `@traceable`

#### Security & Compliance
- [x] **T-015**: Create `SECURITY.md` at project root
- [x] **T-016**: Change `langchain_tracing_v2` default to `False` (opt-in, not opt-out)
- [x] **T-017**: Temp file cleanup — use `tempfile.TemporaryDirectory()` context managers in video pipeline
- [x] **T-018**: Subprocess safety — LibreOffice calls use `subprocess.run()` with explicit arg list, timeout
- [x] **T-019**: Path traversal prevention in `export_slides_as_images()`

#### Agentic Guide Fixes
- [x] **T-020**: Fix `feature_list.json` — `output_video_heygen` → `"scaffold"`, add `video_pipeline_kokoro`
- [x] **T-021**: Create `backend/evals/README.md`
- [x] **T-022**: Update CLAUDE.md Skills section — add `commit-ready`, `coverage-report`, `new-feature`
- [x] **T-023**: Fix PostToolUse hook — remove `|| true` so ruff failures surface

**Blocker**: Cloud Run memory must increase to 4 GiB before deploying Kokoro (peaks at 3.4 GB). Local dev works fine.

---

### v0.5 — Polished React Frontend + Interactive Quiz + Neon PostgreSQL

**Design**: Glassmorphism / frosted glass theme. Dark mode. WCAG 2.1 AA accessible.
**Database**: Neon free tier (serverless PostgreSQL, 512 MB free forever).
**Quiz Agent**: Separate LangGraph workflow (on-demand, reads completed pipeline state including `gap_summary`).
**Auth**: JWT (python-jose) for quiz system. Existing bcrypt session auth stays for content generation.
**Versioning**: `cz bump --increment MINOR` → v0.5.0

#### Foundation Work
- [ ] **T-024**: Write ADR-001 (LangGraph pipeline), ADR-002 (PostgreSQL/Neon), ADR-003 (React frontend)
- [ ] **T-025**: Research notes — `react-vite-fastapi.md`, `asyncpg-postgresql.md`, `python-jose-jwt.md`, `tailwindcss-glassmorphism.md`, `neon-serverless-postgres.md`

#### React Frontend
- [ ] **T-026**: Scaffold `frontend/react-app/` — Vite + React + Tailwind + React Router
- [ ] **T-027**: Build design system — GlassCard, DarkModeToggle components, CSS custom properties, Tailwind glassmorphism utilities
- [ ] **T-028**: Port UploadPage (drag-drop), ProgressPage (real-time), ResultsPage (downloads), LoginPage (frosted glass card)
- [ ] **T-029**: Build QuizPage (take quiz) + QuizResultsPage (red/green results, per-question feedback)
- [ ] **T-030**: Build React dev server proxy to FastAPI on :8080, production static build served by FastAPI

#### Quiz Backend
- [ ] **T-031**: Create `backend/pipeline/agent_quiz.py` — Quiz Agent LangGraph workflow (reads gap_summary + modules)
- [ ] **T-032**: Create `backend/prompts/quiz.py` — quiz generation prompt (30% easy / 50% medium / 20% hard)
- [ ] **T-033**: Create `backend/services/postgres_client.py` — async Neon client (asyncpg), CRUD for quizzes/attempts/responses
- [ ] **T-034**: Create `backend/db/schema.sql` + Alembic migrations (students, quizzes, questions, quiz_attempts, responses)
- [ ] **T-035**: Create `frontend/quiz_routes.py` — `/api/quiz/generate`, `/{id}`, `/{id}/submit`, `/{id}/results`
- [ ] **T-036**: Create `frontend/auth_routes.py` — JWT auth (`/api/auth/register`, `/api/auth/token`, `/api/auth/me`)

#### LangSmith Enrichment
- [ ] **T-037**: Add model tier + severity metadata to every `llm.invoke()` call in all 3 agents
- [ ] **T-038**: Wrap Tavily `search()`, ChromaDB `query()`, and all 3 agent nodes with `@traceable`
- [ ] **T-039**: Fix ThreadPoolExecutor context propagation (`get_current_run_tree`)
- [ ] **T-040**: Upload production prompts to LangSmith Prompt Hub

#### Security Hardening
- [ ] **T-041**: CORS lockdown — replace `allow_origins=["*"]` with configurable `ALLOWED_ORIGINS` whitelist
- [ ] **T-042**: Security headers middleware — CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy
- [ ] **T-043**: Replace hardcoded `CR8-AI` password with `AUTH_PASSWORD` env var
- [ ] **T-044**: JWT auth with HS256, configurable expiry, refresh tokens
- [ ] **T-045**: SQL injection prevention — asyncpg parameterized queries only
- [ ] **T-046**: Create `.github/` directory — copilot-instructions.md symlink, Dependabot, GitHub Actions CI (ruff + pytest + pip-audit)
- [ ] **T-047**: Rewrite negative instructions in CLAUDE.md → positive framing

#### Tests
- [ ] **T-048**: Backend tests — `test_quiz_agent.py`, `test_postgres_client.py`, `test_quiz_routes.py`, `test_auth_routes.py`
- [ ] **T-049**: React tests (Vitest) — QuestionCard, quiz submission flow, results display, dark mode toggle

---

### v0.6 — Admin Dashboard + Data Tracking + Feedback Loop

**Dashboard**: Recharts visualisations, glassmorphism stat cards.
**Feedback Loop**: Quiz data → `feedback_analyser.py` → `agent_generate.py` → eval regression check → conditional replace.
**Versioning**: `cz bump --increment MINOR` → v0.6.0

#### Foundation Work
- [ ] **T-050**: Write ADR-004 (Feedback loop), ADR-005 (Observability stack)
- [ ] **T-051**: Research notes — `recharts.md`, `structured-logging-python.md`, backfill `fpdf2.md`, `python-pptx.md`, `chromadb.md`

#### Admin Dashboard
- [ ] **T-052**: AdminOverview.jsx — stat cards (students, quizzes, avg scores, active jobs)
- [ ] **T-053**: TopicHeatmap.jsx — per-topic performance heatmap (Recharts)
- [ ] **T-054**: QuestionAnalytics.jsx — success rates, most-chosen wrong answers
- [ ] **T-055**: StudentTrends.jsx — score trends over time, cohort comparison
- [ ] **T-056**: QuizEditor.jsx — add/edit/delete questions, set difficulty, customise feedback
- [ ] **T-057**: UserManagement.jsx — view students, assign roles, deactivate accounts
- [ ] **T-058**: SystemHealth.jsx — pipeline job history, error rates, resource usage
- [ ] **T-059**: Create `frontend/admin_routes.py` — admin API endpoints

#### Feedback Loop
- [ ] **T-060**: Create `backend/services/feedback_analyser.py` — query PostgreSQL for per-topic aggregates (50+ completions, avg < 60% = weak)
- [ ] **T-061**: Create `backend/pipeline/regeneration.py` — analyse → regenerate → eval → conditional replace
- [ ] **T-062**: Modify `agent_generate.py` — accept optional `feedback_context` in `_generate_module()`
- [ ] **T-063**: Create `backend/prompts/feedback.py` — feedback injection template

#### LangSmith Advanced
- [ ] **T-064**: Wrap eval judge calls with `@traceable`, populate `langsmith_run_id` in `EvalResult`
- [ ] **T-065**: Submit eval scores as LangSmith feedback on original pipeline runs
- [ ] **T-066**: Configure Annotation Queues + Online Evaluation automations in LangSmith UI

#### Security & Observability
- [ ] **T-067**: RBAC — admin endpoints gated by JWT `role: "admin"` claim
- [ ] **T-068**: Audit logging — all admin actions logged to PostgreSQL `audit_log` table
- [ ] **T-069**: Structured logging — replace print/logging with `structlog` (JSON, no PII, correlation IDs)
- [ ] **T-070**: Data retention policy + GDPR-style `DELETE /api/admin/users/{id}/data`
- [ ] **T-071**: Add `make test` to Stop hook; add CodeQL/Bandit to CI
- [ ] **T-072**: Health check hardening — `/health` checks PostgreSQL, disk, memory (503 if degraded)

#### Tests & Deploy
- [ ] **T-073**: Tests — `test_feedback_analyser.py`, `test_regeneration.py`, `test_admin_routes.py`
- [ ] **T-074**: E2E integration test — upload → generate → quiz → dashboard → feedback → regeneration
- [ ] **T-075**: Full stack deploy — React + FastAPI + Neon PostgreSQL + Kokoro video on Cloud Run

---

### v0.7 — Student Engagement & Competitive Features

**Goal**: Add consumer-grade study features (mind maps, flashcards, RAG chat, student dashboard, SCORM export) with CR8's curriculum-grounding advantage. Competitive response to NoteGPT.
**Versioning**: `cz bump --increment MINOR` → v0.7.0

#### Mind Map Generation
- [ ] **T-080**: Research notes — `mermaid-mindmap.md`, `mermaid-py.md` in `docs/research/`
- [ ] **T-081**: Create `backend/services/mindmap_generator.py` — Convert module JSON (topics/subtopics) to Mermaid mindmap syntax → SVG/PNG via `mermaid-py`
- [ ] **T-082**: Add mindmap LangGraph node — runs after Generate Agent, produces mind map per module
- [ ] **T-083**: Add mind map React component — interactive SVG display with zoom/pan, download button
- [ ] **T-084**: Add `mermaid-py` to `pyproject.toml`, test server-side rendering
- [ ] **T-085**: Tests — `test_mindmap_generator.py` (JSON → Mermaid syntax, SVG output, edge cases)

#### Flashcard Engine (SM-2 Spaced Repetition)
- [ ] **T-086**: Research notes — `sm2-algorithm.md`, `supermemo2-package.md`, `anki-apkg-format.md`
- [ ] **T-087**: Create `backend/services/flashcard_generator.py` — Generate flashcards from module content via GPT-5-mini (front/back pairs, Bloom's tagged, source_section linked)
- [ ] **T-088**: Create `backend/services/sm2_scheduler.py` — Wrap `supermemo2` package, manage card scheduling (next_review_date, ease_factor, interval, repetitions)
- [ ] **T-089**: Alembic migration — `flashcards` table (id, module_topic, front_text, back_text, blooms_level, source_section, created_at) + `flashcard_reviews` table (id, student_id, flashcard_id, quality_rating, next_review_date, ease_factor, interval, repetitions, reviewed_at)
- [ ] **T-090**: Create `frontend/flashcard_routes.py` — `/api/flashcards/generate`, `/due`, `/{id}/review`, `/export/anki`
- [ ] **T-091**: React FlashcardReview.jsx — card flip animation, quality rating (0-5), due card queue
- [ ] **T-092**: Anki `.apkg` export — SQLite database + media files in ZIP
- [ ] **T-093**: Tests — `test_flashcard_generator.py`, `test_sm2_scheduler.py`, `test_flashcard_routes.py`

#### RAG Chat Endpoint
- [ ] **T-094**: Create `backend/services/rag_chat.py` — ChromaDB retrieval (top-k=5, filtered by module_topic) → GPT-5-mini with streaming response
- [ ] **T-095**: Create `frontend/chat_routes.py` — `/api/chat` POST endpoint (question, module_topic) → streaming JSON response
- [ ] **T-096**: React ChatPanel.jsx — message history, streaming response display, topic selector, citation highlights
- [ ] **T-097**: Add `@traceable` to RAG chat for LangSmith visibility
- [ ] **T-098**: Tests — `test_rag_chat.py` (retrieval filtering, response grounding, empty context handling)

#### Student Progress Dashboard
- [ ] **T-099**: Create React StudentDashboard.jsx — topic mastery radar chart (Recharts), quiz score trends, flashcard progress
- [ ] **T-100**: Create `frontend/student_routes.py` — `/api/student/progress`, `/api/student/recommendations`
- [ ] **T-101**: Recommendation engine — identify lowest-scoring quiz sections + overdue flashcards → prioritised study list
- [ ] **T-102**: Tests — `test_student_routes.py`, React component tests

#### SCORM Course Bundle Export
- [ ] **T-103**: Research notes — `scorm-package-spec.md`, `imsmanifest-template.md`
- [ ] **T-104**: Create `backend/services/scorm_bundler.py` — Assemble ZIP with `imsmanifest.xml`, all generated content (PDF, PPT, MP4, SVG mind map, flashcards JSON), self-contained HTML quiz with SCORM API wrapper
- [ ] **T-105**: Create `imsmanifest.xml` Jinja2 template — SCORM 1.2 metadata, SCO references, resource declarations
- [ ] **T-106**: Create self-contained `quiz.html` — embedded quiz (no server dependency), SCORM API communication (cmi.core.score.raw, cmi.core.lesson_status)
- [ ] **T-107**: Create `frontend/export_routes.py` — `/api/export/scorm/{job_id}` → ZIP download
- [ ] **T-108**: Validate SCORM package with SCORM Cloud test environment (Rustici)
- [ ] **T-109**: Tests — `test_scorm_bundler.py` (ZIP structure, manifest validity, quiz HTML rendering)

#### Integration & Deploy
- [ ] **T-110**: E2E test — upload → generate → mind map → flashcards → quiz → RAG chat → SCORM export
- [ ] **T-111**: Update `pyproject.toml` — add `mermaid-py`, `supermemo2`, update version
- [ ] **T-112**: Update Dockerfile — add Node.js for Mermaid CLI fallback (if `mermaid-py` needs Puppeteer)
- [ ] **T-113**: Full stack deploy — React + FastAPI + Neon PostgreSQL + all v0.7 features on Cloud Run

---

### Future (Phase 2+)

- [ ] **T-114**: Avatar overlay — SadTalker/MuseTalk talking head (requires GPU node)
- [ ] **T-115**: LTI 1.3 integration — Canvas, Moodle, Blackboard grade sync
- [ ] **T-116**: TTS upgrade — evaluate Chatterbox vs CosyVoice 3 on GPU
- [ ] **T-117**: PPO + DKVMN prototype — adaptive content selection from quiz data
- [ ] **T-118**: Collaborative annotation — students annotate generated content, annotations visible to cohort
- [ ] **T-119**: Multilingual content — CosyVoice 3 for non-English narration, GPT-5 for translation
- [ ] **T-120**: Chrome extension — summarise/annotate web content within CR8 ecosystem
- [ ] **T-121**: Video summarisation — students upload external videos, CR8 generates notes/flashcards

---

## Open Research Questions (Updated)

1. Does Kokoro TTS quality meet educator expectations for lecture-style narration? (Validate in Sprint 1)
2. What is the optimal number of quiz questions per learning module? (5? 10? 15?)
3. How many student quiz completions are needed before feedback loop produces meaningful improvement signals? (Hypothesis: 50-100 per topic)
4. Can quiz performance data serve as a proxy for DKVMN knowledge state initialisation? (Reduces cold start for Phase 3 RL)
5. What quiz completion rate can we expect without gamification? (Benchmark against MOOC quiz completion: ~20-40%)
6. How quickly does PPO policy converge in an educational domain?
7. What is the optimal reward function weighting (α, β, γ, δ) across different disciplines?
8. Does `mermaid-py` server-side rendering require Puppeteer/Chromium, or can it render SVG natively? (Impacts Docker image size and Cloud Run memory)
9. What is the optimal number of flashcards per learning module? (Hypothesis: 15-25, derived from key concepts)
10. Can quiz question failure rates be used to auto-generate targeted flashcards? (Cross-feature synergy: quiz → flashcard pipeline)
11. What is the optimal RAG chunk size and top-k for educational Q&A? (Hypothesis: 500-token chunks, top-k=5)
12. Which SCORM version should CR8 target — SCORM 1.2 (widest LMS support) or SCORM 2004 (richer data model)? (Hypothesis: SCORM 1.2 for MVP, 2004 for Phase 2)
13. How does NoteGPT's user retention curve compare to CR8's projected institutional retention? (Informs competitive positioning)

---

## CODING AGENT IMPLEMENTATION GUIDE

> **This section is written for the coding agent.** It describes exactly what already exists in the codebase, what needs to be built, and how to build it — file by file, function by function.

---

### SECTION A: WHAT ALREADY EXISTS (DO NOT REBUILD)

The following components are **complete, tested, and deployed**. The coding agent should import from and extend these — never rewrite them.

#### A.1 Pipeline Core (`src/agents/`)

| File | What It Does | Key Functions/Classes |
|------|-------------|----------------------|
| `ingest_agent.py` | Parses PDF/PPTX, extracts topics, embeds into ChromaDB `curriculum` collection | `run_ingest()`, `summarize_file()`, `extract_topics()` |
| `research_agent.py` | Tavily web search per topic, gap analysis via GPT-5-mini, stores in ChromaDB `research` collection | `run_research()`, `search_topic()`, `analyze_gaps()` |
| `generate_agent.py` | Generates learning modules (markdown) with severity-based model routing | `run_generate()`, `generate_module()`, `GENERATE_MODULE` prompt template |
| `script_agent.py` | Converts learning modules to spoken-word scripts with `[SLIDE N]` markers | `run_script()`, `generate_script()` |
| `video_agent.py` | **CURRENT: submits to HeyGen API** — TO BE REPLACED in Sprint 1 | `run_video()`, `build_video()` |

#### A.2 Infrastructure (`src/`)

| File | What It Does | Status |
|------|-------------|--------|
| `file_parser.py` | Extracts text from PDF (PyMuPDF) and PPTX (python-pptx) | Working — **EXTEND** with `export_slides_as_images()` |
| `chromadb_store.py` | ChromaDB wrapper for curriculum + research collections | Working — no changes needed |
| `progress_capture.py` | Captures stdout, parses stage prefixes, calculates weighted progress | Working — **EXTEND** with video/quiz stage weights |
| `config.py` | Pydantic settings, env loading | Working — **EXTEND** with new config vars |
| `prompts/` | Prompt templates for all agents (versioned) | Working — **ADD** quiz generation prompt |

#### A.3 Web Layer (`src/web/`)

| File | What It Does | Status |
|------|-------------|--------|
| `app.py` | FastAPI app, routes for upload/generate/download/progress | Working — **EXTEND** with quiz + video endpoints |
| `templates/index.html` | Single-page HTML frontend | Working — **REPLACE** with React SPA in Sprint 2 |
| `static/` | CSS, JS assets | Working — will be replaced by React build |

#### A.4 Output Generation (`src/output/`)

| File | What It Does | Status |
|------|-------------|--------|
| `pdf_builder.py` | fpdf2-based PDF generation from markdown modules | Working — no changes |
| `ppt_builder.py` | python-pptx PowerPoint generation with severity badges | Working — no changes |
| `video_builder.py` | **CURRENT: HeyGen API submission** | **REWRITE** — see Sprint 1 |

#### A.5 Quality (`src/eval/`)

| File | What It Does | Status |
|------|-------------|--------|
| `l1_checks.py` | 20+ structural validation checks | Working — **EXTEND** with quiz output checks |
| `l2_judge.py` | DeepSeek-V3 LLM judge with rubrics | Working — **ADD** QuizJudge rubric |
| `ab_compare.py` | Paired t-test A/B comparison | Working — no changes |

#### A.6 Tests (`tests/`)

144 tests passing. All new code MUST include tests. Follow existing patterns in `tests/test_*.py`.

#### A.7 Deployment

| File | What It Does | Status |
|------|-------------|--------|
| `Dockerfile` | Cloud Run container (Python, Gunicorn, Uvicorn) | Working — **EXTEND** with ffmpeg, LibreOffice, node |
| `cloudbuild.yaml` | GCP Cloud Build CI/CD | Working — **EXTEND** with new deps |
| `.env.example` | Environment variables template | Working — **EXTEND** with PostgreSQL vars |

---

### SECTION B: WHAT TO BUILD — SPRINT 1 (VIDEO PIPELINE)

**Goal:** Replace HeyGen API with open-source slides + voiceover pipeline. Output: MP4 file per topic module.

#### B.1 Extend `file_parser.py` — Add Slide Image Export

```python
# ADD to file_parser.py

def export_slides_as_images(file_path: str, output_dir: str) -> list[str]:
    """
    Export each slide/page from a PDF or PPTX as a PNG image.

    For PDF: Use PyMuPDF (fitz) to render each page at 150 DPI.
    For PPTX: Use LibreOffice CLI to convert PPTX → PDF, then render.

    Args:
        file_path: Path to PDF or PPTX file
        output_dir: Directory to save PNG files

    Returns:
        List of PNG file paths in slide order ["slide_001.png", "slide_002.png", ...]
    """
    # Implementation:
    # 1. Detect file type (.pdf vs .pptx)
    # 2. If PPTX: subprocess.run(["libreoffice", "--headless", "--convert-to", "pdf", file_path])
    # 3. Open PDF with fitz.open()
    # 4. For each page: page.get_pixmap(dpi=150) → save as PNG
    # 5. Return sorted list of PNG paths
```

**Key constraints:**
- Output PNGs at 150 DPI (produces ~1920×1080 for standard slides)
- Handle edge cases: slides with animations (render final state), landscape vs portrait
- LibreOffice must be installed in Docker container (`apt-get install -y libreoffice-core libreoffice-impress`)

#### B.2 Create `tts_engine.py` — Kokoro TTS Wrapper

> **CRITICAL DEPENDENCY**: Kokoro requires `espeak-ng` as a system dependency. Without it, KPipeline will fail silently or crash. Add `apt-get install -y espeak-ng` to the Dockerfile.

> **MEMORY WARNING**: Kokoro peaks at ~3.4 GB RAM during inference (benchmarked on M4 Pro). Current Cloud Run config is 2 GiB. **You MUST increase Cloud Run memory to 4 GiB** before deploying the video pipeline. See Section B.8 for the `gcloud` command.

```python
# NEW FILE: src/tts/tts_engine.py

import numpy as np
import soundfile as sf
from kokoro import KPipeline
from src.config import settings

SAMPLE_RATE = 24000  # Kokoro outputs 24kHz audio

class TTSEngine:
    """
    Wraps Kokoro TTS for script-to-audio conversion.

    Usage:
        engine = TTSEngine()
        audio_path, duration = engine.synthesize("Hello world", output_path="segment_01.wav")

    System dependencies:
        - espeak-ng (apt-get install -y espeak-ng)
        - pip install kokoro>=0.9.4 soundfile>=0.12

    Memory: ~3.4 GB peak during inference. Ensure container has >= 4 GiB RAM.
    """

    def __init__(self, voice: str = None, lang_code: str = None):
        """
        Initialize Kokoro TTS pipeline.

        Args:
            voice: Kokoro voice preset. Defaults to settings.TTS_VOICE ('af_heart').
                   Options: af_heart, af_sky (female US), am_adam, am_michael (male US),
                   bf_emma, bf_isabella (female British), bm_george, bm_lewis (male British)
            lang_code: Language code. Defaults to settings.TTS_LANG ('a').
                       'a' = American English, 'b' = British English,
                       'e' = Spanish, 'f' = French, 'j' = Japanese, 'z' = Mandarin
        """
        self.voice = voice or settings.TTS_VOICE  # default: 'af_heart'
        self.lang_code = lang_code or settings.TTS_LANG  # default: 'a'
        self.pipeline = KPipeline(lang_code=self.lang_code)

    def synthesize(self, text: str, output_path: str) -> tuple[str, float]:
        """
        Convert text to speech, save as WAV.

        Kokoro's pipeline() returns a generator that yields (gs, ps, audio) tuples:
          - gs: graphemes (input text chunk)
          - ps: phonemes (pronunciation)
          - audio: numpy array of audio samples

        For single segments, we concatenate all chunks into one WAV file.

        Returns:
            (output_path, duration_seconds)
        """
        audio_chunks = []
        generator = self.pipeline(text, voice=self.voice, speed=1, split_pattern=r'\n+')
        for gs, ps, audio in generator:
            audio_chunks.append(audio)

        if not audio_chunks:
            raise ValueError(f"Kokoro produced no audio for text: {text[:50]}...")

        full_audio = np.concatenate(audio_chunks)
        sf.write(output_path, full_audio, SAMPLE_RATE)
        duration = len(full_audio) / SAMPLE_RATE
        return (output_path, duration)

    def synthesize_segments(self, segments: list[dict], output_dir: str) -> list[dict]:
        """
        Process multiple script segments (one per slide).

        Input:  [{"slide_num": 1, "text": "Welcome to..."}, ...]
        Output: [{"slide_num": 1, "audio_path": "/tmp/.../seg_001.wav", "duration": 12.5}, ...]
        """
        results = []
        for segment in segments:
            output_path = f"{output_dir}/seg_{segment['slide_num']:03d}.wav"
            _, duration = self.synthesize(segment["text"], output_path)
            results.append({
                "slide_num": segment["slide_num"],
                "audio_path": output_path,
                "duration": duration,
            })
        return results
```

**Key constraints:**
- **System dependency**: `espeak-ng` MUST be installed (`apt-get install -y espeak-ng`) — Kokoro uses it via misaki G2P library
- **Memory**: 3.4 GB peak RAM. Cloud Run must be configured to 4 GiB (see B.8)
- `pip install kokoro>=0.9.4 soundfile>=0.12` in requirements.txt
- KPipeline generator yields `(graphemes, phonemes, audio_numpy)` tuples — concatenate audio chunks for full output
- Output: 24kHz WAV files (mono, float32)
- Kokoro handles sentence splitting internally via `split_pattern` parameter
- First call may be slower (~5-10s) due to model loading; subsequent calls are fast (~0.5-2s per sentence)

#### B.3 Script Parsing Utility (`src/utils/script_parser.py`)

The Script Agent already generates scripts with `[SLIDE N]` markers. This utility parses them into segments for the video builder.

```python
# NEW FILE: src/utils/script_parser.py

import re

def parse_script_segments(script_text: str) -> list[dict]:
    """
    Parse a script with [SLIDE N] markers into segments.

    Input example:
        "[SLIDE 1] Welcome to this module on neural networks.
         We'll cover the fundamentals of backpropagation.
         [SLIDE 2] Let's start with the forward pass..."

    Returns:
        [
            {"slide_num": 1, "text": "Welcome to this module on neural networks. We'll cover..."},
            {"slide_num": 2, "text": "Let's start with the forward pass..."},
        ]
    """
    pattern = r'\[SLIDE\s+(\d+)\]\s*'
    parts = re.split(pattern, script_text)

    # re.split with capture group returns: [before_first_match, group1, text1, group2, text2, ...]
    segments = []
    # Skip parts[0] (text before first [SLIDE N] marker, usually empty)
    for i in range(1, len(parts), 2):
        slide_num = int(parts[i])
        text = parts[i + 1].strip() if i + 1 < len(parts) else ""
        if text:
            segments.append({"slide_num": slide_num, "text": text})

    if not segments:
        raise ValueError("No [SLIDE N] markers found in script text")

    return segments
```

#### B.4 Rewrite `video_builder.py` — MoviePy Composition

```python
# REWRITE: src/output/video_builder.py

import tempfile
import os
from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
from src.tts.tts_engine import TTSEngine
from src.utils.script_parser import parse_script_segments
from src.config import settings

def build_narrated_slide_video(
    slide_images: list[str],      # Ordered PNG paths from file_parser
    script_text: str,              # Raw script with [SLIDE N] markers
    output_path: str,              # Final MP4 path
    transition_duration: float = None
) -> str:
    """
    Compose a narrated slide video from slide images + script.

    Pipeline:
    1. Parse script into segments by [SLIDE N] markers
    2. For each segment, generate audio via TTSEngine
    3. Create ImageClip from slide PNG, duration = audio duration + 0.5s padding
    4. Attach audio to clip
    5. Concatenate all clips with optional crossfade
    6. Write MP4 (H.264 + AAC, 1080p)

    Handles edge cases:
    - If script references slide N but only M slides exist (N > M): use last slide
    - If multiple script segments reference same slide: create separate clips
    - Cleans up temp audio files after composition
    """
    if transition_duration is None:
        transition_duration = settings.VIDEO_TRANSITION_DURATION  # default: 0.5

    segments = parse_script_segments(script_text)
    tts = TTSEngine()

    with tempfile.TemporaryDirectory() as temp_dir:
        # Step 1: Generate audio for each segment
        audio_results = tts.synthesize_segments(segments, output_dir=temp_dir)

        # Step 2: Build video clips
        clips = []
        for seg_info in audio_results:
            # Map slide_num to image (1-indexed), clamp to available slides
            slide_idx = min(seg_info["slide_num"] - 1, len(slide_images) - 1)
            slide_idx = max(0, slide_idx)  # safety: no negative index
            slide_img = slide_images[slide_idx]

            # Create image clip with duration matching audio + padding
            audio_clip = AudioFileClip(seg_info["audio_path"])
            clip = (
                ImageClip(slide_img)
                .with_duration(seg_info["duration"] + 0.5)  # 0.5s breathing room
                .with_audio(audio_clip)
            )
            clips.append(clip)

        # Step 3: Concatenate with crossfade transitions
        if transition_duration > 0 and len(clips) > 1:
            final = concatenate_videoclips(
                clips, method="compose", padding=-transition_duration
            )
        else:
            final = concatenate_videoclips(clips, method="compose")

        # Step 4: Write MP4
        final.write_videofile(
            output_path,
            fps=settings.VIDEO_FPS,        # default: 24
            codec="libx264",
            audio_codec="aac",
            logger=None,                    # suppress moviepy progress bar
        )

        # Cleanup: moviepy handles clip closing, tempdir auto-cleans audio files
        final.close()

    return output_path
```

**Key constraints:**
- Parse `[SLIDE N]` markers via `script_parser.py` (Section B.3)
- Handle mismatch: if script references more slides than exist, clamp to last slide
- MoviePy v2 API (not v1) — use `with_duration()` not `set_duration()`
- ffmpeg must be installed in Docker container (`apt-get install -y ffmpeg`)
- Use `tempfile.TemporaryDirectory()` for auto-cleanup of intermediate audio files
- `logger=None` on `write_videofile` prevents MoviePy progress bar polluting stdout/ProgressCapture

#### B.4b Update `app.py` — Video Download Endpoint

```python
# ADD to src/web/app.py

@app.get("/download/video/{job_id}")
async def download_video(job_id: str):
    """Serve generated MP4 for download or embedding."""
    video_path = f"/tmp/jobs/{job_id}/output/video.mp4"
    if not os.path.exists(video_path):
        raise HTTPException(404, "Video not found")
    return FileResponse(video_path, media_type="video/mp4", filename="lecture_video.mp4")
```

#### B.5 Update `Dockerfile`

```dockerfile
# ADD to Dockerfile (before pip install)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    espeak-ng \
    libreoffice-core \
    libreoffice-impress \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*
```

> **CRITICAL**: `espeak-ng` is required by Kokoro's misaki G2P library. Without it, KPipeline will fail at phoneme conversion. This is not listed in Kokoro's pip dependencies — it's a system-level dependency.

#### B.6 Update `requirements.txt`

```
# ADD — Sprint 1 (Video Pipeline)
kokoro>=0.9.4
moviepy>=2.0
soundfile>=0.12
Pillow>=10.0
numpy>=1.24

# ADD — Sprint 2 (Quiz Platform)
asyncpg>=0.29
python-jose[cryptography]>=3.3
passlib[bcrypt]>=1.7
alembic>=1.13
```

#### B.8 Update Cloud Run Configuration (BLOCKING)

> **CRITICAL**: Kokoro TTS peaks at ~3.4 GB RAM during inference. Current Cloud Run config is **2 GiB** — this will cause OOM kills. Must increase to 4 GiB before deploying video pipeline.

```bash
# Update Cloud Run service memory (run from project root)
gcloud run services update cr8 \
    --region=europe-west2 \
    --memory=4Gi \
    --cpu=2

# OR update in cloudbuild.yaml / Dockerfile deploy step:
# --memory 4Gi
```

**Why 4 GiB not 3.5 GiB**: Kokoro peak is ~3.4 GB, but the container also runs FastAPI + Uvicorn + ChromaDB + the actual pipeline processing. 4 GiB gives ~600 MB headroom for the rest of the application.

**Cost impact**: Minimal. Cloud Run charges per-request. Increasing memory allocation only affects cost when the service is actively processing requests (which it already does for ~60s+ per job). Idle cost remains ~£0.

**Alternative (if 4 GiB is too expensive for dev)**: Use Kokoro's ONNX optimised model (reduces memory ~30%) or process TTS segments one at a time with explicit `gc.collect()` between segments. However, 4 GiB is the recommended production configuration.

#### B.9 Tests for Sprint 1

Create `tests/test_video_pipeline.py`:
- `test_export_slides_pdf()` — PDF → PNGs, verify count matches page count
- `test_export_slides_pptx()` — PPTX → PNGs, verify via LibreOffice
- `test_tts_synthesize()` — text → WAV, verify duration > 0, file exists
- `test_tts_segments()` — multiple segments → multiple WAVs
- `test_build_video()` — slides + script → MP4, verify file exists, duration > 0
- `test_build_video_slide_mismatch()` — more slides referenced than exist, graceful fallback
- `test_script_parsing()` — `[SLIDE N]` marker extraction

---

### SECTION C: WHAT TO BUILD — SPRINT 2 (QUIZ PLATFORM)

**Goal:** Generate quizzes from learning modules. Students take quizzes. Admin views performance.

#### C.1 Create Quiz Agent (`src/agents/quiz_agent.py`)

```python
# NEW FILE: src/agents/quiz_agent.py

class QuizAgent:
    """
    LangGraph node that generates quiz questions from a learning module.

    Input: Learning module markdown (from generate_agent)
    Output: Structured quiz JSON
    """

    def generate_quiz(self, module_markdown: str, num_questions: int = 10) -> dict:
        """
        Generate quiz questions using GPT-5-mini.

        Prompt strategy:
        1. Provide full module markdown as context
        2. Request N questions at specified difficulty distribution (30% easy, 50% medium, 20% hard)
        3. Require Bloom's taxonomy tagging
        4. Require source_section linking back to module sections
        5. Require plausible distractors for MCQ
        6. Use JSON mode for structured output

        Returns: Quiz JSON (see schema in Loop Intelligence 0.3 §21.2)
        """
```

**Prompt template** — add to `src/prompts/quiz_prompt.py`:
```python
QUIZ_GENERATION_PROMPT = """
You are generating a comprehension quiz for a learning module.

MODULE CONTENT:
{module_markdown}

Generate {num_questions} quiz questions with the following requirements:
- Difficulty distribution: 30% easy (Remember/Understand), 50% medium (Apply/Analyse), 20% hard (Evaluate/Create)
- Question types: multiple choice (4 options each)
- Each question must reference a specific section of the module (source_section field)
- Distractors (wrong answers) must be plausible and address common misconceptions
- Provide feedback for both correct and incorrect answers
- Tag each question with Bloom's taxonomy level

Output as JSON matching this schema:
{quiz_schema}
"""
```

#### C.2 PostgreSQL Schema (`src/db/schema.sql`)

```sql
-- NEW FILE: src/db/schema.sql

CREATE TABLE students (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'student' CHECK (role IN ('student', 'admin')),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE quizzes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    module_topic VARCHAR(500) NOT NULL,
    job_id VARCHAR(255),  -- links to pipeline job
    config JSONB DEFAULT '{}',  -- timer, display_mode, etc.
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    quiz_id UUID REFERENCES quizzes(id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    options JSONB NOT NULL,  -- ["Option A", "Option B", "Option C", "Option D"]
    correct_answer VARCHAR(500) NOT NULL,
    difficulty VARCHAR(20) CHECK (difficulty IN ('easy', 'medium', 'hard')),
    blooms_level VARCHAR(20),
    source_section VARCHAR(500),
    feedback_correct TEXT,
    feedback_incorrect TEXT,
    sort_order INTEGER DEFAULT 0
);

CREATE TABLE quiz_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES students(id),
    quiz_id UUID REFERENCES quizzes(id),
    total_score DECIMAL(5,2),
    completion_time_seconds INTEGER,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    UNIQUE(student_id, quiz_id)  -- one attempt only
);

CREATE TABLE responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    attempt_id UUID REFERENCES quiz_attempts(id) ON DELETE CASCADE,
    question_id UUID REFERENCES questions(id),
    answer_given VARCHAR(500),
    is_correct BOOLEAN NOT NULL,
    time_spent_seconds INTEGER,
    submitted_at TIMESTAMP DEFAULT NOW()
);

-- Analytics views
CREATE MATERIALIZED VIEW topic_performance AS
SELECT q.module_topic, AVG(qa.total_score) as avg_score,
       COUNT(DISTINCT qa.student_id) as student_count
FROM quiz_attempts qa JOIN quizzes q ON qa.quiz_id = q.id
WHERE qa.completed_at IS NOT NULL
GROUP BY q.module_topic;

CREATE MATERIALIZED VIEW question_difficulty AS
SELECT qs.id, qs.question_text, qs.difficulty,
       COUNT(r.id) as total_responses,
       SUM(CASE WHEN r.is_correct THEN 1 ELSE 0 END)::DECIMAL / COUNT(r.id) as correct_rate
FROM questions qs JOIN responses r ON qs.id = r.question_id
GROUP BY qs.id, qs.question_text, qs.difficulty;
```

#### C.3 Database Client (`src/db/postgres_client.py`)

```python
# NEW FILE: src/db/postgres_client.py

import asyncpg
from pydantic_settings import BaseSettings

class DBConfig(BaseSettings):
    POSTGRES_URL: str = "postgresql://cr8:password@localhost:5432/cr8"

class PostgresClient:
    """Async PostgreSQL client for quiz data."""

    async def connect(self):
        self.pool = await asyncpg.create_pool(DBConfig().POSTGRES_URL)

    async def create_quiz(self, quiz_data: dict) -> str: ...
    async def get_quiz(self, quiz_id: str) -> dict: ...
    async def submit_attempt(self, attempt_data: dict) -> dict: ...
    async def get_results(self, attempt_id: str) -> dict: ...
    async def get_topic_performance(self) -> list[dict]: ...
    async def get_question_analytics(self, quiz_id: str) -> list[dict]: ...
    async def get_student_trend(self, student_id: str) -> list[dict]: ...
```

#### C.4 Quiz API Endpoints (`src/web/quiz_routes.py`)

```python
# NEW FILE: src/web/quiz_routes.py

from fastapi import APIRouter, Depends, HTTPException

router = APIRouter(prefix="/api/quiz")

@router.post("/generate")
async def generate_quiz(module_topic: str, job_id: str): ...
    # 1. Retrieve learning module markdown from job output
    # 2. Call QuizAgent.generate_quiz()
    # 3. Store in PostgreSQL
    # 4. Return quiz_id

@router.get("/{quiz_id}")
async def get_quiz(quiz_id: str): ...
    # Return quiz questions (without correct answers)

@router.post("/{quiz_id}/submit")
async def submit_quiz(quiz_id: str, answers: list[dict]): ...
    # 1. Check one-attempt constraint (UNIQUE on student_id + quiz_id)
    # 2. Grade each answer
    # 3. Store responses in PostgreSQL
    # 4. Return results with correct/incorrect + feedback

@router.get("/{quiz_id}/results/{attempt_id}")
async def get_results(quiz_id: str, attempt_id: str): ...
    # Return graded results: green (correct), red (incorrect), feedback per question

@router.get("/admin/dashboard")
async def admin_dashboard(): ...
    # Return aggregated analytics: topic performance, question difficulty, student trends
```

#### C.5 React Frontend Structure

```
src/frontend/          # NEW directory
├── package.json
├── src/
│   ├── App.jsx           # Router: /quiz, /admin, /generate
│   ├── pages/
│   │   ├── QuizPage.jsx      # Student quiz UI
│   │   ├── ResultsPage.jsx   # Green/red answers + feedback
│   │   ├── AdminDashboard.jsx # Charts + analytics
│   │   └── GeneratePage.jsx   # Content generation (replaces index.html)
│   ├── components/
│   │   ├── QuestionCard.jsx   # Single question display
│   │   ├── ScoreChart.jsx     # Recharts topic performance
│   │   ├── HeatMap.jsx        # Topic × student performance grid
│   │   └── ProgressBar.jsx    # Generation progress (replaces current)
│   └── api/
│       └── client.js          # Fetch wrapper for FastAPI endpoints
└── build/              # Static build served by FastAPI
```

**Key UX rules:**
- Quiz: one question per page or all at once (admin-configurable)
- Results: correct answers in `bg-green-100 border-green-500`, incorrect in `bg-red-100 border-red-500`
- Cannot go back after submitting
- No retakes (server-side enforcement via UNIQUE constraint)

#### C.6 Tests for Sprint 2

- `tests/test_quiz_agent.py` — quiz generation output validation (correct schema, difficulty distribution, source_section links)
- `tests/test_quiz_api.py` — all endpoints (generate, get, submit, results, dashboard)
- `tests/test_postgres.py` — CRUD operations, one-attempt constraint, analytics views
- `tests/test_quiz_frontend.py` — component rendering (if using testing-library)

---

### SECTION D: WHAT TO BUILD — SPRINT 3 (FEEDBACK LOOP)

#### D.1 Create `feedback_analyser.py`

```python
# NEW FILE: src/feedback/feedback_analyser.py

class FeedbackAnalyser:
    """
    Analyses quiz performance data to generate content improvement signals.

    Queries PostgreSQL for:
    - Per-topic average scores
    - Per-section question correct rates
    - Common wrong answer patterns

    Produces structured feedback JSON for the Generate Agent.
    """

    async def analyse_topic(self, module_topic: str) -> dict | None:
        """
        Generate feedback for a topic if sufficient data exists.

        Returns None if < 50 quiz completions (insufficient data).
        Returns feedback JSON if weak sections detected (avg score < 0.60).
        """
        # 1. Query topic_performance materialized view
        # 2. If student_count < 50: return None
        # 3. Query question_difficulty for this topic's quiz
        # 4. Identify questions with correct_rate < 0.50
        # 5. Map failed questions back to source_section
        # 6. Analyse common wrong answers (mode of answer_given WHERE is_correct = FALSE)
        # 7. Generate recommendation text via GPT-5-mini
        # 8. Return structured feedback JSON
```

#### D.2 Modify `generate_agent.py`

```python
# MODIFY: src/agents/generate_agent.py

def generate_module(self, topic: dict, feedback_context: dict | None = None) -> str:
    """
    Generate learning module. If feedback_context is provided, inject into prompt.
    """
    prompt = GENERATE_MODULE.format(topic=topic)

    if feedback_context:
        feedback_section = f"""
[FEEDBACK FROM STUDENT PERFORMANCE DATA]
Previous students scored an average of {feedback_context['overall_score']*100:.0f}% on this topic.
Weak sections: {', '.join(s['section'] for s in feedback_context['weak_sections'])}
Common misconceptions: {'; '.join(feedback_context.get('misconceptions_detected', []))}
Recommendations: {'; '.join(s['recommendation'] for s in feedback_context['weak_sections'])}
[END FEEDBACK]

Pay particular attention to the weak areas identified above when generating this module.
"""
        prompt = feedback_section + prompt

    # ... rest of existing generation logic
```

#### D.3 Regeneration Pipeline

```python
# NEW FILE: src/feedback/regeneration_pipeline.py

async def regenerate_with_feedback(job_id: str, module_topic: str):
    """
    Full regeneration cycle:
    1. Analyse quiz data → feedback JSON
    2. Regenerate module with feedback context
    3. Run eval (L1 + L2) on new module
    4. Compare scores with original (regression check)
    5. If improved or equal: replace original
    6. If regressed: flag for human review, keep original
    """
```

---

### SECTION E: CONFIGURATION & ENVIRONMENT

Add to `.env.example`:

```bash
# PostgreSQL (NEW)
POSTGRES_URL=postgresql://cr8:password@localhost:5432/cr8

# TTS (NEW)
TTS_VOICE=af_heart    # Kokoro voice preset
TTS_LANG=a            # 'a' = American English, 'b' = British English

# Video (NEW — replaces HEYGEN_API_KEY)
VIDEO_FPS=24
VIDEO_TRANSITION_DURATION=0.5
SLIDE_EXPORT_DPI=150

# Quiz (NEW)
QUIZ_DEFAULT_NUM_QUESTIONS=10
QUIZ_DIFFICULTY_DISTRIBUTION=0.3,0.5,0.2  # easy,medium,hard
FEEDBACK_MIN_COMPLETIONS=50
FEEDBACK_WEAK_THRESHOLD=0.60
```

---

### SECTION F: DEPENDENCY GRAPH

```
Sprint 1 (no dependencies, can start immediately):
  T-005 (requirements) + T-006 (Dockerfile + espeak-ng) + T-006b (Cloud Run 4GiB) — do FIRST
  T-001 (slide export) ──┐
  T-005b (script parser) ├→ T-003 (video builder) → T-007 (integration test)
  T-002 (TTS engine) ────┘
  T-004 (download endpoint) — independent
  T-008 (progress capture) — independent

Sprint 2 (depends on Sprint 1 completion for full integration):
  T-010 (PostgreSQL + Alembic) → T-011 (quiz API) → T-015 (tests)
  T-009 (Quiz Agent) → T-011 (quiz API)
  T-014 (JWT auth) → T-014b (CORS) → T-014d (React build + FastAPI serving)
  T-012 (React quiz frontend) → T-013 (admin dashboard)
  T-014c (Alembic setup) — independent, do early

Sprint 3 (depends on Sprint 2 + quiz data accumulation):
  T-016 (feedback analyser) → T-017 (generate agent modification)
  T-018 (admin customisation) — independent
  T-019 (video embed) — independent
  T-020 (deploy) → T-021 (e2e test)
```

---

### SECTION G: INFRASTRUCTURE IMPLEMENTATION DETAILS

> **This section covers cross-cutting infrastructure that the coding agent needs for Sprints 1-3.** These are not standalone to-dos but implementation patterns required across multiple sprints.

#### G.1 LangGraph State Schema Modification

The existing LangGraph state machine must be extended to include new pipeline nodes (Video, Quiz). Here's the state schema change:

```python
# MODIFY: src/pipeline/state.py (or wherever the LangGraph state is defined)

from typing import TypedDict, Optional

class PipelineState(TypedDict):
    # EXISTING fields (do not modify)
    file_path: str
    topics: list[dict]
    curriculum_scope: str
    research_results: list[dict]
    modules: list[dict]           # generated markdown modules
    pdf_path: Optional[str]
    ppt_path: Optional[str]
    script_text: Optional[str]

    # NEW fields for v0.3
    slide_images: Optional[list[str]]     # PNG paths from export_slides_as_images()
    video_path: Optional[str]             # final MP4 path
    quiz_data: Optional[list[dict]]       # quiz JSON from Quiz Agent
    feedback_context: Optional[dict]      # from FeedbackAnalyser (Sprint 3)
```

**New LangGraph nodes to add:**

```python
# MODIFY: src/pipeline/graph.py (or wherever the LangGraph graph is built)

from langgraph.graph import StateGraph

graph = StateGraph(PipelineState)

# Existing nodes
graph.add_node("ingest", run_ingest)
graph.add_node("research", run_research)
graph.add_node("generate", run_generate)
graph.add_node("script", run_script)

# NEW nodes
graph.add_node("export_slides", run_export_slides)   # Sprint 1: T-001
graph.add_node("video", run_video)                    # Sprint 1: T-003 (rewritten)
graph.add_node("quiz", run_quiz)                      # Sprint 2: T-009

# Updated edges — video and quiz are optional (controlled by format selection UI)
graph.add_edge("ingest", "research")
graph.add_edge("research", "generate")
graph.add_edge("generate", "script")
graph.add_edge("script", "export_slides")
graph.add_edge("export_slides", "video")
# Quiz runs independently after generate (does not depend on video):
graph.add_edge("generate", "quiz")
```

#### G.2 React Build + FastAPI Static Serving

In Sprint 2, the React SPA replaces `templates/index.html`. The build output is served by FastAPI as static files.

```python
# MODIFY: src/web/app.py

import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="CR8 Learning Platform")

# --- CORS middleware (MUST be added before routes) ---
# During development, React dev server runs on :3000, FastAPI on :8000
# In production, same-origin (React build served by FastAPI) — CORS not needed
# but kept for flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",      # React dev server
        "http://localhost:8000",      # FastAPI dev
        os.getenv("FRONTEND_URL", ""),  # Production URL
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API routes (must come BEFORE static mount) ---
from src.web.quiz_routes import router as quiz_router
app.include_router(quiz_router)
# ... existing routes for /upload, /generate, /download, /progress ...

# --- Serve React build (MUST be last — catches all unmatched routes) ---
REACT_BUILD_DIR = os.path.join(os.path.dirname(__file__), "../../frontend/build")
if os.path.exists(REACT_BUILD_DIR):
    # Serve static assets (JS, CSS, images)
    app.mount("/static", StaticFiles(directory=f"{REACT_BUILD_DIR}/static"), name="static")

    # Catch-all: serve index.html for React Router (SPA client-side routing)
    @app.get("/{full_path:path}")
    async def serve_react(full_path: str):
        """Serve React SPA — all non-API routes return index.html."""
        index_path = os.path.join(REACT_BUILD_DIR, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"error": "Frontend not built. Run: cd frontend && npm run build"}
```

**Build process** (add to CI/CD or Dockerfile):
```dockerfile
# ADD to Dockerfile — React build stage
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# In final stage, copy build output:
COPY --from=frontend-build /app/frontend/build /app/frontend/build
```

#### G.3 JWT Authentication Implementation

```python
# NEW FILE: src/web/auth.py

from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from src.config import settings

# --- Config ---
SECRET_KEY = settings.JWT_SECRET_KEY  # add to .env: JWT_SECRET_KEY=<random-64-char-hex>
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# --- Password hashing ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# --- OAuth2 scheme ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# --- Models ---
class TokenData(BaseModel):
    sub: str          # student/admin email
    role: str         # "student" or "admin"
    exp: datetime

class User(BaseModel):
    email: str
    name: str
    role: str         # "student" or "admin"

# --- Token creation ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# --- Token verification (FastAPI dependency) ---
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        role: str = payload.get("role")
        if email is None:
            raise credentials_exception
        return User(email=email, name=payload.get("name", ""), role=role)
    except JWTError:
        raise credentials_exception

# --- Role-based access ---
def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

def require_student(user: User = Depends(get_current_user)) -> User:
    if user.role not in ("student", "admin"):  # admin can also access student routes
        raise HTTPException(status_code=403, detail="Student access required")
    return user
```

**Auth API endpoints** — add to `src/web/auth_routes.py`:
```python
# NEW FILE: src/web/auth_routes.py

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from src.web.auth import pwd_context, create_access_token, User
from src.db.postgres_client import PostgresClient

router = APIRouter(prefix="/api/auth")

@router.post("/register")
async def register(email: str, name: str, password: str, db: PostgresClient = Depends()):
    """Register a new student account."""
    hashed = pwd_context.hash(password)
    # Store in PostgreSQL students table (add password_hash column)
    await db.create_student(email=email, name=name, password_hash=hashed)
    return {"message": "Registered successfully"}

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: PostgresClient = Depends()):
    """Login and receive JWT token."""
    user = await db.get_user_by_email(form_data.username)
    if not user or not pwd_context.verify(form_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    token = create_access_token(data={"sub": user["email"], "name": user["name"], "role": user["role"]})
    return {"access_token": token, "token_type": "bearer"}
```

**Dependencies to add**: `pip install python-jose[cryptography] passlib[bcrypt]`

#### G.4 Database Migration Strategy (Alembic)

Use Alembic for PostgreSQL schema migrations. This is critical for Sprint 2+ when the schema will evolve (e.g., adding `password_hash` to students, new tables for admin features).

```bash
# Setup (one-time)
pip install alembic asyncpg
cd src/db
alembic init migrations

# Edit alembic.ini:
# sqlalchemy.url = postgresql+asyncpg://cr8:password@localhost:5432/cr8

# Create initial migration from schema.sql:
alembic revision --autogenerate -m "initial schema — students, quizzes, questions, attempts, responses"

# Apply migrations:
alembic upgrade head
```

**Convention**: Every schema change goes through Alembic. Never modify the database directly. Migration files live in `src/db/migrations/versions/`.

**For initial setup (Sprint 2 start)**: Run `schema.sql` directly for the first deployment, then initialise Alembic with `alembic stamp head` to mark the current state as the baseline.

#### G.5 Error Handling Patterns

Consistent error handling across new components:

```python
# NEW FILE: src/utils/errors.py

class CR8Error(Exception):
    """Base error for all CR8 pipeline errors."""
    pass

class TTSError(CR8Error):
    """Kokoro TTS failed to generate audio."""
    pass

class VideoCompositionError(CR8Error):
    """MoviePy/ffmpeg failed to compose video."""
    pass

class QuizGenerationError(CR8Error):
    """Quiz Agent failed to produce valid quiz JSON."""
    pass

class SlideExportError(CR8Error):
    """PyMuPDF/LibreOffice failed to export slide images."""
    pass

class FeedbackAnalysisError(CR8Error):
    """Feedback analyser failed (insufficient data, DB error, etc.)."""
    pass
```

**Usage pattern in pipeline nodes:**

```python
# In video_builder.py
from src.utils.errors import TTSError, VideoCompositionError

def build_narrated_slide_video(...):
    try:
        audio_results = tts.synthesize_segments(segments, output_dir=temp_dir)
    except Exception as e:
        raise TTSError(f"TTS synthesis failed for job: {e}") from e

    try:
        final.write_videofile(output_path, ...)
    except Exception as e:
        raise VideoCompositionError(f"MoviePy composition failed: {e}") from e
```

**In LangGraph nodes**: Catch `CR8Error` subclasses and store error state in `PipelineState` rather than crashing the entire pipeline. This allows partial output (e.g., PDF + PPT succeed but video fails — still deliver the PDF/PPT).

#### G.6 Temp File Cleanup Strategy

All pipeline stages that generate intermediate files must use `tempfile.TemporaryDirectory()` for automatic cleanup:

```python
import tempfile

# Pattern for any stage that creates intermediate files:
with tempfile.TemporaryDirectory(prefix="cr8_video_") as temp_dir:
    # All intermediate files go in temp_dir
    slide_pngs = export_slides_as_images(file_path, output_dir=temp_dir)
    audio_files = tts.synthesize_segments(segments, output_dir=temp_dir)
    # Final output goes to persistent job directory
    build_narrated_slide_video(..., output_path=f"/tmp/jobs/{job_id}/output/video.mp4")
# temp_dir automatically cleaned up on exit (even on exception)
```

**Job output directory**: `/tmp/jobs/{job_id}/output/` persists until the job is complete and files are downloaded. Add a cleanup cron or TTL-based deletion (e.g., delete jobs older than 24 hours).

#### G.7 Updated Environment Variables

Add to `.env.example` and `src/config.py`:

```bash
# ADD to .env.example (supplements Section E)

# JWT Auth (NEW — Sprint 2)
JWT_SECRET_KEY=<generate-with: python -c "import secrets; print(secrets.token_hex(32))">
JWT_ALGORITHM=HS256
JWT_EXPIRY_HOURS=24

# CORS (NEW — development only)
FRONTEND_URL=http://localhost:3000

# Database migrations
DATABASE_URL=postgresql+asyncpg://cr8:password@localhost:5432/cr8
```

```python
# MODIFY: src/config.py — add to existing Settings class

class Settings(BaseSettings):
    # ... existing fields ...

    # JWT (Sprint 2)
    JWT_SECRET_KEY: str = "dev-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 24

    # CORS
    FRONTEND_URL: str = "http://localhost:3000"

    # TTS (Sprint 1) — already in Section E
    TTS_VOICE: str = "af_heart"
    TTS_LANG: str = "a"

    # Video (Sprint 1) — already in Section E
    VIDEO_FPS: int = 24
    VIDEO_TRANSITION_DURATION: float = 0.5
    SLIDE_EXPORT_DPI: int = 150

    # Quiz (Sprint 2) — already in Section E
    QUIZ_DEFAULT_NUM_QUESTIONS: int = 10
    QUIZ_DIFFICULTY_DISTRIBUTION: str = "0.3,0.5,0.2"
    FEEDBACK_MIN_COMPLETIONS: int = 50
    FEEDBACK_WEAK_THRESHOLD: float = 0.60

    # Mind Maps (v0.7)
    MINDMAP_OUTPUT_FORMAT: str = "svg"  # "svg" or "png"
    MINDMAP_MAX_DEPTH: int = 4          # max hierarchy levels in mind map

    # Flashcards (v0.7)
    FLASHCARD_DEFAULT_COUNT: int = 20
    FLASHCARD_SM2_INITIAL_EASE: float = 2.5
    FLASHCARD_SM2_MIN_EASE: float = 1.3

    # RAG Chat (v0.7)
    RAG_TOP_K: int = 5
    RAG_CHUNK_SIZE: int = 500          # tokens
    RAG_MODEL: str = "gpt-5-mini"

    # SCORM (v0.7)
    SCORM_VERSION: str = "1.2"          # "1.2" or "2004"
```

---

### SECTION H: WHAT TO BUILD — v0.7 (STUDENT ENGAGEMENT & COMPETITIVE FEATURES)

> **Goal:** Add consumer-grade study features that match NoteGPT's best offerings while maintaining CR8's curriculum-grounding advantage. Five features: mind maps, flashcards (SM-2), RAG chat, student dashboard, SCORM export.

---

#### H.1 Mind Map Generator (`backend/services/mindmap_generator.py`)

**What it does:** Converts the structured topic/subtopic JSON from the Generate Agent into a visual mind map using Mermaid.js mindmap syntax, rendered to SVG/PNG via the `mermaid-py` package.

**Input:** Module JSON from Generate Agent (already contains hierarchical topic → subtopic → key concept structure).

**Output:** SVG or PNG file of the mind map.

```python
# NEW FILE: backend/services/mindmap_generator.py

import mermaid as md
from mermaid.graph import Graph
from src.config import settings

class MindMapGenerator:
    """
    Generates visual mind maps from learning module content.

    Uses Mermaid.js mindmap syntax rendered server-side via mermaid-py.
    No browser/Puppeteer needed — mermaid-py uses the Mermaid CLI (mmdc).

    Dependencies:
        pip install mermaid-py
        # mermaid-py requires Node.js + @mermaid-js/mermaid-cli (npx mmdc)
        # Add to Dockerfile: RUN npm install -g @mermaid-js/mermaid-cli
    """

    def generate_mindmap_syntax(self, module_data: dict) -> str:
        """
        Convert module JSON to Mermaid mindmap syntax.

        Input example:
        {
            "topic": "Neural Network Optimisation",
            "subtopics": [
                {
                    "name": "Gradient Descent",
                    "concepts": ["Batch GD", "Stochastic GD", "Mini-Batch SGD"]
                },
                {
                    "name": "Regularisation",
                    "concepts": ["L1 (Lasso)", "L2 (Ridge)", "Dropout"]
                }
            ]
        }

        Output:
        mindmap
          root((Neural Network Optimisation))
            Gradient Descent
              Batch GD
              Stochastic GD
              Mini-Batch SGD
            Regularisation
              L1 Lasso
              L2 Ridge
              Dropout
        """
        lines = ["mindmap"]
        # Root node — double parentheses for rounded shape
        topic_clean = module_data["topic"].replace("(", "").replace(")", "")
        lines.append(f"  root(({topic_clean}))")

        for subtopic in module_data.get("subtopics", []):
            sub_clean = subtopic["name"].replace("(", "").replace(")", "")
            lines.append(f"    {sub_clean}")
            for concept in subtopic.get("concepts", []):
                concept_clean = concept.replace("(", "").replace(")", "")
                lines.append(f"      {concept_clean}")

        return "\n".join(lines)

    def render_to_file(self, module_data: dict, output_path: str) -> str:
        """
        Generate mind map and render to SVG/PNG.

        Args:
            module_data: Structured module JSON with topic/subtopics/concepts
            output_path: Output file path (e.g., "mindmap.svg" or "mindmap.png")

        Returns:
            Path to rendered file
        """
        syntax = self.generate_mindmap_syntax(module_data)
        graph = Graph("mindmap", syntax)
        rendered = md.Mermaid(graph)
        rendered.to_svg(output_path) if output_path.endswith(".svg") else rendered.to_png(output_path)
        return output_path

    def generate_from_modules(self, modules: list[dict], output_dir: str) -> list[str]:
        """
        Generate mind maps for all modules in a pipeline run.

        Returns: List of file paths to rendered mind maps.
        """
        paths = []
        for i, module in enumerate(modules):
            ext = settings.MINDMAP_OUTPUT_FORMAT
            path = f"{output_dir}/mindmap_{i+1:03d}.{ext}"
            self.render_to_file(module, path)
            paths.append(path)
        return paths
```

**Key constraints:**
- `mermaid-py` requires Node.js + `@mermaid-js/mermaid-cli` installed globally (`npm install -g @mermaid-js/mermaid-cli`)
- Add to Dockerfile: `RUN npm install -g @mermaid-js/mermaid-cli`
- Mermaid mindmap syntax uses indentation for hierarchy (2 spaces per level)
- Special characters in node text (parentheses, brackets) must be stripped or escaped
- SVG output is preferred (smaller, scalable, embeddable in React); PNG as fallback
- Maximum depth: 4 levels (root → topic → subtopic → concept) to avoid cluttered diagrams

**LangGraph integration:**
```python
# Add new node to graph.py
graph.add_node("mindmap", run_mindmap)
graph.add_edge("generate", "mindmap")  # runs after content generation
```

---

#### H.2 Flashcard Engine with SM-2 Spaced Repetition

**What it does:** Generates flashcards from learning module content, schedules reviews using the SM-2 algorithm, and provides a React UI for card review with quality rating.

##### H.2a Flashcard Generator (`backend/services/flashcard_generator.py`)

```python
# NEW FILE: backend/services/flashcard_generator.py

from src.config import settings

FLASHCARD_PROMPT = """
You are generating flashcards for a learning module.

MODULE CONTENT:
{module_markdown}

Generate {num_cards} flashcards with these requirements:
- Each card has a FRONT (question/prompt) and BACK (answer/explanation)
- Cards should test key concepts, definitions, applications, and relationships
- Tag each card with Bloom's taxonomy level (remember, understand, apply, analyse)
- Link each card to a specific section of the module (source_section)
- Mix card types: definition, concept application, comparison, cause-effect
- Difficulty distribution: 30% easy (remember), 50% medium (understand/apply), 20% hard (analyse)

Output as JSON:
{{
    "cards": [
        {{
            "front": "What is the purpose of batch normalisation?",
            "back": "Batch normalisation stabilises training by normalising inputs to each layer, reducing internal covariate shift and enabling higher learning rates.",
            "blooms_level": "understand",
            "source_section": "Core Content > Optimisation Techniques",
            "difficulty": "medium"
        }}
    ]
}}
"""

class FlashcardGenerator:
    """
    Generates flashcards from learning modules using GPT-5-mini.
    Cards are structured for SM-2 spaced repetition scheduling.
    """

    def generate(self, module_markdown: str, num_cards: int = None) -> list[dict]:
        """
        Generate flashcards from module content.

        Returns: List of flashcard dicts with front, back, blooms_level,
                 source_section, difficulty fields.
        """
        num_cards = num_cards or settings.FLASHCARD_DEFAULT_COUNT
        # Call GPT-5-mini with FLASHCARD_PROMPT
        # Parse JSON response
        # Validate card structure
        # Return list of card dicts
```

##### H.2b SM-2 Scheduler (`backend/services/sm2_scheduler.py`)

```python
# NEW FILE: backend/services/sm2_scheduler.py

from supermemo2 import SMTwo
from datetime import datetime, timedelta
from src.config import settings

class SM2Scheduler:
    """
    Wraps the supermemo2 package for flashcard scheduling.

    SM-2 Algorithm:
    - Quality rating: 0-5 (0=complete blackout, 5=perfect recall)
    - Quality >= 3: successful recall → increase interval
    - Quality < 3: failed recall → reset to interval=1
    - Ease factor starts at 2.5, adjusts with each review
    - Minimum ease factor: 1.3

    Usage:
        scheduler = SM2Scheduler()
        result = scheduler.review(quality=4, repetitions=3, ease_factor=2.5, interval=10)
        # result: {"repetitions": 4, "ease_factor": 2.6, "interval": 26, "next_review": "2026-03-29"}
    """

    def review(self, quality: int, repetitions: int = 0,
               ease_factor: float = None, interval: int = 0) -> dict:
        """
        Process a single flashcard review.

        Args:
            quality: Student's self-rated recall quality (0-5)
            repetitions: Number of consecutive successful reviews
            ease_factor: Current ease factor (default: FLASHCARD_SM2_INITIAL_EASE)
            interval: Current interval in days

        Returns:
            Dict with updated repetitions, ease_factor, interval, next_review_date
        """
        ease_factor = ease_factor or settings.FLASHCARD_SM2_INITIAL_EASE
        review = SMTwo(quality, repetitions, ease_factor, interval)
        # Or use the functional API:
        # review = SMTwo.first_review(quality) for first review
        # review = SMTwo(quality, repetitions, ease_factor, interval) for subsequent

        return {
            "repetitions": review.repetitions,
            "ease_factor": max(review.easiness, settings.FLASHCARD_SM2_MIN_EASE),
            "interval": review.interval,
            "next_review_date": (datetime.now() + timedelta(days=review.interval)).isoformat(),
        }

    def get_due_cards(self, student_id: str, limit: int = 20) -> list[dict]:
        """
        Query PostgreSQL for flashcards due for review.

        SELECT f.*, fr.ease_factor, fr.interval, fr.repetitions
        FROM flashcards f
        JOIN flashcard_reviews fr ON f.id = fr.flashcard_id
        WHERE fr.student_id = :student_id
          AND fr.next_review_date <= NOW()
        ORDER BY fr.next_review_date ASC
        LIMIT :limit
        """
        # Implementation queries PostgreSQL via postgres_client
```

##### H.2c Flashcard Database Schema

```sql
-- ADD via Alembic migration

CREATE TABLE flashcards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    module_topic VARCHAR(500) NOT NULL,
    job_id VARCHAR(255),
    front_text TEXT NOT NULL,
    back_text TEXT NOT NULL,
    blooms_level VARCHAR(20),
    source_section VARCHAR(500),
    difficulty VARCHAR(20) CHECK (difficulty IN ('easy', 'medium', 'hard')),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE flashcard_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES students(id),
    flashcard_id UUID REFERENCES flashcards(id),
    quality_rating INTEGER CHECK (quality_rating BETWEEN 0 AND 5),
    ease_factor DECIMAL(4,2) DEFAULT 2.50,
    interval INTEGER DEFAULT 0,        -- days
    repetitions INTEGER DEFAULT 0,
    next_review_date TIMESTAMP DEFAULT NOW(),
    reviewed_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(student_id, flashcard_id)   -- one active schedule per student per card
);

CREATE INDEX idx_flashcard_due ON flashcard_reviews(student_id, next_review_date);
```

##### H.2d Anki Export

```python
# ADD to backend/services/flashcard_generator.py

import sqlite3
import zipfile
import json

def export_anki_apkg(flashcards: list[dict], output_path: str) -> str:
    """
    Export flashcards to Anki .apkg format.

    .apkg format: ZIP containing:
    - collection.anki2 (SQLite database with notes, cards, models)
    - media (empty JSON object if no media)

    This is a minimal implementation for basic front/back cards.
    """
    # 1. Create SQLite database (collection.anki2) in memory
    # 2. Create model (note type) with Front/Back fields
    # 3. Insert each flashcard as a note + card
    # 4. ZIP the database + media file
    # 5. Return path to .apkg file
```

**Dependencies:** `pip install supermemo2`

---

#### H.3 RAG Chat Endpoint

**What it does:** Allows students to ask natural-language questions about the generated learning materials. Uses ChromaDB (already populated by Ingest + Research agents) for retrieval, GPT-5-mini for response generation.

```python
# NEW FILE: backend/services/rag_chat.py

from langsmith import traceable
from src.chromadb_store import ChromaDBStore
from src.config import settings

class RAGChatService:
    """
    Retrieval-Augmented Generation chat for learning content.

    Architecture:
    1. Student asks question + provides module_topic context
    2. Query ChromaDB for relevant chunks (filtered by module_topic)
    3. Construct prompt with retrieved context
    4. Stream GPT-5-mini response back to student

    ChromaDB already contains:
    - 'curriculum' collection: embedded chunks from uploaded PDFs/PPTX
    - 'research' collection: embedded web research results from Tavily

    This endpoint queries BOTH collections for comprehensive answers.
    """

    def __init__(self):
        self.store = ChromaDBStore()

    @traceable(name="rag_chat_query")
    async def answer_question(
        self, question: str, module_topic: str, stream: bool = True
    ):
        """
        Answer a student question using RAG.

        Args:
            question: Student's natural-language question
            module_topic: Topic context (filters ChromaDB retrieval)
            stream: Whether to stream the response

        Returns:
            Generator yielding response chunks (if stream=True)
            or complete response string (if stream=False)
        """
        # Step 1: Retrieve relevant chunks from both collections
        curriculum_chunks = self.store.query(
            collection="curriculum",
            query_text=question,
            n_results=settings.RAG_TOP_K,
            where={"module_topic": module_topic}  # filter by topic
        )
        research_chunks = self.store.query(
            collection="research",
            query_text=question,
            n_results=settings.RAG_TOP_K,
            where={"module_topic": module_topic}
        )

        # Step 2: Construct prompt with context
        context = self._format_context(curriculum_chunks, research_chunks)
        prompt = f"""You are a helpful educational assistant for the topic: {module_topic}.

Answer the student's question using ONLY the provided context from their course materials.
If the context doesn't contain enough information, say so clearly.
Always cite which section the information comes from.

CONTEXT FROM COURSE MATERIALS:
{context}

STUDENT QUESTION: {question}

ANSWER:"""

        # Step 3: Call GPT-5-mini with streaming
        # Use OpenAI client with stream=True for streaming responses
        # Yield chunks for real-time display in React frontend

    def _format_context(self, curriculum_chunks, research_chunks) -> str:
        """Format retrieved chunks into a readable context string."""
        sections = []
        for chunk in curriculum_chunks:
            sections.append(f"[Curriculum] {chunk['text']}")
        for chunk in research_chunks:
            sections.append(f"[Industry Research] {chunk['text']}")
        return "\n\n---\n\n".join(sections)
```

**FastAPI endpoint:**

```python
# NEW FILE: frontend/chat_routes.py

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from src.services.rag_chat import RAGChatService
from src.web.auth import require_student

router = APIRouter(prefix="/api/chat")

@router.post("/")
async def chat(
    question: str,
    module_topic: str,
    user = Depends(require_student)
):
    """
    RAG chat endpoint. Streams response chunks.

    Request body: {"question": "What is backpropagation?", "module_topic": "Neural Networks"}
    Response: Server-Sent Events stream of response text chunks
    """
    service = RAGChatService()

    async def event_stream():
        async for chunk in service.answer_question(question, module_topic):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

**React component:**

```jsx
// frontend/react-app/src/components/ChatPanel.jsx

// Key UX requirements:
// - Message history in browser state (useState, no localStorage)
// - Streaming response display (SSE via EventSource)
// - Topic selector dropdown (filters retrieval to current module)
// - Citation highlights: when response references "[Curriculum]" or "[Industry Research]",
//   render as styled badges
// - Input: text field + send button
// - Auto-scroll to bottom on new messages
```

**Key constraints:**
- Filter ChromaDB queries by `module_topic` to prevent cross-module information leakage
- Use GPT-5-mini (not GPT-5.1) for cost efficiency — chat is high-volume
- Stream responses via Server-Sent Events (SSE) for real-time display
- No server-side message history storage for MVP (browser state only)
- Add `@traceable` decorator for LangSmith visibility on RAG quality

---

#### H.4 Student Progress Dashboard

**React components:**

```jsx
// frontend/react-app/src/pages/StudentDashboard.jsx

// Three main visualisations:

// 1. Topic Mastery Radar Chart (Recharts RadarChart)
//    - Each axis = one module topic
//    - Value = average quiz score for that topic (0-100%)
//    - Overlaid with class average for comparison
//    - Data source: /api/student/progress

// 2. Flashcard Progress Timeline (Recharts LineChart)
//    - X-axis: dates
//    - Y-axis: cards reviewed / cards mastered / cards due
//    - Shows spaced repetition progress over time
//    - Data source: /api/student/flashcard-stats

// 3. Recommended Study Areas (sorted list)
//    - Combines: lowest quiz scores + overdue flashcards + sections not yet reviewed
//    - Each recommendation links to the relevant content section or flashcard deck
//    - Data source: /api/student/recommendations
```

**API endpoints:**

```python
# NEW FILE: frontend/student_routes.py

from fastapi import APIRouter, Depends
from src.web.auth import require_student
from src.db.postgres_client import PostgresClient

router = APIRouter(prefix="/api/student")

@router.get("/progress")
async def get_progress(user = Depends(require_student), db: PostgresClient = Depends()):
    """
    Return student's quiz scores per topic for radar chart.

    Query: SELECT q.module_topic, qa.total_score
           FROM quiz_attempts qa JOIN quizzes q ON qa.quiz_id = q.id
           WHERE qa.student_id = :student_id AND qa.completed_at IS NOT NULL
    """

@router.get("/flashcard-stats")
async def get_flashcard_stats(user = Depends(require_student), db: PostgresClient = Depends()):
    """
    Return flashcard review statistics over time.

    Query: SELECT DATE(reviewed_at) as date,
                  COUNT(*) as reviewed,
                  SUM(CASE WHEN interval >= 21 THEN 1 ELSE 0 END) as mastered,
                  (SELECT COUNT(*) FROM flashcard_reviews
                   WHERE student_id = :id AND next_review_date <= NOW()) as due
           FROM flashcard_reviews WHERE student_id = :student_id
           GROUP BY DATE(reviewed_at) ORDER BY date
    """

@router.get("/recommendations")
async def get_recommendations(user = Depends(require_student), db: PostgresClient = Depends()):
    """
    Return prioritised study recommendations.

    Algorithm:
    1. Get quiz topics with score < 70% → "Review this topic"
    2. Get flashcard decks with > 10 overdue cards → "Review flashcards for..."
    3. Get sections with < 50% question correct rate → "Focus on..."
    4. Sort by urgency (lowest score first, most overdue first)
    5. Return top 5 recommendations
    """
```

---

#### H.5 SCORM Course Bundle Export

```python
# NEW FILE: backend/services/scorm_bundler.py

import zipfile
import os
from jinja2 import Template
from src.config import settings

class SCORMBundler:
    """
    Packages all generated content for a module into a SCORM-compatible ZIP.

    SCORM 1.2 structure:
    course_bundle.zip
    ├── imsmanifest.xml          # SCORM metadata
    ├── content/
    │   ├── learning_guide.pdf    # Generated PDF
    │   ├── gap_analysis.pptx     # Generated PPT
    │   ├── lecture_video.mp4     # Generated video
    │   ├── quiz.html             # Self-contained quiz (HTML + JS)
    │   ├── mindmap.svg           # Generated mind map
    │   └── flashcards.json       # Flashcard data
    ├── css/
    │   └── styles.css            # Quiz styling
    └── js/
        └── scorm_api.js          # SCORM 1.2 API wrapper

    The quiz.html is self-contained: no server dependency.
    It communicates with the LMS via the SCORM JavaScript API
    (LMSInitialize, LMSSetValue, LMSCommit, LMSFinish).
    """

    MANIFEST_TEMPLATE = '''<?xml version="1.0" encoding="UTF-8"?>
<manifest identifier="CR8-{{ module_id }}" version="1.0"
  xmlns="http://www.imsproject.org/xsd/imscp_rootv1p1p2"
  xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_rootv1p2"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <metadata>
    <schema>ADL SCORM</schema>
    <schemaversion>1.2</schemaversion>
  </metadata>
  <organizations default="CR8_org">
    <organization identifier="CR8_org">
      <title>{{ module_title }}</title>
      <item identifier="item_1" identifierref="resource_1">
        <title>{{ module_title }} — Learning Materials</title>
      </item>
    </organization>
  </organizations>
  <resources>
    <resource identifier="resource_1" type="webcontent" adlcp:scormtype="sco"
      href="content/quiz.html">
      {% for file in content_files %}
      <file href="{{ file }}" />
      {% endfor %}
    </resource>
  </resources>
</manifest>'''

    def bundle(self, job_id: str, module_topic: str, output_path: str) -> str:
        """
        Assemble SCORM ZIP from generated content.

        Args:
            job_id: Pipeline job ID (to locate generated files)
            module_topic: Topic name for manifest metadata
            output_path: Path for output ZIP file

        Returns:
            Path to generated SCORM ZIP
        """
        job_dir = f"/tmp/jobs/{job_id}/output"

        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add generated content files
            content_files = []
            for fname in ["learning_guide.pdf", "gap_analysis.pptx",
                         "lecture_video.mp4", "mindmap.svg", "flashcards.json"]:
                fpath = os.path.join(job_dir, fname)
                if os.path.exists(fpath):
                    zf.write(fpath, f"content/{fname}")
                    content_files.append(f"content/{fname}")

            # Generate and add self-contained quiz HTML
            quiz_html = self._generate_quiz_html(job_id)
            zf.writestr("content/quiz.html", quiz_html)
            content_files.append("content/quiz.html")

            # Add SCORM API wrapper
            zf.writestr("js/scorm_api.js", self._get_scorm_api_js())
            content_files.append("js/scorm_api.js")

            # Add CSS
            zf.writestr("css/styles.css", self._get_quiz_css())
            content_files.append("css/styles.css")

            # Generate and add manifest
            manifest = Template(self.MANIFEST_TEMPLATE).render(
                module_id=job_id[:8],
                module_title=module_topic,
                content_files=content_files
            )
            zf.writestr("imsmanifest.xml", manifest)

        return output_path

    def _generate_quiz_html(self, job_id: str) -> str:
        """
        Generate self-contained HTML quiz with embedded questions + SCORM API.

        The quiz loads questions from embedded JSON (no server dependency).
        On completion, it reports the score to the LMS via:
        - API.LMSSetValue("cmi.core.score.raw", score)
        - API.LMSSetValue("cmi.core.lesson_status", "completed"/"failed")
        - API.LMSCommit("")
        - API.LMSFinish("")
        """
        # Load quiz data from PostgreSQL or job output
        # Embed as JSON in <script> tag
        # Include SCORM API calls for LMS communication
        # Return complete HTML string

    def _get_scorm_api_js(self) -> str:
        """Return SCORM 1.2 API wrapper JavaScript."""
        return '''
// SCORM 1.2 API Wrapper
var API = null;

function findAPI(win) {
    var findAPITries = 0;
    while ((win.API == null) && (win.parent != null) && (win.parent != win)) {
        findAPITries++;
        if (findAPITries > 7) return null;
        win = win.parent;
    }
    return win.API;
}

function initSCORM() {
    API = findAPI(window);
    if (API) API.LMSInitialize("");
}

function reportScore(score, maxScore) {
    if (!API) return;
    API.LMSSetValue("cmi.core.score.raw", String(score));
    API.LMSSetValue("cmi.core.score.max", String(maxScore));
    API.LMSSetValue("cmi.core.lesson_status", score >= (maxScore * 0.6) ? "passed" : "failed");
    API.LMSCommit("");
}

function finishSCORM() {
    if (API) API.LMSFinish("");
}

window.onload = initSCORM;
window.onunload = finishSCORM;
'''
```

**Key constraints:**
- SCORM 1.2 for maximum LMS compatibility (Canvas, Moodle, Blackboard all support it)
- Quiz HTML must be completely self-contained (no fetch calls, no server dependency)
- Quiz questions embedded as JSON in a `<script>` tag within the HTML
- SCORM API communication: `LMSInitialize`, `LMSSetValue`, `LMSCommit`, `LMSFinish`
- Pass threshold: 60% (configurable)
- Validate with [SCORM Cloud](https://cloud.scorm.com/) before production

---

#### H.6 Updated Tech Stack Summary (v0.7 Additions)

| Layer | Technology | Purpose | Status |
|-------|-----------|---------|--------|
| **Mind map rendering** | **Mermaid.js + mermaid-py** | **Module JSON → SVG/PNG mind maps** | **NEW — v0.7** |
| **Flashcard generation** | **GPT-5-mini** | **Generate front/back card pairs from modules** | **NEW — v0.7** |
| **Spaced repetition** | **supermemo2 (SM-2)** | **Flashcard review scheduling** | **NEW — v0.7** |
| **RAG chat** | **ChromaDB + GPT-5-mini** | **Student Q&A grounded in course content** | **NEW — v0.7** |
| **Student dashboard** | **React + Recharts** | **Progress visualisation, recommendations** | **NEW — v0.7** |
| **SCORM export** | **Python zipfile + Jinja2** | **LMS-compatible course bundles** | **NEW — v0.7** |
| **Anki export** | **sqlite3 + zipfile** | **Flashcard export to .apkg** | **NEW — v0.7** |

#### H.7 Updated Dependency Graph (v0.7)

```
v0.7 (depends on v0.6 completion for PostgreSQL, React, admin infrastructure):

  Mind Maps (independent — can start immediately):
    T-081 (mindmap generator) → T-082 (LangGraph node) → T-083 (React component)
    T-084 (mermaid-py setup) — do FIRST
    T-085 (tests) — after T-081

  Flashcards (depends on PostgreSQL from v0.5):
    T-087 (flashcard generator) → T-090 (API endpoints) → T-091 (React UI)
    T-088 (SM-2 scheduler) → T-090 (API endpoints)
    T-089 (Alembic migration) — do FIRST
    T-092 (Anki export) — independent, do after T-087
    T-093 (tests) — after T-090

  RAG Chat (depends on ChromaDB + FastAPI from existing pipeline):
    T-094 (rag_chat.py) → T-095 (chat API endpoint) → T-096 (React ChatPanel)
    T-097 (LangSmith tracing) — after T-094
    T-098 (tests) — after T-095

  Student Dashboard (depends on quiz data + flashcard data):
    T-099 (React dashboard) → depends on T-100 (API endpoints)
    T-101 (recommendation engine) → T-100
    T-102 (tests) — after T-100

  SCORM Export (depends on ALL content types being generated):
    T-104 (scorm_bundler.py) → T-105 (manifest template) → T-106 (quiz HTML)
    T-107 (export API) — after T-104
    T-108 (SCORM Cloud validation) — after T-107
    T-109 (tests) — after T-107

  Integration:
    T-110 (E2E test) — LAST, depends on all above
    T-111 (pyproject.toml) — do FIRST
    T-112 (Dockerfile update) — do FIRST
    T-113 (deploy) — after T-110
```

#### H.8 New Error Types (add to `src/utils/errors.py`)

```python
# ADD to src/utils/errors.py

class MindMapError(CR8Error):
    """Mermaid mind map generation or rendering failed."""
    pass

class FlashcardError(CR8Error):
    """Flashcard generation or SM-2 scheduling failed."""
    pass

class RAGChatError(CR8Error):
    """RAG chat retrieval or response generation failed."""
    pass

class SCORMBundleError(CR8Error):
    """SCORM package assembly or validation failed."""
    pass
```
