# Frontend API Endpoints

The CR8 web UI is a FastAPI application serving a single-page HTML interface.

**File**: `frontend/app.py`

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serve the HTML UI |
| `/api/upload` | POST | Upload a PDF or PPTX, returns `{job_id, filename}` |
| `/api/start` | POST | Start pipeline for a job, returns `{status: running}` |
| `/api/progress/{job_id}` | GET | Poll progress: `{status, stage, percent, logs, elapsed, warnings}` |
| `/api/download/{job_id}/{type}` | GET | Download output files (pdf, scripts, videos) |

## Upload Flow

```
POST /api/upload
Content-Type: multipart/form-data

Body: file=<PDF or PPTX file>

Response: {"job_id": "abc123", "filename": "syllabus.pdf"}
```

The endpoint validates the uploaded file using magic bytes before saving:

- **PDF**: first 5 bytes must be `%PDF-`
- **PPTX**: first 4 bytes must be `PK\x03\x04` (ZIP header — all `.pptx` files are ZIP archives)

Any other file type is rejected with HTTP 400. The validated file is saved to a temporary directory keyed by `job_id`.

## Pipeline Execution

```
POST /api/start
Content-Type: application/json

Body: {"job_id": "abc123"}

Response: {"status": "running"}
```

The pipeline runs in a background thread. Progress is tracked via `ProgressCapture`. On start, the endpoint scans the job directory for both `.pdf` and `.pptx` files to locate the uploaded source file.

## Progress Polling

```
GET /api/progress/abc123

Response:
{
    "status": "running",
    "stage": "Research",
    "percent": 45,
    "logs": ["[Ingest] Extracting text...", "[Research] Searching web..."],
    "elapsed": 32.5,
    "warnings": []
}
```

The frontend polls this endpoint every 2 seconds to update the progress bar and log display. The `warnings` list accumulates any `[Video] ERROR:` or `[Video] WARNING:` lines captured during video generation. These are surfaced to the user as a yellow warning box below the download buttons on completion.

## ProgressCapture

The `ProgressCapture` class intercepts pipeline `print()` output and parses stage prefixes to compute progress percentage.

### Stage Weights

| Stage | Weight | Cumulative |
|-------|--------|------------|
| Upload & Validation | 0.02 | 2% |
| Ingest | 0.10 | 12% |
| Research | 0.18 | 30% |
| Module Generation | 0.20 | 50% |
| PPT Generation | 0.10 | 60% |
| Script Generation | 0.10 | 70% |
| PDF Build | 0.05 | 75% |
| PPT Build | 0.05 | 80% |
| Video Generation | 0.18 | 98% |
| Completion | 0.02 | 100% |

!!! warning "Video weight"
    The Video stage weight was increased from 2% to 18% (net 18% of total pipeline weight) to reflect the CPU time consumed by Kokoro TTS synthesis. The cumulative percentages above reflect this rebalancing.

### How It Works

1. `ProgressCapture` replaces `sys.stdout` with a custom writer
2. Each `print()` call is intercepted and parsed for stage prefixes (e.g., `[Research]`)
3. The stage prefix maps to a weight in the table above
4. Progress percentage is computed as the cumulative weight up to the current stage
5. Lines beginning with `[Video] ERROR:` or `[Video] WARNING:` are also collected into a separate `warnings` list
6. All captured output lines are stored in a thread-safe log buffer
7. The `/api/progress` endpoint reads from this buffer to return current state

## Download Endpoints

```
GET /api/download/abc123/pdf      # Download the learning module PDF
GET /api/download/abc123/scripts  # Download video scripts (ZIP)
GET /api/download/abc123/videos   # Download generated videos (ZIP)
```

Files are served from the output directory associated with the `job_id`. Returns 404 if the pipeline has not completed or the requested output type was not generated.
