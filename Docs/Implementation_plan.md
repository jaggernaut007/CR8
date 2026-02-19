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
      test_pdf_builder.py     # 1 test
```

No `api/`, no `frontend/`, no web layer. Just pipeline + services + CLI runner.

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

---

## Key Technical Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Entry point | CLI script | Fastest iteration — no server overhead |
| PDF lib | **fpdf2** | Pure Python, no system deps (WeasyPrint required pango/glib which had FFI issues on macOS) |
| Embeddings | ChromaDB default (all-MiniLM-L6-v2) | Free, local, no API cost |
| LLM split | GPT-5-mini (agents 1+2), GPT-5 (agent 3) | Save cost on extraction, quality on generation |
| Progress | Print statements | Simple; upgrade to rich/tqdm later |

---

## Known Issues / Notes

- **Runtime**: ~29 minutes for a single slide with 15 topics (mostly API calls). Parallelization would help.
- **fpdf2 Unicode**: Latin-1 only. The `_sanitize()` function maps common Unicode chars from GPT output to ASCII equivalents. Remaining non-latin-1 chars are replaced with `?`.
- **ChromaDB dedup**: Research agent deduplicates search results by MD5 hash to avoid DuplicateIDError.

---

## Test Data

- **Quick** (1 file): `NLP_Course/CS224N_Downloads/Slides/01_Word_Vectors_I.pdf`
- **Medium** (3 files): Slides 01, 08, 09
- **Full** (all slides): `NLP_Course/CS224N_Downloads/Slides/*.pdf`

---

## Verification

1. `make test` — 7 unit tests pass (file parser, ChromaDB, PDF builder)
2. `python -m backend.run_pipeline <file>` — produces PDF in `outputs/`
3. LangSmith dashboard shows traces for all 3 nodes
4. PDF has cover page, TOC, chapters with market-enriched content
