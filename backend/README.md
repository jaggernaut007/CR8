# backend/

Python backend for the CR8 Adaptive Learning Pipeline.

## Structure

```
backend/
├── config.py           ← Pydantic Settings: all env vars, model routing, temperatures
├── run_pipeline.py     ← CLI entry point: python -m backend.run_pipeline path/to/file.pdf
├── pipeline/           ← LangGraph 3-agent state machine
├── services/           ← External API wrappers (one file per integration)
├── prompts/            ← All prompt strings as Python constants
├── evals/              ← Evaluation framework (L1 structural + L2 LLM judges)
└── tests/              ← pytest tests (zero real API calls); 507 total across backend + frontend + GPU service
```

## Entry Points

| How to use | Command |
|------------|---------|
| Web UI | `make dev` → http://localhost:8080 |
| CLI | `make run ARGS="lecture.pdf"` |
| Tests | `make test` |
| Evals | `python -m backend.evals --help` |

## Key Files

- [config.py](config.py) — All configuration via environment variables
- [run_pipeline.py](run_pipeline.py) — CLI that calls `pipeline/graph.py`
- [pipeline/graph.py](pipeline/graph.py) — LangGraph graph definition

## Data Flow

```
PDF/PPTX input
    → file_parser.py (extract text, slides)
    → agent_ingest.py (identify topics, complexity scores)
    → agent_research.py (Tavily web search + ChromaDB context)
    → agent_generate.py (generate content per topic)
    → pdf_builder / ppt_builder / video_builder (or GPU service)
    → output files in outputs/
```

## Model Routing

Controlled by `backend/config.py` env vars:

| Setting | Use Case |
|---------|----------|
| `OPENAI_MODEL_NANO` | Fast extraction (topic IDs, keywords) |
| `OPENAI_MODEL_MINI` | Moderate reasoning (gap analysis, summaries) |
| `OPENAI_MODEL` | Main generation (learning guide sections) |
| `OPENAI_MODEL_PREMIUM` | Critical quality (final review, executive summary) |

## Services

One file per external integration in `backend/services/`:

| File | Purpose |
|------|---------|
| `llm.py` | OpenAI wrapper with 4-tier model routing |
| `chromadb_store.py` | ChromaDB vector store (all-MiniLM-L6-v2 embeddings) |
| `web_search.py` | Tavily API wrapper |
| `file_parser.py` | PyMuPDF PDF extraction + LibreOffice PPTX→PNG slide export |
| `pdf_builder.py` | fpdf2 learning guide PDF builder |
| `ppt_builder.py` | python-pptx gap analysis PowerPoint builder |
| `video_builder.py` | Kokoro TTS + MoviePy/ffmpeg local video pipeline; HeyGen API path |
| `tts_engine.py` | Kokoro TTS wrapper (lazy KPipeline, GPU-aware) |
| `script_parser.py` | Parses `[SLIDE N]` markers from video scripts |
| `gpu_utils.py` | Central GPU/hardware detection (`get_torch_device`, `get_ffmpeg_encoder`) |
| `gcs_client.py` | GCS upload/download for CPU↔GPU video job data transfer |
| `gpu_client.py` | HTTP client for the CR8 GPU Cloud Run video service |
