# Implementation Plan: CR8 Pipeline — CLI-First Prototype

## Status: Complete

The 3-agent LangGraph pipeline is working end-to-end as a CLI tool. Feed curriculum PDFs in, get a market-enriched learning guide PDF out.

---

## Project Structure

```
Software/
  pyproject.toml              # dependencies
  Makefile                    # dev shortcuts: install, test, run, clean
  .env                        # API keys (OpenAI, Tavily, LangSmith)
  .env.example                # template for .env

  backend/
    __init__.py
    config.py                 # pydantic-settings loads .env
    run_pipeline.py           # CLI entry point: python -m backend.run_pipeline <files>

    pipeline/
      __init__.py
      graph.py                # LangGraph StateGraph: ingest → research → generate
      state.py                # PipelineState TypedDict
      agent_ingest.py         # Agent 1: parse files, extract topics, embed curriculum
      agent_research.py       # Agent 2: web search, gap analysis, store enrichments
      agent_generate.py       # Agent 3: generate modules, compile PDF

    services/
      __init__.py
      file_parser.py          # PyMuPDF text extraction (.pdf), python-pptx (.pptx)
      chromadb_store.py       # ChromaDB wrapper (curriculum + research collections)
      llm.py                  # OpenAI wrapper (GPT-5 + GPT-5-mini)
      web_search.py           # Tavily API wrapper
      pdf_builder.py          # fpdf2 PDF generation with Unicode sanitization

    prompts/
      __init__.py
      ingest.py               # SUMMARIZE_FILE + EXTRACT_TOPICS templates
      research.py             # GAP_ANALYSIS template
      generate.py             # GENERATE_MODULE template

    tests/
      __init__.py
      conftest.py             # Fixtures: CS224N test files, temp ChromaDB dir
      test_file_parser.py     # 3 tests
      test_chromadb_store.py  # 3 tests
      test_pdf_builder.py     # 20+ tests
      test_run_pipeline.py    # 10 tests (run_job validation + invocation)

  frontend/
    __init__.py
    app.py                    # FastAPI server + ProgressCapture
    templates/
      index.html              # Single-page UI (inline CSS + JS)
    tests/
      __init__.py
      test_api.py             # 28 endpoint tests
      test_progress_capture.py # 32 unit tests
```

Pipeline + services + CLI runner + FastAPI web frontend.

---

## Setup

### Prerequisites
- Python 3.11+
- API keys: OpenAI, Tavily, LangSmith

### Install
```bash
cd Software
python -m venv .venv
source .venv/bin/activate
make install   # pip install -e ".[dev]"
```

### Configure
Copy `.env.example` to `.env` and fill in your API keys:
```
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=cr8-prototype
```

### Run
```bash
# Single file
python -m backend.run_pipeline NLP_Course/CS224N_Downloads/Slides/01_Word_Vectors_I.pdf

# Multiple files
python -m backend.run_pipeline NLP_Course/CS224N_Downloads/Slides/*.pdf

# Tests
make test
```

Output PDF goes to `outputs/<timestamp>_learning_guide.pdf`.

---

## Implementation Steps (All Complete)

### Step 1: Scaffolding
- `pyproject.toml` with deps: langchain, langchain-openai, langgraph, langsmith, chromadb, pymupdf, python-pptx, tavily-python, fpdf2, pydantic-settings, jinja2, markdown
- `Makefile`: install, test, run, clean
- `backend/config.py`: pydantic-settings loading `.env`

### Step 2: File Parser (TDD)
- PyMuPDF page-by-page extraction for PDFs
- python-pptx slide-by-slide extraction for .pptx
- Returns `[{"text": "...", "source": "filename.pdf", "page": 1}, ...]`

### Step 3: ChromaDB Service (TDD)
- PersistentClient with get_or_create_collection
- Two collections: `curriculum` (raw text chunks) and `research` (search results + enrichments)
- Default embeddings (all-MiniLM-L6-v2) — no OpenAI embeddings needed

### Step 4: LLM + Web Search Services
- `llm.py`: `get_llm("mini")` → GPT-5-mini, `get_llm("full")` → GPT-5
- `web_search.py`: Tavily wrapper, `search(query, max_results=5)`

### Step 5: Agent 1 — Ingest
- Parse files → summarize each (GPT-5-mini, 15k char limit per file)
- Extract topics from combined summaries (JSON mode) → `[{name, description}]`
- Chunk text (RecursiveCharacterTextSplitter, 1500 chars, 150 overlap) → embed into ChromaDB `curriculum`

### Step 6: Agent 2 — Research
- For each topic: 2 Tavily searches (job skills + industry trends), 5 results each
- Retrieve top 3 curriculum chunks from ChromaDB
- GPT-5-mini gap analysis → `{topic, gaps, enrichments}`
- Store enrichments in ChromaDB `research` collection
- Deduplicates document IDs to prevent ChromaDB DuplicateIDError

### Step 7: Agent 3 — Generate + PDF
- For each topic: retrieve from both ChromaDB collections
- GPT-5 generates module markdown (objectives, content, industry context, takeaways, resources)
- fpdf2 compiles all modules into PDF with cover page, TOC, and chapters
- Unicode sanitization handles GPT's smart quotes, em dashes, bullets, etc.

### Step 8: Pipeline Wiring + CLI
- LangGraph StateGraph: `START → ingest → research → generate → END`
- CLI entry point: `python -m backend.run_pipeline <files>`
- LangSmith traces at `cr8-prototype` project

### Step 9: FastAPI Web Frontend (TDD)
- `frontend/app.py`: FastAPI async server with `ProgressCapture` class for real-time progress tracking
- `frontend/templates/index.html`: Single-page UI with upload, format selection, progress bar, download
- `backend/run_pipeline.py`: Added `run_job()` function — programmatic entry point for the web layer
- `backend/config.py`: Added `"extra": "ignore"` to handle extra `.env` keys gracefully
- Pipeline runs in background thread via `asyncio.to_thread()`, preserving all `ThreadPoolExecutor` parallelism
- `ProgressCapture` intercepts stdout, parses `[Stage]` prefixes, computes progress % with stage weights
- Three API endpoints: upload PDF, start pipeline, poll progress; plus download endpoint for completed files
- Frontend polls `/api/progress` every 3s, shows stage label, progress bar, elapsed/estimated time, scrolling logs
- Video checkbox disabled by default (requires HeyGen keys in `.env`)
- Single job at a time (prototype scope — `settings` is a global singleton)
- 70 new tests: `test_api.py` (28), `test_progress_capture.py` (32), `test_run_pipeline.py` (10)
- Dependencies added: `fastapi>=0.115`, `uvicorn[standard]>=0.34`, `python-multipart>=0.0.9`, `httpx>=0.27` (dev)

---

## Key Technical Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Entry point | CLI + FastAPI | CLI for dev iteration; FastAPI web UI for users |
| PDF lib | **fpdf2** | Pure Python, no system deps (WeasyPrint required pango/glib which had FFI issues on macOS) |
| Embeddings | ChromaDB default (all-MiniLM-L6-v2) | Free, local, no API cost |
| LLM split | GPT-5-mini (agents 1+2), GPT-5 (agent 3) | Save cost on extraction, quality on generation |
| Concurrency | `ThreadPoolExecutor` | stdlib, no extra deps; `max_workers=4` configurable via settings |
| Domain scoping | `curriculum_scope` in state | Prevents LLM drift into unrelated topics; enforced in all prompts |
| Progress | Print statements + ProgressCapture | Pipeline prints `[Stage]` prefixes; web UI captures stdout and parses progress |
| Web framework | FastAPI + uvicorn | Async HTTP, matches Technical Assessment MVP stack recommendation |

---

## Post-Prototype Improvements (Complete)

### Parallelization
All three agents now use `ThreadPoolExecutor` (controlled by `max_workers` in config, default 4):
- **Ingest**: File summarization runs concurrently
- **Research**: All topics researched in parallel; within each topic, the two web searches also run in parallel
- **Generate**: All learning modules generated concurrently

### Domain Scoping
New `curriculum_scope` field flows through the entire pipeline to prevent topic drift:
- Ingest extracts a one-sentence scope description along with enriched topic metadata (`key_techniques`, `domain_context`)
- Research and Generate prompts enforce staying within the curriculum's domain
- Web search queries are more targeted using techniques and domain context instead of generic topic names

### Test Hardening
PDF builder tests expanded from 1 to 20+ covering Unicode edge cases, malformed markdown, empty/long content, special characters, and structural mismatches.

### Bug Fix
- PDF title on cover page now sanitized to prevent `UnicodeEncodeError`

---

## Known Issues / Notes

- **fpdf2 Unicode**: Latin-1 only. The `_sanitize()` function maps common Unicode chars from GPT output to ASCII equivalents. Remaining non-latin-1 chars are replaced with `?`.
- **ChromaDB dedup**: Research agent deduplicates search results by MD5 hash to avoid DuplicateIDError.

---

## Test Data

- **Quick** (1 file): `NLP_Course/CS224N_Downloads/Slides/01_Word_Vectors_I.pdf`
- **Medium** (3 files): Slides 01, 08, 09
- **Full** (all slides): `NLP_Course/CS224N_Downloads/Slides/*.pdf`

---

## Verification

1. `make test` — 144 tests pass (74 backend + 70 frontend)
2. `python -m backend.run_pipeline <file>` — produces PDF in `outputs/`
3. `make dev` — web UI at http://localhost:8000, upload PDF, track progress, download output
4. LangSmith dashboard shows traces for all 3 nodes
5. PDF has cover page, TOC, chapters with market-enriched content
