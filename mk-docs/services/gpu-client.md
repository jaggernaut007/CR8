# GPU Client

HTTP client for the CR8 Cloud Run GPU video generation service.

## Module

::: backend.services.gpu_client

## Overview

The `GPUVideoClient` communicates with the GPU microservice to offload video generation (TTS + ffmpeg) to an NVIDIA L4 GPU on Cloud Run. Includes automatic failover to a fallback GPU region.

### Key Methods

| Method | Description |
|--------|-------------|
| `is_available()` | Health check against GPU service `/health` endpoint |
| `submit_job(job_id, gcs_prefix)` | POST to `/api/v1/video-jobs`, returns `video_job_id` |
| `poll_until_complete(video_job_id)` | Polls status, emits `[Video] GPU:` progress lines |
| `cancel_job(video_job_id)` | POST to cancel a running job |

### Authentication

Uses Cloud Run identity tokens (OIDC) for service-to-service auth. Tokens are fetched via `google-auth` and cached. Falls back gracefully when running outside GCP (local dev).

### Failover

If the primary GPU service (`GPU_SERVICE_URL`) is unavailable, the client automatically tries the fallback (`GPU_FALLBACK_URL`). If both GPU services fail, the pipeline falls back to local CPU video generation.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `GPU_SERVICE_URL` | *(empty)* | Primary GPU service URL |
| `GPU_FALLBACK_URL` | *(empty)* | Fallback GPU service URL |
| `GCS_BUCKET` | `cr8-jobs` | Shared GCS bucket for data transfer |
