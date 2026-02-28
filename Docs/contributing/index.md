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

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `backend/tests/test_file_parser.py` | 3 | PDF extraction, non-empty pages, multiple files |
| `backend/tests/test_chromadb_store.py` | 3 | Add/query, reset, collection isolation |
| `backend/tests/test_pdf_builder.py` | 20+ | PDF generation, Unicode, edge cases |
| `backend/tests/test_run_pipeline.py` | 10 | Input validation, format checking, pipeline invocation |
| `frontend/tests/test_api.py` | 28 | All FastAPI endpoints |
| `frontend/tests/test_progress_capture.py` | 32 | Progress parsing, stage transitions, thread safety |

**Total: 144 tests** (74 backend + 70 frontend)

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
