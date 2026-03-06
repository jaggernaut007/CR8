# Installation

## Prerequisites

- Python 3.11 or higher
- API keys for: [OpenAI](https://platform.openai.com/), [Tavily](https://tavily.com/)
- Optional: [LangSmith](https://smith.langchain.com/) for tracing (recommended for debugging and observability)

## Setup

```bash
# Clone the repository and navigate to the project root
cd CR8-edtech

# Install uv (Astral package manager) if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install all dependencies (creates .venv automatically)
make install
```

`make install` runs `uv sync --all-extras`, which installs the package and all core + dev + eval + docs dependencies.

## Dependencies

### Core

| Package | Version | Purpose |
|---------|---------|---------|
| `langchain` | >=0.3 | LLM orchestration framework |
| `langchain-openai` | >=0.3 | OpenAI integration for LangChain |
| `langgraph` | >=0.2 | State graph pipeline orchestration |
| `langsmith` | >=0.2 | LLM observability and tracing |
| `chromadb` | >=0.5 | Vector store with local embeddings |
| `pymupdf` | >=1.24 | PDF text extraction |
| `python-pptx` | >=1.0 | PowerPoint extraction and generation |
| `tavily-python` | >=0.5 | Web search API |
| `fpdf2` | >=2.8 | PDF generation (pure Python, no system deps) |
| `pydantic-settings` | >=2.0 | Environment configuration |
| `langchain-text-splitters` | >=0.3 | Text chunking |
| `fastapi` | >=0.115 | Async web framework |
| `uvicorn[standard]` | >=0.34 | ASGI server |
| `python-multipart` | >=0.0.9 | File upload handling |
| `gunicorn` | >=22.0 | Production WSGI/ASGI server |
| `matplotlib` | >=3.8 | Plotting support |
| `python-dotenv` | >=1.0 | .env file loading |
| `jinja2` | >=3.1 | Template rendering |
| `markdown` | >=3.6 | Markdown processing |
| `requests` | >=2.31 | HTTP client |

### Dev

Installed automatically with `make install` (via the `[dev]` extra):

| Package | Version | Purpose |
|---------|---------|---------|
| `pytest` | >=8.0 | Test framework |
| `ruff` | >=0.5 | Linter and formatter |
| `httpx` | >=0.27 | Async HTTP client (required by FastAPI TestClient) |

### Eval (optional)

Included automatically with `make install` (`uv sync --all-extras`).

| Package | Version | Purpose |
|---------|---------|---------|
| `click` | >=8.1 | CLI framework for eval commands |
| `scipy` | >=1.11 | Statistical tests (paired t-test for A/B comparisons) |
| `tabulate` | >=0.9 | Table formatting for eval reports |

### Docs (optional)

Included automatically with `make install` (`uv sync --all-extras`).

| Package | Purpose |
|---------|---------|
| `mkdocs` | Static site generator for documentation |
| `mkdocs-material` | Material theme for MkDocs |
| `mkdocstrings` | Auto-generate API docs from docstrings |
