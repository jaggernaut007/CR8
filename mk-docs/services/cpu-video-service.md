# CPU Video Service

Standalone FastAPI microservice that runs Kokoro TTS + ffmpeg video composition on CPU only. Deployed to Cloud Run as the Tier 3 fallback in the 3-tier video service chain.

## Overview

The CPU video service provides the same HTTP API as the GPU service (`gpu_service/`) but targets CPU-only hardware. It is deployed with 8 vCPU / 32 GiB RAM on Cloud Run (europe-west2) — enough RAM to run Kokoro TTS sequentially and compose videos in parallel with `libx264`.

```
Tier 1: GPU Primary   (europe-west4, NVIDIA L4)
Tier 2: GPU Fallback  (europe-west1, NVIDIA L4)
Tier 3: CPU Video     (europe-west2, 8 vCPU / 32 GiB)  ← this service
```

`VideoServiceClient` in `backend/services/gpu_client.py` routes to this service automatically when both GPU tiers are unreachable on infrastructure errors.

## Package Layout

| File | Purpose |
|------|---------|
| `cpu_video_service/app.py` | FastAPI app — routes and request/response models |
| `cpu_video_service/worker.py` | Background worker — 4-phase pipeline logic |
| `cpu_video_service/gcs_client.py` | GCS operations scoped to this service |
| `cpu_video_service/config.py` | Pydantic settings loaded from environment |

## API Endpoints

All endpoints mirror the GPU service contract so `VideoServiceClient` can route to either tier transparently.

### `GET /health`

Lightweight health check for Cloud Run startup probe. Returns `{"status": "ok", "type": "cpu-video"}`.

### `POST /api/v1/video-jobs`

Accept a video generation job. Runs in a background thread.

**Request body:**
```json
{
  "job_id": "abc123",
  "gcs_prefix": "gs://cr8-jobs/abc123"
}
```

**Response (HTTP 202):**
```json
{
  "video_job_id": "vj_abc123_a1b2c3",
  "status": "accepted"
}
```

Returns HTTP 429 when the concurrency limit (`MAX_CONCURRENT_JOBS`) is reached.

### `GET /api/v1/video-jobs/{video_job_id}`

Poll the current status and progress of a running job.

**Response fields:**
| Field | Type | Description |
|-------|------|-------------|
| `video_job_id` | str | Job identifier |
| `status` | str | `accepted` / `downloading` / `tts` / `composing` / `uploading` / `complete` / `error` / `cancelled` / `cancelling` |
| `progress.phase` | str | Current pipeline phase |
| `progress.percent` | int | 0–100 completion estimate |
| `progress.current_topic` | int | TTS phase — topic index in progress |
| `progress.total_topics` | int | TTS phase — total topic count |
| `progress.completed_videos` | int | Compose phase — videos finished |
| `progress.total_videos` | int | Compose phase — total to compose |
| `progress.elapsed_s` | int | Seconds since job started |
| `progress.eta_s` | int | Estimated seconds remaining |
| `output_paths` | list[str] | MP4 filenames on completion |
| `warnings` | list[str] | Per-topic errors that did not fail the whole job |
| `error` | str | Error message when status is `error` |

### `POST /api/v1/video-jobs/{video_job_id}/cancel`

Cancel a running job. Cancellation takes effect at the next phase boundary (between TTS topics, or between compose workers). Returns HTTP 409 if the job cannot be cancelled.

## Worker Pipeline

The background worker executes four phases inside a temporary directory:

```
Phase 1: Download   — manifest.json + slide PNGs from GCS
Phase 2: TTS        — Kokoro on CPU, sequential per topic
Phase 3: Compose    — ffmpeg libx264, parallel across topics
Phase 4: Upload     — MP4s + final status JSON to GCS
```

Progress updates are written to the in-memory job store after each topic in the TTS phase and after each video in the compose phase.

### CPU vs GPU differences

| Aspect | GPU service | CPU video service |
|--------|------------|-------------------|
| TTS device | CUDA / auto | CPU (forced via `VIDEO_DEVICE=cpu`) |
| Video encoder | `h264_nvenc` (NVENC) | `libx264` (software) |
| Deployment | europe-west4, 4 vCPU, 16 GiB | europe-west2, 8 vCPU, 32 GiB |
| Expected throughput | ~2-3 min per 5-topic job | ~20-30 min per 5-topic job |

The CPU service uses more vCPUs to partially compensate for the lack of hardware acceleration and to run more compose workers in parallel.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `CPU_VIDEO_SERVICE_URL` | *(empty)* | Set on the main pipeline service to route Tier 3 traffic here |
| `GCS_BUCKET` | `cr8-jobs` | Shared GCS bucket (same as GPU service) |
| `KOKORO_VOICE` | `af_heart` | Kokoro voice identifier |
| `KOKORO_LANG` | `a` | Kokoro language code |
| `VIDEO_FPS` | `5` | Output frame rate |
| `VIDEO_MAX_WORKERS` | `4` | Parallel compose workers (lower than GPU: fewer hardware threads) |
| `MAX_CONCURRENT_JOBS` | `1` | Max simultaneous jobs (RAM is the limiting factor) |

## Container

Built from `Dockerfile.cpu-video` (2-stage build). Includes `ffmpeg`, `espeak-ng`, and `libreoffice-impress`. Does not include CUDA dependencies.

## Tests

| File | Tests | What it covers |
|------|-------|----------------|
| `cpu_video_service/tests/test_app.py` | 19 | FastAPI endpoints: `/health`, POST/GET/cancel video-jobs, concurrency limit |
| `cpu_video_service/tests/test_worker.py` | 37 | Full job lifecycle, cancellation flow, ETA estimation, error handling |
| `cpu_video_service/tests/test_gcs_client.py` | 22 | `download_manifest()`, `download_slides()`, `upload_videos()`, `upload_status()` |
