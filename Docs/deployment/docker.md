# Docker

CR8 uses a multi-stage Docker build for efficient containerization. The resulting image is optimized for deployment on GCP Cloud Run but can also be used for local development and testing.

## Dockerfile Overview

The Dockerfile uses a **multi-stage build** based on `python:3.11-slim`:

```
Stage 1: Builder
├── Install build dependencies (gcc, etc.)
├── Copy requirements and install Python packages
└── Build wheels for all dependencies

Stage 2: Runtime
├── Copy wheels from builder stage
├── Install runtime-only system deps
├── Copy application source code
├── Set up non-root user
└── Configure Gunicorn + Uvicorn entrypoint
```

### Key Design Decisions

- **`python:3.11-slim`** base image keeps the final image small (~500MB vs ~1.2GB for full Python images)
- **Multi-stage build** separates build tools from runtime, reducing attack surface and image size
- **Non-root user** for security best practices
- **Gunicorn with Uvicorn workers** for production-grade async request handling

## Build Locally

```bash
make docker-build
```

This runs:

```bash
docker build -t cr8-pipeline .
```

## Run Locally

```bash
make docker-run
```

This runs:

```bash
docker run --rm -p 8080:8080 --env-file .env cr8-pipeline
```

The application will be available at **http://localhost:8080**.

!!! note
    Make sure your `.env` file contains all required API keys before running. See the [Configuration guide](../getting-started/configuration.md) for the full list of environment variables.

## Environment Variables

All environment variables are passed to the container via `--env-file .env`. The container does not bake any secrets into the image.

Required variables:

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key for GPT models |
| `TAVILY_API_KEY` | Tavily API key for web search |
| `HEYGEN_API_KEY` | HeyGen API key for video generation |

Optional variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8080` | Port the server listens on |
| `WORKERS` | `1` | Number of Gunicorn workers |
| `LOG_LEVEL` | `info` | Logging level |

## Cloud Run Settings

When deploying to GCP Cloud Run, the following settings are recommended:

| Setting | Value | Reason |
|---------|-------|--------|
| **Memory** | 2 GiB | ChromaDB and LLM response buffering require significant memory |
| **CPU** | 2 | Pipeline runs multiple concurrent API calls |
| **Request timeout** | 3600s (1 hour) | Full pipeline execution can take 10-30 minutes |
| **Min instances** | 0 | Scale to zero when idle to minimize cost |
| **Max instances** | 1 | Pipeline is not designed for concurrent multi-user execution |
| **Concurrency** | 1 | One pipeline run at a time per instance |

!!! warning
    Setting max instances above 1 is not recommended. ChromaDB uses ephemeral in-memory storage within each container, so multiple instances would not share state. The pipeline is designed for single-user execution.

## Troubleshooting

### Container exits immediately

Check that all required environment variables are set in your `.env` file:

```bash
docker run --rm --env-file .env cr8-pipeline env | grep -E "(OPENAI|TAVILY|HEYGEN)"
```

### Out of memory

If the container is killed with OOM errors, increase the memory limit:

```bash
docker run --rm -p 8080:8080 --env-file .env --memory=4g cr8-pipeline
```

### Port already in use

If port 8080 is occupied, map to a different host port:

```bash
docker run --rm -p 9090:8080 --env-file .env cr8-pipeline
```

Then access the application at http://localhost:9090.
