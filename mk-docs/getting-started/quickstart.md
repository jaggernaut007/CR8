# Quick Start

This guide walks you through running the CR8 pipeline on your first set of PDFs and inspecting the output.

## Running the Pipeline

Make sure you have completed [Installation](installation.md) and [Configuration](configuration.md) before proceeding.

### Single file

```bash
python -m backend.run_pipeline path/to/lecture.pdf
```

### Multiple files

```bash
python -m backend.run_pipeline slides/01.pdf slides/02.pdf slides/03.pdf
```

### Glob pattern

```bash
python -m backend.run_pipeline NLP_Course/CS224N_Downloads/Slides/*.pdf
```

## Checking Output

The output PDF is saved to `outputs/<timestamp>_learning_guide.pdf`.

Verify the output by checking that:

1. The pipeline completed without errors
2. A PDF exists in the `outputs/` directory
3. The PDF contains a cover page, table of contents, and chapters with industry context
4. LangSmith traces are visible at [smith.langchain.com](https://smith.langchain.com/) (if tracing is enabled)

## Running the Web UI

For a browser-based experience with drag-and-drop upload, real-time progress tracking, and download:

```bash
make dev
# Opens at http://localhost:8080
```

See [Web UI](web-ui.md) for full details.

## Running Tests

```bash
make test
```

## Makefile Commands

| Command | Description |
|---------|-------------|
| `make install` | Install package in editable mode with dev deps |
| `make test` | Run pytest with verbose output |
| `make run ARGS="file.pdf"` | Run the pipeline (CLI) |
| `make dev` | Start FastAPI web UI at http://localhost:8080 (hot-reload, all interfaces) |
| `make serve` | Start FastAPI web UI at http://localhost:8080 (hot-reload, localhost only) |
| `make docker-build` | Build Docker image locally |
| `make docker-run` | Run Docker container locally on port 8080 |
| `make clean` | Remove `chroma_db/`, `outputs/`, caches |

## Troubleshooting

### `UnicodeEncodeError` in PDF generation

fpdf2 uses Helvetica (latin-1 encoding). If GPT returns Unicode characters like smart quotes or em dashes, `_sanitize()` in `pdf_builder.py` handles the mapping. If you see a new character failing, add it to `_UNICODE_REPLACEMENTS` in `backend/services/pdf_builder.py`.

### `DuplicateIDError` in ChromaDB

The research agent deduplicates document IDs using MD5 hashes. If you see this error, the deduplication logic in `agent_research.py` may need to be extended.

### ChromaDB `PanicException` on startup (version mismatch)

If you see `pyo3_runtime.PanicException: range start index ... out of range`, the `chroma_db/` directory was created by an older ChromaDB version and is incompatible with the currently installed version. Fix:

```bash
make clean
```

This wipes the stale database. It gets rebuilt automatically on the next pipeline run.

### ChromaDB `NotFoundError` on reset

`reset_collections()` catches both `ValueError` and `NotFoundError` when deleting collections that don't exist. This is handled gracefully and requires no action.

### Pipeline is slow

Most time is spent on API calls (OpenAI + Tavily). All agents run their work in parallel via `ThreadPoolExecutor` (controlled by `MAX_WORKERS`, default 8), which significantly reduces wall-clock time compared to sequential execution. Adjust `MAX_WORKERS` in your `.env` to tune concurrency.

### `ModuleNotFoundError: No module named 'backend'`

Make sure you installed in development mode:

```bash
pip install -e ".[dev]"
```

Or equivalently:

```bash
make install
```
