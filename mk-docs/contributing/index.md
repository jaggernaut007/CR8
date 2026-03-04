# Contributing

## Development Setup

```bash
# Clone and install
git clone <repo-url>
cd Software
python -m venv .venv
source .venv/bin/activate
make install
```

## Running Tests

```bash
# All tests
make test

# Specific test file
pytest backend/tests/test_file_parser.py -v

# Specific test
pytest backend/tests/test_chromadb_store.py::test_two_collections -v
```

## Test Suite

**426 tests — 0 real API calls.** All LLMs, web search, and ChromaDB are mocked.

### Backend Tests

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `backend/tests/test_structural_checks.py` | 63 | All L1 structural check modules + `_sanitize` property-based tests |
| `backend/tests/test_eval_harness.py` | 28 | Comparator winner/regression math, scorer L1-only, syrupy snapshots, hypothesis property tests |
| `backend/tests/test_graph_integration.py` | 8 | LangGraph `build_pipeline()` compilation, node wiring, state propagation |
| `backend/tests/test_pipeline_agents.py` | 45 | `ingest_node`, `research_node`, `generate_node`, `_validate_module`, `_detect_hook_type`, `_sanitize` |
| `backend/tests/test_services.py` | 13 | `get_llm()` tier routing, `search()` with mocked Tavily, ChromaDB edge cases |
| `backend/tests/test_bug_fixes.py` | 21 | Regression suite for all March 2026 hardening fixes |
| `backend/tests/test_pdf_builder.py` | 20+ | PDF generation: Unicode, malformed markdown, code blocks, special chars |
| `backend/tests/test_chromadb_store.py` | 7 | Add/query, reset, isolation, custom IDs, metadata, empty collection, `n_results` limit |
| `backend/tests/test_file_parser.py` | 6 | PDF extraction, non-empty pages, multiple files, missing file, empty PDF, unsupported type |
| `backend/tests/test_run_pipeline.py` | 8 | `run_job()` validation and invocation |
| `backend/tests/test_video_builder.py` | 11 | URL guard, download helpers, Kokoro two-phase pipeline, shared engine, empty slide guard |

### Frontend Tests

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `frontend/tests/test_api.py` | 90 | All FastAPI endpoints: auth, upload (PDF + PPTX), start, progress, download; video UI |
| `frontend/tests/test_progress_capture.py` | 39 | Stage parsing, progress %age, thread safety, stage time budgets |

See the [Testing Guide](../testing/index.md) for full architecture details, shared fixtures, and how to add new tests.

## Code Style

The project uses [Ruff](https://docs.astral.sh/ruff/) for linting with a line length of 100:

```bash
ruff check backend/ frontend/
```

## Makefile Commands

| Command | Description |
|---------|-------------|
| `make install` | Install package with dev deps |
| `make test` | Run pytest with verbose output |
| `make run ARGS="file.pdf"` | Run the pipeline (CLI) |
| `make dev` | Start web UI (all interfaces, hot-reload) |
| `make serve` | Start web UI (localhost only, hot-reload) |
| `make docker-build` | Build Docker image |
| `make docker-run` | Run Docker container |
| `make clean` | Remove chroma_db/, outputs/, caches |
| `make docs-serve` | Preview documentation locally |
| `make docs-build` | Build documentation (strict mode) |
