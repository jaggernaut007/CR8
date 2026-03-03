# CR8 Loop Intelligence — Implementation & Strategy Brief v0.3

## This document is the link between the codebase and the business strategy. It summarises the current technical implementation so the strategic roadmap can be built without needing to read through all the code.

**Last Updated**: 2026-03-03
**Previous Version**: Loop Intelligence 0.2 (2026-02-27)
**Version Delta**: Added Quiz Platform, Feedback Loop, Open-Source Video Pipeline; replanned video phases

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

## Current Implementation Status (as of v0.2)

The content generation prototype is **complete and deployed**.

### The 3-Agent Pipeline (Working)

**Ingest Agent** — Parses uploaded curriculum files (PDF/PPTX), uses GPT-5-nano to summarise each file in parallel (map-reduce for files >15K chars), extracts 10-25 structured topics (with key techniques, domain context, and curriculum scope boundary), chunks and embeds into ChromaDB `curriculum` collection.

**Research Agent** — Takes each topic, runs two parallel Tavily web searches per topic (job skills/applications + industry trends/alternatives), retrieves matching curriculum chunks from ChromaDB, feeds to GPT-5-mini for structured gap analysis (JSON mode) with severity rating (critical/moderate/minor). All topics researched concurrently via ThreadPoolExecutor.

**Generate Agent** — Retrieves context from both ChromaDB collections, looks up gap analysis, uses severity-based model routing (critical → GPT-5.1, moderate/minor → GPT-5-mini). Generates learning modules in markdown with 7 sections. All modules generate in parallel, then compile into chained output: PDF → PPT → Video Script → Video.

### Web UI (Working)

FastAPI web frontend with drag-and-drop PDF upload, format selection with dependency chain, real-time progress tracking (polling every 3s), file download.

### Deployment (Working)

Dockerised on GCP Cloud Run (europe-west2). Single container, Gunicorn + Uvicorn, ephemeral ChromaDB, secrets from GCP Secret Manager. Scales to zero (~£0 idle cost). Config: 2 GiB RAM (⚠️ **must increase to 4 GiB for video pipeline** — see Section B.8), 2 vCPU, 3600s timeout, max 1 instance.

### Test Coverage

144 tests passing (74 backend + 70 frontend).

---

## What's New in v0.3: Three Major Additions

### 1. Narrated Slide Video Pipeline (Open-Source)

**Problem**: v0.2 video pipeline used HeyGen API (avatar-only on white background, no slide integration). Expensive, vendor-locked, and didn't actually show slides.

**v0.3 Approach**: Two-phase implementation. Phase 1 (current sprint) removes the avatar entirely and delivers slides + voiceover using fully open-source tools. Phase 2 (future) adds an AI avatar overlay.

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

**Output spec:**
- Resolution: 1920×1080 (or matches slide aspect ratio)
- Codec: H.264 + AAC
- Target duration: ~2 minutes per topic module
- File size: ~15-30 MB per video
- Embeddable: standard MP4, plays in any browser `<video>` tag
- Downloadable: served via FastAPI file download endpoint

**Cost**: £0 per video (no API calls). Only compute cost on Cloud Run.

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
| Observability | LangSmith | Trace every LLM call | Working |
| Deployment | Docker + GCP Cloud Run | Containerised, scales to zero | Working |

---

## Updated Strategic Roadmap

### Phase 1 — Current Sprint (0-3 months)

1. **Open-source narrated slide video** — Slides + Kokoro TTS voiceover → MP4 via MoviePy/ffmpeg. No avatar. No API costs.
2. **Quiz platform MVP** — Quiz Agent generates questions. React frontend for students. One-attempt quizzes with red/green feedback. PostgreSQL for data storage.
3. **Admin dashboard v1** — Basic visualisation of quiz performance by topic and student. Question-level analytics.
4. **React frontend upgrade** — Replace single-page HTML with full React SPA (serves both quiz and content generation UI).
5. **Prompt v3 iteration** — Use eval framework for continued A/B testing.

### Phase 2 — Scale & Enrich (3-6 months)

1. **Avatar overlay** — Add SadTalker/MuseTalk talking head to video pipeline (requires GPU infrastructure).
2. **Content feedback loop** — Connect quiz analytics to Generate Agent. Automated content improvement based on student performance data.
3. **Admin quiz customisation** — Admin can edit questions, set difficulty levels, customise feedback messages.
4. **LMS integration** — LTI 1.3 API for Canvas, Moodle, Blackboard. Quiz results sync to grade books.
5. **Expand eval datasets** — Test across computer science, engineering, business courses.

### Phase 3 — Adaptive Intelligence (6-12 months)

1. **PPO + DKVMN hybrid system** — RL-based adaptive content selection based on quiz performance data.
2. **Cold start strategy** — ALEKS-style diagnostic assessment (20-30 questions).
3. **Multi-agent expansion** — Assessment Agent, Analytics Agent, Quality Assurance Agent, Adaptation Agent.
4. **Infrastructure migration** — Cloud Run → Kubernetes (GPU nodes), ChromaDB → PostgreSQL + DynamoDB, Redis Cluster.
5. **TTS upgrade** — Kokoro → Chatterbox or CosyVoice 3 (GPU, higher quality).

### Phase 4 — Production Scale (12-18+ months)

1. Multi-region Kubernetes deployment
2. CDN for video delivery (CloudFront)
3. Event streaming (Kafka) for interaction logging
4. WCAG 2.1 AA accessibility compliance
5. Published efficacy study
6. International expansion (Ireland → Australia/Canada → EU)

---

## Key Dependencies & Risks (Updated)

**API Cost Structure** — Pipeline remains API-heavy for content generation. Video pipeline is now £0 cost (open-source). Quiz generation adds ~$0.01-0.02 per quiz via GPT-5-mini.

**Content Quality Ceiling** — Now addressable via feedback loop. Quiz data provides quantitative signal for which content sections need improvement.

**Video Quality** — Kokoro TTS is near-commercial quality but not as polished as ElevenLabs. Acceptable for MVP. Upgrade path to Chatterbox/CosyVoice exists for Phase 3.

**Quiz Data Cold Start** — Feedback loop requires sufficient quiz data (target: 100+ students per topic). Until then, content improvement relies on manual educator feedback and eval framework.

**PostgreSQL Migration** — Quiz platform requires persistent database. This is the first step away from ephemeral ChromaDB. Must plan migration carefully.

**Single-Job Constraint** — Still enforced. Scaling to concurrent users requires job queuing. Quiz platform is independent and can handle concurrent users from day one.

---

## Immediate To-Do List (Ordered by Priority)

### Sprint 1: Video Pipeline (Weeks 1-3)

- [ ] **T-001**: Add `export_slides_as_images()` to `file_parser.py` — PyMuPDF for PDF slides, LibreOffice CLI for PPTX → PDF → PNG via pdftoppm
- [ ] **T-002**: Create `tts_engine.py` — wrapper around Kokoro TTS. Input: text string. Output: WAV file + duration in seconds. Handle sentence splitting for natural pacing.
- [ ] **T-003**: Rewrite `video_builder.py` — parse `[SLIDE N]` markers from script, match to slide PNGs, generate audio per segment, composite via MoviePy, output MP4.
- [ ] **T-004**: Add video download endpoint to FastAPI — serve generated MP4 files. Add `<video>` embed support.
- [ ] **T-005**: Update `requirements.txt` — add `kokoro>=0.9.4`, `moviepy>=2.0`, `soundfile>=0.12`, `Pillow>=10.0`, `numpy>=1.24`.
- [ ] **T-005b**: Create `src/utils/script_parser.py` — parse `[SLIDE N]` markers from script text into segment list (see Section B.3).
- [ ] **T-006**: Update Dockerfile — add `ffmpeg`, `espeak-ng`, `libreoffice-core`, `libreoffice-impress`, `poppler-utils`. **espeak-ng is critical** — Kokoro fails without it.
- [ ] **T-006b**: **BLOCKING** — Increase Cloud Run memory from 2 GiB to 4 GiB (see Section B.8). Kokoro peaks at ~3.4 GB RAM.
- [ ] **T-007**: Test video pipeline end-to-end with cs224n dataset. Verify: slides render correctly, audio syncs to slides, MP4 plays in browser.
- [ ] **T-008**: Update ProgressCapture — add video generation stage weighting.

### Sprint 2: Quiz Platform (Weeks 3-6)

- [ ] **T-009**: Create Quiz Agent — new LangGraph node. Input: learning module markdown. Output: structured quiz JSON (question text, options, correct answer, difficulty, Bloom's level, source section tag).
- [ ] **T-010**: Set up PostgreSQL — schema for: students, quizzes, questions, responses, scores. Deploy on Cloud SQL or containerised.
- [ ] **T-011**: Build quiz API endpoints — `POST /quiz/generate`, `GET /quiz/{id}`, `POST /quiz/{id}/submit`, `GET /quiz/{id}/results`.
- [ ] **T-012**: Build React quiz frontend — question display, option selection, submit, results page (green/red answers), feedback display. One-attempt enforcement.
- [ ] **T-013**: Build basic admin dashboard — topic performance heatmap, student score distribution, question difficulty analysis.
- [ ] **T-014**: Add JWT authentication — `src/web/auth.py` + `src/web/auth_routes.py`. Student login, admin login, role-based access. Use `python-jose[cryptography]` + `passlib[bcrypt]`. See Section G.3.
- [ ] **T-014b**: Add CORS middleware to `app.py` — allow React dev server on :3000. See Section G.2.
- [ ] **T-014c**: Set up Alembic for database migrations — `src/db/migrations/`. See Section G.4.
- [ ] **T-014d**: React build + FastAPI static serving — multi-stage Dockerfile, mount `/static`, catch-all route for SPA. See Section G.2.
- [ ] **T-015**: Write tests — Quiz Agent output validation, API endpoint tests, frontend component tests.

### Sprint 3: Feedback Loop & Polish (Weeks 6-9)

- [ ] **T-016**: Create `feedback_analyser.py` — query PostgreSQL for per-topic quiz aggregates. Output: structured feedback JSON with weak sections and recommendations.
- [ ] **T-017**: Modify `generate_agent.py` — accept optional `feedback_context`. Inject into GENERATE_MODULE prompt. Validate via eval framework that regenerated content doesn't regress.
- [ ] **T-018**: Admin quiz customisation UI — add/edit/delete questions, set difficulty, customise feedback text per question.
- [ ] **T-019**: Video embed/download integration — embed videos on quiz results page for review. Download button on all generated outputs.
- [ ] **T-020**: Deploy full stack — React frontend + FastAPI + PostgreSQL + video pipeline on Cloud Run. Update CI/CD.
- [ ] **T-021**: End-to-end integration test — upload curriculum → generate all outputs (PDF, PPT, video, quiz) → student takes quiz → admin views dashboard → feedback loop triggers regeneration.

### Future Sprints (Phase 2+)

- [ ] **T-022**: Avatar overlay — integrate SadTalker for talking head generation (requires GPU node).
- [ ] **T-023**: LTI 1.3 integration — Canvas, Moodle, Blackboard grade sync.
- [ ] **T-024**: TTS upgrade — evaluate Chatterbox vs CosyVoice 3 on GPU infrastructure.
- [ ] **T-025**: PPO + DKVMN prototype — adaptive content selection using quiz interaction data.

---

## Open Research Questions (Updated)

1. Does Kokoro TTS quality meet educator expectations for lecture-style narration? (Validate in Sprint 1)
2. What is the optimal number of quiz questions per learning module? (5? 10? 15?)
3. How many student quiz completions are needed before feedback loop produces meaningful improvement signals? (Hypothesis: 50-100 per topic)
4. Can quiz performance data serve as a proxy for DKVMN knowledge state initialisation? (Reduces cold start for Phase 3 RL)
5. What quiz completion rate can we expect without gamification? (Benchmark against MOOC quiz completion: ~20-40%)
6. How quickly does PPO policy converge in an educational domain?
7. What is the optimal reward function weighting (α, β, γ, δ) across different disciplines?

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
```
