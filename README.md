# CR8 — Adaptive Learning Pipeline

A 3-agent AI pipeline that transforms university curriculum materials into market-enriched learning guides. Feed in lecture PDFs, get out a structured PDF with industry context, gap analysis, and curated resources.

```
Curriculum PDFs  ──>  [Ingest]  ──>  [Research]  ──>  [Generate]  ──>  Learning Guide PDF
                      Agent 1        Agent 2          Agent 3         + PPT + Scripts + Videos
```

Built with LangGraph, OpenAI, ChromaDB, Tavily, fpdf2, and FastAPI.

**[Full Documentation](docs/index.md)** | **[Architecture](docs/architecture/index.md)** | **[API Reference](docs/api/index.md)**

---

## Quick Start

### Prerequisites

- Python 3.11+
- API keys: [OpenAI](https://platform.openai.com/), [Tavily](https://tavily.com/), [LangSmith](https://smith.langchain.com/) (optional)

### Install & Run

```bash
# Setup
python -m venv .venv && source .venv/bin/activate
make install

# Configure
cp .env.example .env   # Add your API keys

# Run the pipeline
python -m backend.run_pipeline path/to/lecture.pdf

# Or start the web UI
make dev   # http://localhost:8080
```

Output is saved to `outputs/<timestamp>/`.

### Run Tests

```bash
make test   # 144 tests (74 backend + 70 frontend)
```

---

## Key Features

- **3-agent pipeline** — Ingest, Research, Generate, orchestrated by LangGraph
- **Multi-model routing** — GPT-5-nano (extraction), GPT-5-mini (analysis), GPT-5.1 (generation) with severity-based routing
- **Chained outputs** — PDF → PPT → Scripts → Videos, each building on the previous
- **Vector-backed context** — ChromaDB stores curriculum and research for semantic retrieval
- **Web UI** — Upload PDFs, select formats, track progress in real time
- **Evaluation framework** — L1 structural checks (free) + L2 DeepSeek-V3 judge (~$0.02/run)

---

## Documentation

Full documentation lives in [`docs/`](docs/index.md):

| Section | Description |
|---------|-------------|
| [Getting Started](docs/getting-started/index.md) | Installation, quickstart, configuration, web UI |
| [Architecture](docs/architecture/index.md) | Pipeline design, data flow, model routing, output chain |
| [Agents](docs/agents/index.md) | Deep dive into Ingest, Research, and Generate agents |
| [Services](docs/services/index.md) | LLM wrapper, ChromaDB, PDF/PPT/Video builders |
| [Evaluation](docs/evals/index.md) | Two-layer eval system, CLI, prompt registry, A/B testing |
| [Deployment](docs/deployment/index.md) | Docker and GCP Cloud Run deployment |
| [Design Decisions](docs/design/index.md) | Research documents and architectural rationale |
| [API Reference](docs/api/index.md) | Auto-generated API documentation |
| [Contributing](docs/contributing/index.md) | Dev setup, testing, updating docs |

### Preview docs locally

```bash
pip install -e ".[docs]"
make docs-serve   # http://localhost:8000
```

---

## Makefile Commands

| Command | Description |
|---------|-------------|
| `make install` | Install package in editable mode with dev deps |
| `make test` | Run all tests |
| `make dev` | Start web UI (hot-reload) |
| `make run ARGS="file.pdf"` | Run pipeline via CLI |
| `make clean` | Remove chroma_db/, outputs/, caches |
| `make docs-serve` | Preview documentation site locally |
| `make docs-build` | Build documentation with strict checks |

---

## Project Structure

```
Software/
├── backend/
│   ├── config.py             # Pydantic-settings configuration
│   ├── run_pipeline.py       # CLI entry point
│   ├── pipeline/             # LangGraph agents (ingest, research, generate)
│   ├── services/             # LLM, ChromaDB, file parser, builders
│   ├── prompts/              # All prompt templates
│   ├── evals/                # Evaluation framework
│   └── tests/                # Backend tests
├── frontend/
│   ├── app.py                # FastAPI server
│   ├── templates/            # Web UI
│   └── tests/                # Frontend tests
├── docs/                     # Documentation (MkDocs + Material)
├── mkdocs.yml                # Documentation config
├── Makefile                  # Dev shortcuts
└── pyproject.toml            # Python project config
```
