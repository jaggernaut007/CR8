# CLAUDE.md — backend/
<!-- Lazy-loaded when editing files inside backend/. Supplements root CLAUDE.md. -->

## Backend Architecture

### Pipeline (backend/pipeline/)
- `graph.py` — LangGraph graph definition and compilation; this is the pipeline entry point
- `state.py` — ALL pipeline state as a typed `TypedDict`; add new fields here only
- `agent_ingest.py` — Agent 1: extracts topics and structure from uploaded PDFs
- `agent_research.py` — Agent 2: enriches topics with Tavily web search + ChromaDB context
- `agent_generate.py` — Agent 3: generates learning guide content using OpenAI

### Services (backend/services/)
One file per external integration. Never add external API calls anywhere else:
- `llm.py` — OpenAI wrapper with model routing (nano/mini/model/premium)
- `chromadb_store.py` — ChromaDB vector store with all-MiniLM-L6-v2 embeddings
- `web_search.py` — Tavily API wrapper
- `file_parser.py` — PyMuPDF PDF extraction + python-pptx PPTX parsing + slide export
- `pdf_builder.py` — fpdf2 output builder
- `ppt_builder.py` — python-pptx output builder
- `video_builder.py` — Kokoro TTS video pipeline (two-phase: sequential TTS → parallel ffmpeg)
- `script_parser.py` — Parses `[SLIDE N]` markers from video scripts into segments
- `tts_engine.py` — Kokoro TTS wrapper with lazy model loading, GPU-aware device selection
- `gpu_utils.py` — GPU/hardware detection: torch device selection, ffmpeg encoder probing
- `gcs_client.py` — GCS upload/download for CPU↔video-service data transfer
- `gpu_client.py` — `VideoServiceClient`: 3-tier fallback HTTP client (GPU Primary → GPU Fallback → CPU Video). `GPUVideoClient` is a backward-compatible alias. Fallback triggers on `ConnectionError`, `Timeout`, or 5xx only — not on job-level errors.

### Prompts (backend/prompts/)
All prompt strings are Python constants — never put prompts inline in agents or services:
- `ingest.py`, `research.py`, `generate.py`, `ppt.py`, `video.py`

### Evals (backend/evals/)
Full evaluation framework with CLI:
- `cli.py` / `__main__.py` — `python -m backend.evals` entry point
- `judges/` — L1 structural checks + L2 LLM-as-judge scoring
- `harness/` — test runner, comparator, reporter
- `prompt_registry/` — versioned prompt variants for A/B comparison
- `datasets/` — cached pipeline states for reproducible evals

## Model Routing
Set in `backend/config.py` via env vars:
- `OPENAI_MODEL_NANO` — fast extraction tasks (topic identification, keyword extraction)
- `OPENAI_MODEL_MINI` — moderate reasoning (gap analysis, summaries)
- `OPENAI_MODEL` — main generation tasks (learning guide sections)
- `OPENAI_MODEL_PREMIUM` — critical quality tasks (executive summaries, final review)

## Key Rules
- State changes always go through `backend/pipeline/state.py` TypedDict
- New output formats require a new service in `backend/services/` + new prompts
- Prompt changes require running `python -m backend.evals run_ab` before committing
- All external API calls must have corresponding mocks in `backend/tests/`
