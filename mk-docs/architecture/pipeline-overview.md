# Pipeline Overview

## LangGraph Pipeline

CR8's pipeline is a linear 3-node [LangGraph](https://github.com/langchain-ai/langgraph) `StateGraph`. Each node is a Python function that receives the shared `PipelineState` dict, performs its work, and returns updates to that state.

```
START --> [ingest] --> [research] --> [generate] --> END
```

The graph is defined in `backend/pipeline/graph.py`:

```python
from langgraph.graph import StateGraph, START, END
from backend.pipeline.state import PipelineState

def build_pipeline():
    graph = StateGraph(PipelineState)

    graph.add_node("ingest", ingest_node)
    graph.add_node("research", research_node)
    graph.add_node("generate", generate_node)

    graph.add_edge(START, "ingest")
    graph.add_edge("ingest", "research")
    graph.add_edge("research", "generate")
    graph.add_edge("generate", END)

    return graph.compile()
```

There are no conditional edges or branching -- every run executes all three agents in sequence. The compiled graph is invoked with an `initial_state` dict containing `job_id`, `file_paths`, and empty placeholders for downstream fields.

## How to Run

### CLI

```bash
# Single file
python -m backend.run_pipeline path/to/lecture.pdf

# Multiple files
python -m backend.run_pipeline slides/01.pdf slides/02.pdf slides/03.pdf

# Glob pattern
python -m backend.run_pipeline NLP_Course/CS224N_Downloads/Slides/*.pdf

# With output format selection
python -m backend.run_pipeline --format pdf,script slides/*.pdf
python -m backend.run_pipeline --format pdf,video slides/*.pdf
```

The CLI entry point is `backend/run_pipeline.py`. It parses arguments, validates format flags, builds the pipeline via `build_pipeline()`, and invokes it with an initial state.

### Web UI

```bash
make dev
# Opens at http://localhost:8080
```

The web UI (`frontend/app.py`) calls `run_job()` from `backend/run_pipeline.py`, which wraps the same `build_pipeline().invoke()` call. The pipeline runs in a background thread via `asyncio.to_thread()`, with `ProgressCapture` intercepting stdout to provide real-time progress updates.

## Project Structure

```
Software/
├── .env.example              # Environment variable template
├── .gitignore                # Git ignore rules
├── Makefile                  # Dev shortcuts (install, test, run, clean)
├── pyproject.toml            # Python deps and project config
├── README.md                 # Project README
│
├── backend/
│   ├── __init__.py
│   ├── config.py             # Pydantic-settings config (loads .env)
│   ├── run_pipeline.py       # CLI entry point + run_job() for web
│   │
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── state.py          # PipelineState TypedDict
│   │   ├── graph.py          # LangGraph StateGraph definition
│   │   ├── agent_ingest.py   # Agent 1: parse, extract topics, embed
│   │   ├── agent_research.py # Agent 2: web search, gap analysis
│   │   └── agent_generate.py # Agent 3: generate modules, build PDF
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── file_parser.py    # PDF/PPTX text extraction + slide export
│   │   ├── chromadb_store.py # ChromaDB wrapper (add, query, reset)
│   │   ├── llm.py            # OpenAI wrapper (nano/mini/premium tiers)
│   │   ├── web_search.py     # Tavily search wrapper
│   │   ├── pdf_builder.py    # fpdf2 PDF generation (rich text, code blocks)
│   │   ├── ppt_builder.py    # python-pptx gap analysis PowerPoint
│   │   ├── video_builder.py  # Kokoro TTS video pipeline (two-phase: TTS → ffmpeg)
│   │   ├── script_parser.py  # Parse [SLIDE N] markers from video scripts
│   │   ├── tts_engine.py     # Kokoro TTS wrapper (GPU-aware device selection)
│   │   ├── gpu_utils.py      # GPU/hardware detection (torch device, ffmpeg encoder)
│   │   ├── gcs_client.py     # GCS upload/download for CPU↔GPU data transfer
│   │   └── gpu_client.py     # HTTP client for GPU service (identity token auth)
│   │
│   ├── prompts/
│   │   ├── __init__.py
│   │   ├── ingest.py         # SUMMARIZE_FILE, SUMMARIZE_CHUNK, REDUCE_SUMMARIES, EXTRACT_TOPICS
│   │   ├── research.py       # GAP_ANALYSIS (with severity)
│   │   ├── generate.py       # GENERATE_MODULE
│   │   ├── ppt.py            # STRUCTURE_GAP_SLIDES, STRUCTURE_SINGLE_TOPIC_SLIDE, STRUCTURE_EXECUTIVE_SUMMARY
│   │   └── video.py          # MODULE_TO_SCRIPT, SCRIPT_FROM_SLIDES, HOOK_EXAMPLES
│   │
│   ├── evals/                # Evaluation framework (L1 structural + L2 LLM judge)
│   │   ├── config.py
│   │   ├── cli.py
│   │   ├── run_ab_comparison.py
│   │   └── prompt_registry/
│   │       └── variants/     # Versioned prompt variants (generate_v2.py, video_v2.py)
│   │
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py       # Shared fixtures
│       ├── test_file_parser.py
│       ├── test_chromadb_store.py
│       ├── test_pdf_builder.py
│       └── test_run_pipeline.py
│
├── frontend/
│   ├── __init__.py
│   ├── app.py                # FastAPI server + ProgressCapture
│   ├── templates/
│   │   └── index.html        # Single-page UI (inline CSS + JS)
│   └── tests/
│       ├── __init__.py
│       ├── test_api.py       # FastAPI endpoint tests
│       └── test_progress_capture.py
│
├── gpu_service/              # GPU microservice (Kokoro TTS + ffmpeg on NVIDIA L4)
│   ├── app.py                # FastAPI endpoints for video jobs
│   ├── worker.py             # Video rendering worker
│   ├── config.py             # GPU service configuration
│   └── gcs_client.py         # GCS client for downloading/uploading
│
├── docs/                     # Project documentation
├── outputs/                  # Generated PDFs (gitignored)
├── chroma_db/                # Vector database (gitignored)
└── NLP_Course/               # Test data (Stanford CS224N)
    └── CS224N_Downloads/
        └── Slides/           # Lecture PDFs for testing
```

## Agent Responsibilities

| Agent | File | Input | Output | Model(s) |
|-------|------|-------|--------|----------|
| **Ingest** | `agent_ingest.py` | Curriculum PDFs | Topics, raw text, curriculum scope, ChromaDB `curriculum` collection | GPT-5-nano |
| **Research** | `agent_research.py` | Topics + curriculum scope | Gap summary (severity, gaps, enrichments), ChromaDB `research` collection | GPT-5-mini, Tavily API |
| **Generate** | `agent_generate.py` | Topics + gaps + both ChromaDB collections | PDF, PPT, video scripts, videos | GPT-5.1 (critical), GPT-5-mini (moderate/minor), GPT-5-nano (PPT summary) |

All agents process their work in parallel using `ThreadPoolExecutor` (controlled by the `MAX_WORKERS` setting, default 8).
