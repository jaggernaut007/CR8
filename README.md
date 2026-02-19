# CR8 — Adaptive Learning Pipeline

A 3-agent AI pipeline that transforms university curriculum materials into market-enriched learning guides. Feed in lecture PDFs, get out a structured PDF with industry context, gap analysis, and curated resources.

```
Curriculum PDFs  ──>  [Ingest]  ──>  [Research]  ──>  [Generate]  ──>  Learning Guide PDF
                      Agent 1        Agent 2          Agent 3
```

Built with LangGraph, OpenAI, ChromaDB, Tavily, and fpdf2.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Architecture Overview](#architecture-overview)
- [Pipeline Deep Dive](#pipeline-deep-dive)
  - [Agent 1: Ingest](#agent-1-ingest)
  - [Agent 2: Research](#agent-2-research)
  - [Agent 3: Generate](#agent-3-generate)
- [Project Structure](#project-structure)
- [Services Reference](#services-reference)
  - [File Parser](#file-parser)
  - [ChromaDB Store](#chromadb-store)
  - [LLM Wrapper](#llm-wrapper)
  - [Web Search](#web-search)
  - [PDF Builder](#pdf-builder)
- [Prompt Templates](#prompt-templates)
- [Configuration](#configuration)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Future Work](#future-work)

---

## Quick Start

### Prerequisites

- Python 3.11 or higher
- API keys for: [OpenAI](https://platform.openai.com/), [Tavily](https://tavily.com/), [LangSmith](https://smith.langchain.com/) (optional but recommended)

### Installation

```bash
# Clone and navigate to the project
cd Software

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
make install
```

### Configuration

Copy the example env file and fill in your API keys:

```bash
cp .env.example .env
```

Then edit `.env`:

```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5
OPENAI_MODEL_MINI=gpt-5-mini
TAVILY_API_KEY=tvly-...
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=cr8-prototype
```

### Run the Pipeline

```bash
# Single file
python -m backend.run_pipeline path/to/lecture.pdf

# Multiple files
python -m backend.run_pipeline slides/01.pdf slides/02.pdf slides/03.pdf

# Glob pattern
python -m backend.run_pipeline NLP_Course/CS224N_Downloads/Slides/*.pdf
```

Output PDF is saved to `outputs/<timestamp>_learning_guide.pdf`.

### Run Tests

```bash
make test
```

---

## Architecture Overview

CR8 uses a **linear 3-agent pipeline** orchestrated by [LangGraph](https://github.com/langchain-ai/langgraph). Each agent is a node in a directed graph, passing state forward through a shared `PipelineState` dictionary.

```
┌─────────────────────────────────────────────────────────────────┐
│                        LangGraph Pipeline                       │
│                                                                 │
│   START ──> [Ingest Node] ──> [Research Node] ──> [Generate Node] ──> END
│                  │                   │                   │       │
│                  ▼                   ▼                   ▼       │
│             ChromaDB            ChromaDB             ChromaDB    │
│           (curriculum)         (research)          (both cols)   │
│                                    │                   │        │
│                              Tavily Search        OpenAI GPT-5  │
│                              OpenAI Mini          PDF Builder   │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

State is a `TypedDict` that accumulates data as it passes through each node:

| Field | Set by | Type | Description |
|-------|--------|------|-------------|
| `job_id` | CLI runner | `str` | Random 12-char hex ID |
| `file_paths` | CLI runner | `list[str]` | Input file paths |
| `topics` | Agent 1 | `list[dict]` | `[{"name": "...", "description": "..."}]` |
| `raw_text` | Agent 1 | `str` | Concatenated extracted text |
| `gap_summary` | Agent 2 | `list[dict]` | Gap analysis per topic |
| `pdf_path` | Agent 3 | `str` | Path to output PDF |
| `current_stage` | All agents | `str` | `starting` → `ingested` → `researched` → `complete` |

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Pipeline orchestration | LangGraph | State machine for agent coordination |
| LLM (extraction) | OpenAI GPT-5-mini | Topic extraction, summarization, gap analysis |
| LLM (generation) | OpenAI GPT-5 | Learning module content generation |
| Vector store | ChromaDB | Semantic search over curriculum and research |
| Embeddings | all-MiniLM-L6-v2 | ChromaDB default, local, free |
| Web search | Tavily API | Industry trends and job requirements |
| PDF text extraction | PyMuPDF (fitz) | Extract text from PDF files |
| Slide extraction | python-pptx | Extract text from PowerPoint files |
| PDF generation | fpdf2 | Compile learning guide PDF |
| Configuration | pydantic-settings | Type-safe env loading |
| Observability | LangSmith | Trace every LLM call |

---

## Pipeline Deep Dive

### Agent 1: Ingest

**File**: `backend/pipeline/agent_ingest.py`

Parses curriculum files, identifies topics, and builds the vector knowledge base.

**Process**:

1. **Parse files** — Extract text page-by-page using PyMuPDF (`.pdf`) or python-pptx (`.pptx`)
2. **Summarize** — Each file is summarized by GPT-5-mini (truncated to 15,000 chars to fit context)
3. **Extract topics** — Combined summaries are analyzed by GPT-5-mini (JSON mode) to produce 10-25 topics, each with a name and description
4. **Chunk and embed** — Raw text is split into 1,500-character chunks (150 overlap) using `RecursiveCharacterTextSplitter`, then embedded into ChromaDB's `curriculum` collection

**Console output**:
```
[Ingest] Starting...
[Ingest] Parsed 01_Word_Vectors_I.pdf — 73 pages
[Ingest] Summarized 01_Word_Vectors_I.pdf
[Ingest] Extracted 15 topics
[Ingest] Embedded 48 chunks into ChromaDB
```

**State updates**: `topics`, `raw_text`, `current_stage = "ingested"`

---

### Agent 2: Research

**File**: `backend/pipeline/agent_research.py`

For each topic, researches current industry requirements and identifies curriculum gaps.

**Process** (per topic):

1. **Web search** — Two Tavily searches:
   - `"{topic} job requirements skills 2025 2026"` (5 results)
   - `"{topic} industry trends applications 2025 2026"` (5 results)
2. **Curriculum retrieval** — Top 3 matching chunks from ChromaDB `curriculum` collection
3. **Gap analysis** — GPT-5-mini compares curriculum content against industry findings (JSON mode), producing gaps and enrichments
4. **Store enrichments** — All search results and enrichments are embedded into ChromaDB `research` collection (deduplicated by MD5 hash)

**Console output**:
```
[Research] Starting...
[Research] Topic 1/15: Word2Vec Embeddings
[Research]   Found 4 gaps
[Research] Topic 2/15: GloVe and Global Methods
[Research]   Found 3 gaps
...
[Research] Completed — 15 topics analyzed
```

**State updates**: `gap_summary`, `current_stage = "researched"`

---

### Agent 3: Generate

**File**: `backend/pipeline/agent_generate.py`

Generates full learning modules and compiles the final PDF.

**Process** (per topic):

1. **Retrieve context** — Top 5 chunks from `curriculum` + top 5 from `research` collections
2. **Get gap analysis** — Looks up the gap summary for this topic
3. **Generate module** — GPT-5 (full model) generates a markdown module with sections: Learning Objectives, Core Content, Industry Context, Key Takeaways, Further Reading
4. **Compile PDF** — All modules are rendered into a formatted PDF with cover page, table of contents, and one chapter per topic

**Console output**:
```
[Generate] Starting...
[Generate] Module 1/15: Word2Vec Embeddings
[Generate]   Done — 3847 chars
...
[Generate] PDF written to outputs/20260218_235751_learning_guide.pdf
```

**State updates**: `pdf_path`, `current_stage = "complete"`

**Output PDF structure**:
- Cover page (title, date, topic count)
- Table of contents
- Chapters (one per topic), each containing:
  - Chapter title and description
  - Learning Objectives
  - Core Content
  - Industry Context
  - Key Takeaways
  - Further Reading

---

## Project Structure

```
Software/
├── .env.example              # Environment variable template
├── .gitignore                # Git ignore rules
├── Makefile                  # Dev shortcuts (install, test, run, clean)
├── pyproject.toml            # Python deps and project config
├── README.md                 # This file
│
├── backend/
│   ├── __init__.py
│   ├── config.py             # Pydantic-settings config (loads .env)
│   ├── run_pipeline.py       # CLI entry point
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
│   │   ├── file_parser.py    # PDF/PPTX text extraction
│   │   ├── chromadb_store.py # ChromaDB wrapper (add, query, reset)
│   │   ├── llm.py            # OpenAI ChatOpenAI wrapper
│   │   ├── web_search.py     # Tavily search wrapper
│   │   └── pdf_builder.py    # fpdf2 PDF generation
│   │
│   ├── prompts/
│   │   ├── __init__.py
│   │   ├── ingest.py         # SUMMARIZE_FILE, EXTRACT_TOPICS
│   │   ├── research.py       # GAP_ANALYSIS
│   │   └── generate.py       # GENERATE_MODULE
│   │
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py       # Shared fixtures
│       ├── test_file_parser.py
│       ├── test_chromadb_store.py
│       └── test_pdf_builder.py
│
├── Docs/
│   ├── Prototype_plan.md     # Original system design
│   ├── Implementation_plan.md # Build log and decisions
│   └── Technical_assessment.md # Research on adaptive learning tech
│
├── outputs/                  # Generated PDFs (gitignored)
├── chroma_db/                # Vector database (gitignored)
└── NLP_Course/               # Test data (Stanford CS224N)
    └── CS224N_Downloads/
        └── Slides/           # Lecture PDFs for testing
```

---

## Services Reference

### File Parser

**File**: `backend/services/file_parser.py`

Extracts text from curriculum files. Supports PDF (via PyMuPDF) and PowerPoint (via python-pptx).

```python
from backend.services.file_parser import extract_text

pages = extract_text("lecture.pdf")
# Returns: [
#   {"text": "Lecture 1: Introduction...", "source": "lecture.pdf", "page": 1},
#   {"text": "Word embeddings are...",    "source": "lecture.pdf", "page": 2},
#   ...
# ]
```

| Function | Signature | Description |
|----------|-----------|-------------|
| `extract_text` | `(file_path: str) -> list[dict]` | Route to PDF or PPTX extractor based on extension |

Supported formats: `.pdf`, `.pptx`

---

### ChromaDB Store

**File**: `backend/services/chromadb_store.py`

Wrapper around ChromaDB's persistent client. Manages two collections:
- **`curriculum`** — Chunked text from source materials
- **`research`** — Web search results and enrichment content from gap analysis

```python
from backend.services.chromadb_store import ChromaStore

store = ChromaStore("./chroma_db")

# Add documents
store.add_documents("curriculum", documents=["text..."], metadatas=[{"source": "file.pdf"}], ids=["doc_1"])

# Query
results = store.query("curriculum", "attention mechanism", n_results=5)
# Returns: {"documents": [["..."]], "metadatas": [[{...}]], "distances": [[0.3, ...]]}

# Reset (deletes both collections)
store.reset_collections()
```

| Method | Signature | Description |
|--------|-----------|-------------|
| `__init__` | `(persist_dir: str)` | Create persistent ChromaDB client |
| `get_or_create_collection` | `(name: str)` | Get or create a collection |
| `add_documents` | `(collection_name, documents, metadatas=None, ids=None)` | Add docs to collection |
| `query` | `(collection_name, query_text, n_results=5)` | Semantic search |
| `reset_collections` | `()` | Delete curriculum and research collections |

Uses ChromaDB's built-in `all-MiniLM-L6-v2` embeddings — local, free, no API calls.

---

### LLM Wrapper

**File**: `backend/services/llm.py`

Thin wrapper around `langchain-openai`'s `ChatOpenAI`.

```python
from backend.services.llm import get_llm

mini = get_llm("mini")   # GPT-5-mini — for extraction and analysis
full = get_llm("full")   # GPT-5 — for content generation

response = mini.invoke("Summarize this text...")
print(response.content)
```

| Function | Signature | Description |
|----------|-----------|-------------|
| `get_llm` | `(model: str = "mini") -> ChatOpenAI` | Returns configured LLM instance |

Both models use `temperature=0.3` for consistent outputs.

---

### Web Search

**File**: `backend/services/web_search.py`

Wrapper around Tavily's search API for finding industry context.

```python
from backend.services.web_search import search

results = search("transformer models job requirements 2025", max_results=5)
# Returns: [
#   {"title": "...", "url": "...", "content": "...", "score": 0.95},
#   ...
# ]
```

| Function | Signature | Description |
|----------|-----------|-------------|
| `search` | `(query: str, max_results: int = 5) -> list[dict]` | Search the web via Tavily |

Uses `search_depth="basic"` for fast results. The client is lazily initialized as a singleton.

---

### PDF Builder

**File**: `backend/services/pdf_builder.py`

Generates formatted A4 PDFs from topic data and markdown module content using fpdf2.

```python
from backend.services.pdf_builder import build_pdf

build_pdf(
    title="Market-Enriched Learning Guide",
    topics=[{"name": "Word2Vec", "description": "..."}],
    modules_md=["## Learning Objectives\n- Explain word embeddings..."],
    output_path="outputs/guide.pdf",
)
```

| Function / Class | Description |
|------------------|-------------|
| `build_pdf(title, topics, modules_md, output_path)` | Main entry point — generates the full PDF |
| `_sanitize(text)` | Replace Unicode characters that Helvetica (latin-1) can't render |
| `_render_markdown_line(pdf, line)` | Render a single markdown line (headings, bullets, paragraphs) |
| `_LearningGuidePDF` | Custom FPDF subclass with header/footer |

**PDF settings**: A4 format, 25mm side margins, 20mm top/bottom margins, Helvetica font family.

**Unicode handling**: GPT outputs often include smart quotes, em dashes, bullets, and other Unicode characters that latin-1 can't encode. The `_sanitize()` function maps 20+ common Unicode chars to ASCII equivalents, with a catch-all `encode("latin-1", errors="replace")` fallback.

---

## Prompt Templates

All prompts live in `backend/prompts/` and use Python string `.format()` for variable interpolation.

### Ingest Prompts (`backend/prompts/ingest.py`)

**`SUMMARIZE_FILE`** — Summarizes a single curriculum file (300-500 words). Focuses on topics, technical terms, and depth of coverage.

Variables: `{source}`, `{text}`

**`EXTRACT_TOPICS`** — Extracts 10-25 distinct topics from combined file summaries. Returns JSON with `{"topics": [{"name": "...", "description": "..."}]}`.

Variables: `{summaries}`

### Research Prompt (`backend/prompts/research.py`)

**`GAP_ANALYSIS`** — Compares curriculum coverage against industry job requirements and trends. Returns JSON with `{topic, curriculum_coverage, industry_demands, gaps, enrichments}`.

Variables: `{topic_name}`, `{topic_description}`, `{curriculum_chunks}`, `{job_results}`, `{trend_results}`

### Generate Prompt (`backend/prompts/generate.py`)

**`GENERATE_MODULE`** — Generates a full learning module in markdown with five sections: Learning Objectives, Core Content, Industry Context, Key Takeaways, Further Reading.

Variables: `{topic_name}`, `{topic_description}`, `{curriculum_chunks}`, `{research_chunks}`, `{gap_analysis}`

---

## Configuration

All configuration is managed through environment variables, loaded by `backend/config.py` using pydantic-settings.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | — | OpenAI API key |
| `OPENAI_MODEL` | No | `gpt-5` | Model for content generation (Agent 3) |
| `OPENAI_MODEL_MINI` | No | `gpt-5-mini` | Model for extraction/analysis (Agents 1 & 2) |
| `TAVILY_API_KEY` | Yes | — | Tavily web search API key |
| `CHROMA_PERSIST_DIR` | No | `./chroma_db` | ChromaDB storage directory |
| `LANGCHAIN_TRACING_V2` | No | `true` | Enable LangSmith tracing |
| `LANGCHAIN_PROJECT` | No | `cr8-prototype` | LangSmith project name |

To view traces, visit [smith.langchain.com](https://smith.langchain.com/) and look for the `cr8-prototype` project. Every LLM call is tagged with a descriptive `run_name` (e.g., `summarize_lecture.pdf`, `gap_analysis_Word2Vec`, `generate_Transformers`).

---

## Testing

### Running Tests

```bash
# All tests (verbose)
make test

# Specific test file
pytest backend/tests/test_file_parser.py -v

# Specific test
pytest backend/tests/test_chromadb_store.py::test_two_collections -v
```

### Test Suite

| Test File | Tests | What It Covers |
|-----------|-------|----------------|
| `test_file_parser.py` | 3 | PDF extraction, non-empty pages, multiple files |
| `test_chromadb_store.py` | 3 | Add/query, reset collections, collection isolation |
| `test_pdf_builder.py` | 1 | PDF generation, file validity, magic bytes |

**Test data**: Tests use Stanford CS224N lecture slides from `NLP_Course/CS224N_Downloads/Slides/`. The `conftest.py` provides fixtures for single-file and multi-file test scenarios, plus a temporary ChromaDB directory.

### Manual E2E Test

```bash
# Quick test (1 file, ~15 topics, ~30 min)
python -m backend.run_pipeline NLP_Course/CS224N_Downloads/Slides/01_Word_Vectors_I.pdf

# Medium test (3 files)
python -m backend.run_pipeline \
  NLP_Course/CS224N_Downloads/Slides/01_Word_Vectors_I.pdf \
  NLP_Course/CS224N_Downloads/Slides/08_Transformers.pdf \
  NLP_Course/CS224N_Downloads/Slides/09_Pretraining.pdf
```

Verify:
1. Pipeline completes without errors
2. PDF exists in `outputs/`
3. PDF has cover page, TOC, and chapters with industry context
4. LangSmith traces visible at [smith.langchain.com](https://smith.langchain.com/)

---

## Troubleshooting

### Common Issues

**`UnicodeEncodeError` in PDF generation**

fpdf2 uses Helvetica (latin-1 encoding). If GPT returns Unicode characters like smart quotes or em dashes, `_sanitize()` in `pdf_builder.py` handles the mapping. If you see a new character failing, add it to `_UNICODE_REPLACEMENTS`.

**`DuplicateIDError` in ChromaDB**

The research agent deduplicates document IDs using MD5 hashes. If you see this error, the deduplication logic in `agent_research.py` may need to be extended.

**ChromaDB `NotFoundError` on reset**

`reset_collections()` catches both `ValueError` and `NotFoundError` when deleting collections that don't exist. This is handled gracefully.

**Pipeline is slow (~30 min for 1 file)**

Most time is spent on API calls (OpenAI + Tavily). The research agent makes 2 web searches per topic and 1 LLM call per topic, all sequentially. Parallelization would significantly reduce runtime.

**`ModuleNotFoundError: No module named 'backend'`**

Make sure you installed in development mode: `pip install -e ".[dev]"` (or `make install`).

### Makefile Commands

| Command | Description |
|---------|-------------|
| `make install` | Install package in editable mode with dev deps |
| `make test` | Run pytest with verbose output |
| `make run ARGS="file.pdf"` | Run the pipeline |
| `make clean` | Remove `chroma_db/`, `outputs/`, caches |

---

## Future Work

This prototype proves the core concept: curriculum in, market-enriched learning guide out. Planned next steps (see `Docs/Prototype_plan.md` for full roadmap):

- **Flask API + React frontend** — File upload UI, progress indicator, PDF download
- **Performance** — Parallelize research agent (async per-topic), batch LLM calls
- **Prompt iteration** — Improve content quality based on manual PDF review
- **Video generation** — HeyGen API integration for AI-generated lecture videos
- **Adaptive assessment** — PPO + DKVMN hybrid for personalized learning paths (see `Docs/Technical_assessment.md`)

---

## Dependencies

Core:
- `langchain>=0.3` / `langchain-openai>=0.3` / `langgraph>=0.2` / `langsmith>=0.2`
- `chromadb>=0.5` — Vector store with local embeddings
- `pymupdf>=1.24` — PDF text extraction
- `python-pptx>=1.0` — PowerPoint text extraction
- `tavily-python>=0.5` — Web search API
- `fpdf2>=2.8` — PDF generation (pure Python, no system deps)
- `pydantic-settings>=2.0` — Environment configuration
- `langchain-text-splitters>=0.3` — Text chunking

Dev:
- `pytest>=8.0` — Test framework
- `ruff>=0.5` — Linter
