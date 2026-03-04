# Deployment

CR8 deploys as a **dual-service architecture**: a CPU service for the pipeline and an optional GPU service for video rendering. This section covers local Docker usage and production deployment to GCP Cloud Run.

- **[Docker](docker.md)** -- Build and run locally with Docker (CPU + GPU images)
- **[GCP Cloud Run](gcp-cloud-run.md)** -- Production deployment to Google Cloud

## Architecture

``` mermaid
graph TB
    User[Browser] -->|HTTPS| CPU[CPU Service<br/>europe-west2]
    CPU -->|env vars| SM[Secret Manager]
    CPU -->|API calls| OAI[OpenAI API]
    CPU -->|API calls| TAV[Tavily API]
    CPU -->|slide PNGs| GCS[(GCS Bucket<br/>cr8-jobs)]
    GPU[GPU Service<br/>europe-west1/west4<br/>NVIDIA L4] -->|download slides| GCS
    GPU -->|upload MP4s| GCS
    CPU -->|POST /api/v1/video-jobs| GPU
    CPU -->|poll status| GPU
    CPU -->|download MP4s| GCS
    subgraph CPU Service
        GU[Gunicorn + Uvicorn] --> FA[FastAPI App]
        FA --> PL[Pipeline Thread]
        PL --> CDB[(ChromaDB ephemeral)]
    end
    subgraph GPU Service
        UV[Uvicorn] --> GA[FastAPI GPU App]
        GA --> WK[Video Worker]
        WK --> TTS[Kokoro TTS]
        WK --> FF[ffmpeg NVENC]
    end
```

!!! note
    The GPU service is optional. When `GPU_SERVICE_URL` is not set, video rendering runs locally on the CPU service using Kokoro TTS + software ffmpeg encoding.

## Quick Reference

| Task | Command |
|------|---------|
| Build CPU Docker image | `make docker-build` |
| Build GPU Docker image | `docker build -f Dockerfile.gpu -t cr8-gpu-service .` |
| Run locally in Docker | `make docker-run` |
| Deploy to Cloud Run | `./deploy.sh PROJECT_ID` (deploys both services) |
| Deploy details | See [GCP Cloud Run guide](gcp-cloud-run.md) |

## Requirements

- Docker 20.10+ (for local builds)
- GCP account with Cloud Run enabled (for production)
- GCS bucket for CPU↔GPU data transfer (production video rendering)
- All API keys configured in `.env` or GCP Secret Manager
