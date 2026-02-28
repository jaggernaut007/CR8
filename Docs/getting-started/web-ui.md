# Web UI

A minimal FastAPI web interface for uploading PDFs, selecting output formats, monitoring progress in real time, and downloading generated files.

## Starting the Server

```bash
make dev
# Opens at http://localhost:8080
```

The UI is a single-page HTML file with inline CSS and vanilla JS -- no build step required.

## Features

- **PDF upload** -- drag-and-drop or file picker
- **Format selection** -- PDF (always on), PPT (optional gap analysis slides), Script (optional, auto-enables PPT), Video (disabled by default, requires HeyGen API keys, auto-enables Script + PPT)
- **Real-time progress** -- stage label, progress bar, elapsed/estimated time, scrolling log area
- **Download** -- PDF as direct download, scripts and videos as .zip files

## Architecture

The web UI follows a simple async pattern: the browser polls for progress while the pipeline runs in a background thread.

```
Browser (JS fetch)     FastAPI (async uvicorn)      Pipeline Thread
    |                        |                            |
    |-- POST /api/upload --->|  save PDF to uploads/      |
    |<-- { job_id } ---------|                            |
    |                        |                            |
    |-- POST /api/start ---->|  asyncio.create_task()     |
    |                        |    +-- asyncio.to_thread()-->|
    |<-- {status: running} --|         run_job()          |
    |                        |                            |-- ThreadPoolExecutor(8)
    |-- GET /api/progress -->|                            |   (parallel topics)
    |<-- {stage, pct, logs} -|  reads ProgressCapture     |
    |   (poll every 3s)      |                            |
    |                        |<--- result dict -----------|
    |-- GET /api/progress -->|                            |
    |<-- {complete, files} --|                            |
    |                        |                            |
    |-- GET /api/download -->|                            |
    |<-- file bytes ---------|                            |
```

1. The browser uploads a PDF via `POST /api/upload`, receiving a `job_id`.
2. `POST /api/start` launches the pipeline in a background thread using `asyncio.to_thread()`.
3. The browser polls `GET /api/progress/{job_id}` every 3 seconds to get the current stage, percentage, and log output.
4. When the pipeline completes, the progress response includes the list of downloadable files.
5. The browser requests files via `GET /api/download/{job_id}/{type}`.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serve the HTML UI |
| `/api/upload` | POST | Upload a PDF, returns `{job_id, filename}` |
| `/api/start` | POST | Start pipeline for a job, returns `{status: running}` |
| `/api/progress/{job_id}` | GET | Poll progress: `{status, stage, percent, logs, elapsed}` |
| `/api/download/{job_id}/{type}` | GET | Download output files (pdf, scripts, videos) |

## Progress Tracking

The `ProgressCapture` class (defined in `frontend/app.py`) intercepts pipeline `print()` output and parses stage prefixes (`[Ingest]`, `[Research]`, `[Generate]`, `[Script]`, `[Video]`) to compute an overall progress percentage using stage weights:

| Stage | Weight | Cumulative |
|-------|--------|------------|
| Ingest | 15% | 0--15% |
| Research | 50% | 15--65% |
| Generate | 25% | 65--90% |
| Script | 8% | 90--98% |
| Video | 2% | 98--100% |

Sub-step progress (`Topic X/Y`, `Module X/Y`) is interpolated within each stage for smooth progress bar updates. For example, if the Research agent is on topic 8 of 15, the progress bar shows approximately `15% + (8/15 * 50%) = 41.7%`.
