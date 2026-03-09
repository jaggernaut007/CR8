# Technology Stack

## Component Overview

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Pipeline orchestration | LangGraph | State machine for agent coordination |
| LLM (extraction) | OpenAI GPT-5-nano / GPT-5-mini (tiered) | Nano for summarization/extraction, mini for gap analysis |
| LLM (generation) | OpenAI GPT-5.1 / GPT-5-mini (severity-routed) | Premium for critical topics + scripts, mini for moderate/minor |
| Vector store | ChromaDB | Semantic search over curriculum and research |
| Embeddings | all-MiniLM-L6-v2 | ChromaDB default, local, free |
| Web search | Tavily API | Industry trends and job requirements |
| PDF text extraction | PyMuPDF (fitz) | Extract text from PDF files |
| Slide extraction | python-pptx | Extract text from PowerPoint files |
| PDF generation | fpdf2 | Compile learning guide PDF |
| PPT generation | python-pptx | Generate gap analysis PowerPoint slides |
| Video generation | HeyGen API v2 | AI avatar video rendering from scripts |
| Web framework | FastAPI + uvicorn | Async HTTP server, API layer, SPA host |
| React SPA | React 19 + Vite 7 | Client-side single-page application |
| UI styling | Tailwind v4 | Utility-first CSS with glassmorphism design |
| Client state | Tanstack Query | Server-state caching, polling, and mutations |
| Client routing | React Router v7 | Client-side navigation with protected routes |
| Concurrency | ThreadPoolExecutor | Parallel agent execution (configurable `max_workers`) |
| Configuration | pydantic-settings | Type-safe env loading |
| Observability | LangSmith | Trace every LLM call |

## Key Design Choices

### LangGraph over raw LangChain

LangGraph provides a `StateGraph` abstraction that makes the pipeline's control flow explicit. Each agent is a node, edges define execution order, and state is a typed dict that accumulates data. This is simpler and more debuggable than chaining LangChain runnables, and it integrates natively with LangSmith for per-node tracing.

### ChromaDB with Local Embeddings

ChromaDB's built-in `all-MiniLM-L6-v2` embedding model runs locally with no API calls. This keeps vector operations free, fast, and offline-capable. The trade-off is embedding quality -- a hosted model like OpenAI's `text-embedding-3-small` would produce better similarity scores, but the local model is sufficient for the curriculum-scale retrieval in this pipeline.

ChromaDB persists to disk at `./chroma_db/`, so the vector store survives between runs. This is useful when regenerating outputs without re-ingesting source files.

### fpdf2 for PDF Generation

fpdf2 is a pure-Python PDF library with no system dependencies (no wkhtmltopdf, no LaTeX). This makes it trivial to deploy in containers. The trade-off is limited font support -- fpdf2 uses Helvetica (latin-1 encoding), so a `_sanitize()` function maps 20+ common Unicode characters (smart quotes, em dashes, bullets) to ASCII equivalents.

### Tavily for Web Search

Tavily is a search API designed for LLM applications. It returns clean, structured results with relevance scores, which is more useful than raw Google results. The `search_depth="basic"` setting is fast and sufficient for identifying industry trends and job requirements.

### 3-Tier Model System

Instead of using a single model for all tasks, CR8 routes tasks to three model tiers (nano, mini, premium) based on the complexity and quality requirements of each task. This balances cost, speed, and output quality. See [Multi-Model Routing](model-routing.md) for details.

## Dependencies

### Core

| Package | Version | Role |
|---------|---------|------|
| `langchain` | >=0.3 | LLM framework |
| `langchain-openai` | >=0.3 | OpenAI integration |
| `langgraph` | >=0.2 | Pipeline state graph |
| `langsmith` | >=0.2 | Observability/tracing |
| `chromadb` | >=0.5 | Vector store with local embeddings |
| `pymupdf` | >=1.24 | PDF text extraction |
| `python-pptx` | >=1.0 | PowerPoint extraction and generation |
| `tavily-python` | >=0.5 | Web search API |
| `fpdf2` | >=2.8 | PDF generation (pure Python) |
| `pydantic-settings` | >=2.0 | Environment configuration |
| `langchain-text-splitters` | >=0.3 | Text chunking |
| `fastapi` | >=0.115 | Async web framework |
| `uvicorn[standard]` | >=0.34 | ASGI server |
| `python-multipart` | >=0.0.9 | File upload handling |
| `gunicorn` | >=22.0 | Production ASGI server |

### Dev

| Package | Version | Role |
|---------|---------|------|
| `pytest` | >=8.0 | Test framework |
| `ruff` | >=0.5 | Linter |
| `httpx` | >=0.27 | Required by FastAPI TestClient |

### Eval (optional)

Install with `pip install -e ".[eval]"`:

| Package | Version | Role |
|---------|---------|------|
| `click` | >=8.1 | CLI framework for eval commands |
| `scipy` | >=1.11 | Statistical tests (paired t-test for A/B) |
| `tabulate` | >=0.9 | Table formatting for eval reports |
