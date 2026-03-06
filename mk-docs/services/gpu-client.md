# Video Service Client

HTTP client for CR8 Cloud Run video generation services (GPU and CPU-video).

## Module

::: backend.services.gpu_client

## Overview

`VideoServiceClient` communicates with remote video microservices to offload video generation (TTS + ffmpeg) away from the main pipeline container. It implements a **3-tier fallback chain** — trying each tier in sequence on infrastructure failures until a job is accepted.

```
Tier 1: GPU Primary   (europe-west4, NVIDIA L4)
Tier 2: GPU Fallback  (europe-west1, NVIDIA L4)
Tier 3: CPU Video     (europe-west2, 8 vCPU / 32 GiB)
```

`GPUVideoClient` is retained as a backward-compatible alias.

### Key Methods

| Method | Description |
|--------|-------------|
| `is_available()` | Health checks each tier in order; pins the client to the first healthy tier |
| `submit_job(job_id, gcs_prefix)` | POST to `/api/v1/video-jobs`, tries next tier on infrastructure errors |
| `poll_until_complete(video_job_id)` | Polls status on the pinned tier, emits `[Video] GPU:` progress lines |
| `cancel_job(video_job_id)` | POST to cancel a running job on the current tier |

### Fallback Trigger Rules

Fallback to the next tier is triggered by **infrastructure failures only**:

- `requests.ConnectionError` — service unreachable
- `requests.Timeout` — service did not respond in time
- `requests.HTTPError` — 5xx response from the service

Job-level errors (4xx responses, worker errors reported in the job status) do **not** trigger fallback. Once a tier accepts a job (`submit_job` succeeds), all subsequent polling stays on that tier.

### Authentication

Uses Cloud Run identity tokens (OIDC) for service-to-service auth. Tokens are fetched via `google-auth` and cached. Falls back gracefully when running outside GCP (local dev).

### Progress Lines

`poll_until_complete` prints structured lines so the CPU-side `ProgressCapture` can track video-stage progress:

```
[Video] GPU: tts (42%)
[Video] GPU_TTS: 2/5
[Video] GPU_COMPOSE: 1/5
[Video] GPU_TIME: elapsed=120 eta=280
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `GPU_SERVICE_URL` | *(empty)* | GPU primary service URL (europe-west4) |
| `GPU_FALLBACK_URL` | *(empty)* | GPU fallback service URL (europe-west1) |
| `CPU_VIDEO_SERVICE_URL` | *(empty)* | CPU-only video service URL (europe-west2) |
| `GCS_BUCKET` | `cr8-jobs` | Shared GCS bucket for data transfer |

The `should_use_video_service` property on `Settings` returns `True` when any of `GPU_SERVICE_URL` or `CPU_VIDEO_SERVICE_URL` is set. The pipeline checks this property to decide whether to route video jobs remotely or run Kokoro locally.

!!! warning "Fallback is for infrastructure failures only"
    If the GPU service reports a job-level error (e.g. Kokoro model loading failed), the pipeline raises `RuntimeError` and does not retry on a lower tier. Tier fallback only covers service-unreachable scenarios.
