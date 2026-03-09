# Contributing

## Development Setup

```bash
# Clone and install (requires uv — https://docs.astral.sh/uv/)
git clone <repo-url>
cd CR8
make install    # runs uv sync --all-extras
```

## Running Tests

```bash
# All tests
make test

# Specific test file
uv run pytest backend/tests/test_file_parser.py -v

# Specific test
uv run pytest backend/tests/test_chromadb_store.py::test_two_collections -v
```

## Test Suite

**628 tests — 0 real API calls.** All LLMs, web search, and ChromaDB are mocked.

### Backend Tests

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `backend/tests/test_structural_checks.py` | 72 | All L1 structural check modules + `_sanitize` property-based tests |
| `backend/tests/test_pdf_builder.py` | 66 | PDF generation: Unicode, malformed markdown, code blocks, special chars |
| `backend/tests/test_pipeline_agents.py` | 40 | `ingest_node`, `research_node`, `generate_node`, `_validate_module`, `_detect_hook_type`, `_sanitize` |
| `backend/tests/test_gpu_client.py` | 37 | GPU client dispatch, fallback chain, polling, GCS transfer |
| `backend/tests/test_eval_harness.py` | 27 | Comparator winner/regression math, scorer L1-only, syrupy snapshots, hypothesis property tests |
| `backend/tests/test_video_builder.py` | 27 | URL guard, download helpers, Kokoro two-phase pipeline, shared engine, empty slide guard |
| `backend/tests/test_bug_fixes.py` | 20 | Regression suite for March 2026 hardening fixes |
| `backend/tests/test_script_parser.py` | 19 | Script segment parsing, `[SLIDE N]` marker handling |
| `backend/tests/test_db_client.py` | 19 | Async CRUD: user, job, quiz tables; pool lifecycle |
| `backend/tests/test_services.py` | 13 | `get_llm()` tier routing, `search()` with mocked Tavily, ChromaDB edge cases |
| `backend/tests/test_file_parser.py` | 13 | PDF extraction, non-empty pages, multiple files, missing file, empty PDF, unsupported type, slide export |
| `backend/tests/test_gpu_utils.py` | 12 | `get_torch_device()` detection, `get_ffmpeg_encoder()` probing |
| `backend/tests/test_auth_service.py` | 12 | JWT token creation/verification, bcrypt hashing, token type enforcement |
| `backend/tests/test_run_pipeline.py` | 11 | `run_job()` validation and invocation |
| `backend/tests/test_tts_engine.py` | 10 | Kokoro TTS wrapper, GPU device selection, lazy KPipeline init |
| `backend/tests/test_graph_integration.py` | 8 | LangGraph `build_pipeline()` compilation, node wiring, state propagation |
| `backend/tests/test_gcs_client.py` | 8 | GCS upload/download, bucket operations |
| `backend/tests/test_chromadb_store.py` | 7 | Add/query, reset, isolation, custom IDs, metadata, empty collection, `n_results` limit |

### Frontend Tests

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `frontend/tests/test_api.py` | 65 | Core FastAPI endpoints: upload (PDF + PPTX), start, progress, cancel, download; video UI |
| `frontend/tests/test_progress_capture.py` | 55 | Stage parsing, progress %age, thread safety, stage time budgets, GPU progress lines |
| `frontend/tests/test_auth_routes.py` | 48 | JWT register/login/refresh/me/logout; legacy session login; rate limiting; dual-auth |
| `frontend/tests/test_quiz_routes.py` | 24 | Quiz API routes: generate, fetch, submit, results, by-job; Pydantic model validation; route helpers |

See the [Testing Guide](../testing/index.md) for full architecture details, shared fixtures, and how to add new tests.

## Code Style & Quality

The project uses [Ruff](https://docs.astral.sh/ruff/) for linting with 12 rule categories beyond the defaults. See the full [Code Quality Guide](code-quality.md) for details.

```bash
# Check for violations
uv run ruff check .

# Auto-fix safe violations
uv run ruff check . --fix

# Check specific category
uv run ruff check . --select PLR --statistics
```

**Key constraints enforced by Ruff:**

- Max **25 statements** per function (PLR0915)
- Max **5 arguments** per function (PLR0913)
- Max **cyclomatic complexity 10** (C901)
- No `print()` in production code (T20) — use `logging`
- No f-strings in log calls (G) — use lazy `%s` formatting
- No commented-out code (ERA001)
- No mutable default arguments (B006)
- No builtin shadowing (A) — never name variables `list`, `dict`, `type`, `id`
- Modern Python syntax required (UP) — `dict` not `typing.Dict`

## Makefile Commands

| Command | Description |
|---------|-------------|
| `make install` | Install all deps via `uv sync --all-extras` |
| `make test` | Run pytest with verbose output |
| `make run ARGS="file.pdf"` | Run the pipeline (CLI) |
| `make dev` | Start web UI (all interfaces, hot-reload) |
| `make serve` | Start web UI (localhost only, hot-reload) |
| `make docker-build` | Build Docker image |
| `make docker-run` | Run Docker container |
| `make clean` | Remove chroma_db/, outputs/, caches |
| `make docs-serve` | Preview documentation locally |
| `make docs-build` | Build documentation (strict mode) |
