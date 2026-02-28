# Deployment

CR8 deploys as a single Docker container. This section covers local Docker usage and production deployment to GCP Cloud Run.

- **[Docker](docker.md)** -- Build and run locally with Docker
- **[GCP Cloud Run](gcp-cloud-run.md)** -- Production deployment to Google Cloud

## Architecture

``` mermaid
graph TB
    User[Browser] -->|HTTPS| CR[GCP Cloud Run]
    CR -->|env vars| SM[Secret Manager]
    CR -->|API calls| OAI[OpenAI API]
    CR -->|API calls| TAV[Tavily API]
    CR -->|API calls| HG[HeyGen API]
    subgraph Cloud Run Container
        GU[Gunicorn + Uvicorn] --> FA[FastAPI App]
        FA --> PL[Pipeline Thread]
        PL --> CDB[(ChromaDB ephemeral)]
    end
```

## Quick Reference

| Task | Command |
|------|---------|
| Build Docker image | `make docker-build` |
| Run locally in Docker | `make docker-run` |
| Deploy to Cloud Run | See [GCP Cloud Run guide](gcp-cloud-run.md) |

## Requirements

- Docker 20.10+ (for local builds)
- GCP account with Cloud Run enabled (for production)
- All API keys configured in `.env` or GCP Secret Manager
