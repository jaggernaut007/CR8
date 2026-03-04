# Deployment Guide — GCP Cloud Run

Step-by-step guide to deploying the CR8 Learning Pipeline on Google Cloud Run.

---

## Architecture

```
                    ┌─────────────────────────────────────┐
                    │         GCP Cloud Run                │
                    │                                      │
User ──HTTPS──>     │  Gunicorn + Uvicorn (1 worker)      │
                    │    └── FastAPI app                   │
                    │         ├── /health                  │
                    │         ├── /api/upload              │
                    │         ├── /api/start ──> Pipeline  │──> OpenAI API
                    │         ├── /api/progress            │──> Tavily API
                    │         └── /api/download            │──> HeyGen API (optional)
                    │                                      │
                    │  ChromaDB (ephemeral on disk)        │
                    │  uploads/ & outputs/ (ephemeral)     │
                    │                                      │
                    └──────────────┬───────────────────────┘
                                   │
                         GCP Secret Manager
                         (OPENAI_API_KEY, TAVILY_API_KEY)
```

**Key design decisions:**
- Single instance (`max-instances=1`) — the app enforces one job at a time
- Scale to zero (`min-instances=0`) — near-zero cost when idle, ~30-60s cold start
- CPU always allocated (`--no-cpu-throttling`) — background pipeline threads need CPU between requests
- Ephemeral storage — ChromaDB rebuilds every job; users download outputs immediately

---

## Prerequisites

1. **Google Cloud account** with billing enabled
2. **gcloud CLI** — [Install guide](https://cloud.google.com/sdk/docs/install)
3. **Docker** — installed and running
4. **API keys** ready:
   - OpenAI API key (`sk-...`)
   - Tavily API key (`tvly-...`)
   - HeyGen API key (optional, for video generation)

---

## Step 1: GCP Project Setup

Run the one-time setup script:

```bash
./deploy.sh --setup YOUR_PROJECT_ID
```

This enables the required GCP APIs and creates the Artifact Registry repository. If you prefer to do it manually:

```bash
gcloud config set project YOUR_PROJECT_ID

# Enable APIs
gcloud services enable \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    secretmanager.googleapis.com

# Create container registry
gcloud artifacts repositories create cr8 \
    --repository-format=docker \
    --location=europe-west2 \
    --description="CR8 Pipeline container images"
```

---

## Step 2: Create Secrets

Store API keys in GCP Secret Manager (never in code or environment files):

```bash
# Required
echo -n 'sk-your-openai-key' | gcloud secrets create OPENAI_API_KEY \
    --data-file=- --replication-policy=automatic

echo -n 'tvly-your-tavily-key' | gcloud secrets create TAVILY_API_KEY \
    --data-file=- --replication-policy=automatic

# Optional (for video generation)
echo -n 'your-heygen-key' | gcloud secrets create HEYGEN_API_KEY \
    --data-file=- --replication-policy=automatic
```

Grant the Cloud Run service account access to read secrets:

```bash
PROJECT_NUMBER=$(gcloud projects describe YOUR_PROJECT_ID --format='value(projectNumber)')

for SECRET in OPENAI_API_KEY TAVILY_API_KEY; do
    gcloud secrets add-iam-policy-binding $SECRET \
        --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
        --role="roles/secretmanager.secretAccessor"
done
```

To update a secret later:

```bash
echo -n 'new-key-value' | gcloud secrets versions add OPENAI_API_KEY --data-file=-
```

---

## Step 3: Deploy

```bash
./deploy.sh YOUR_PROJECT_ID
```

The script will:
1. Configure Docker to push to Artifact Registry
2. Build the Docker image for `linux/amd64` using `docker buildx` (required when building on Apple Silicon)
3. Push it to `europe-west2-docker.pkg.dev/YOUR_PROJECT_ID/cr8/cr8-pipeline`
4. Deploy to Cloud Run with the configured settings
5. Print the service URL

To deploy to a different region:

```bash
./deploy.sh YOUR_PROJECT_ID us-east1
```

---

## Step 4: Verify

```bash
# Get the service URL
SERVICE_URL=$(gcloud run services describe cr8-pipeline \
    --region=europe-west2 --format='value(status.url)')

# Health check
curl ${SERVICE_URL}/health
# Expected: {"status":"ok","active_jobs":0}

# Open the UI
open ${SERVICE_URL}
```

Upload a PDF, start the pipeline, and download the result to confirm everything works.

---

## Local Docker Testing

Test the container locally before deploying:

```bash
# Build
make docker-build

# Run (uses your local .env file)
make docker-run

# Visit http://localhost:8080
```

---

## Cloud Run Configuration Reference

### Without Video (PDF/PPT/Script only)

| Setting | Value | Rationale |
|---------|-------|-----------|
| `--port` | 8080 | Cloud Run default |
| `--memory` | 2Gi | Pipeline + ChromaDB + embeddings model |
| `--cpu` | 2 | Parallel ThreadPoolExecutor workers |
| `--timeout` | 3600 | Pipeline runs 3-5 min without video |
| `--min-instances` | 0 | Scale to zero when idle |
| `--max-instances` | 1 | App enforces single concurrent job |
| `--no-cpu-throttling` | — | Background threads need CPU between requests |
| `--allow-unauthenticated` | — | Public access |

### With Video — GPU Service (Recommended)

The recommended video deployment uses two services: a CPU service for the
pipeline and a separate GPU service for TTS + video composition on an NVIDIA L4.

**CPU service** (`cr8-pipeline`, europe-west2, London):

| Setting | Value | Rationale |
|---------|-------|-----------|
| `--memory` | 4Gi | Pipeline + ChromaDB + slide image export |
| `--cpu` | 2 | Pipeline is I/O-bound (API calls) |
| `--timeout` | 3600 | ~6-8 min total with GPU offload |
| `--min-instances` | 0 | Scale to zero when idle |

**GPU service** (`cr8-gpu`, europe-west1, Belgium):

| Setting | Value | Rationale |
|---------|-------|-----------|
| `--memory` | **16Gi** | Minimum for L4 GPU + Kokoro model |
| `--cpu` | **4** | Minimum for L4 GPU |
| `--gpu` | 1 | NVIDIA L4 (24 GB VRAM) |
| `--gpu-type` | nvidia-l4 | Only GPU type available on Cloud Run |
| `--timeout` | 3600 | Video generation takes ~2-3 min on GPU |
| `--min-instances` | 0 | Scale to zero (no GPU cost when idle) |
| `--no-allow-unauthenticated` | — | Private — only CPU service calls it via IAM |

The deployed GPU service URL is:
`https://cr8-gpu-1000325314523.europe-west1.run.app` (private, IAM-authenticated).

!!! info "GPU regions"
    Cloud Run GPU support is available in `europe-west1` (Belgium) and
    `europe-west4` (Netherlands) within Europe. CR8 deploys to `europe-west1`
    (Belgium). Cross-region latency from the CPU service in europe-west2 is <10ms.

!!! warning "Health endpoint: /health, not /healthz"
    The GPU service exposes `GET /health`. Cloud Run intercepts requests to
    `/healthz` for its own platform health checks. Probing `/healthz` directly
    against the GPU service will return an unexpected response. Use `/health`
    when checking GPU service readiness from the CPU service or from scripts.

!!! tip "Cost comparison: GPU is cheaper per job"
    A 5-topic video job costs ~$0.06 on GPU (3 min) vs ~$0.13 on CPU (20 min).
    GPU finishes faster, so you pay for less compute time.

### With Video — CPU Only (Legacy)

For local development or when GPU is not available, video runs locally on CPU:

| Setting | Value | Rationale |
|---------|-------|-----------|
| `--memory` | **4Gi** | Kokoro TTS peaks at ~3.4 GB; 2Gi will OOM |
| `--cpu` | **4** | TTS synthesis + parallel ffmpeg encoding are CPU-bound |
| `--timeout` | 3600 | Pipeline runs 15-25 min with video for 5 topics |

!!! warning "Kokoro TTS requires 4 GiB minimum"
    The Kokoro TTS model uses ~250 MB on disk and peaks at ~3.4 GB RAM during
    synthesis. Deploying with `--memory=2Gi` and video enabled will cause the
    container to be OOM-killed. Always use `--memory=4Gi` when
    `VIDEO_PROVIDER=kokoro`.

### Environment Variables

Set via `--set-env-vars` in deploy.sh:

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_MODEL` | gpt-5.1 | Backward-compat alias (maps to premium) |
| `OPENAI_MODEL_PREMIUM` | gpt-5.1 | Premium model for critical modules + scripts |
| `OPENAI_MODEL_MINI` | gpt-5-mini | Model for analysis/structured output |
| `OPENAI_MODEL_NANO` | gpt-5-nano | Model for summarization/extraction |
| `CHROMA_PERSIST_DIR` | ./chroma_db | Vector DB directory |
| `LANGCHAIN_TRACING_V2` | true | Enable LangSmith tracing |
| `LANGCHAIN_PROJECT` | cr8-prototype | LangSmith project name |
| `GPU_SERVICE_URL` | *(empty)* | URL of GPU video service (enables GPU offload) |
| `GCS_BUCKET` | cr8-jobs | Shared GCS bucket name for CPU↔GPU data transfer |

The production GCS bucket is `gs://cr8-jobs-cr8-learning`.

### Secrets

Injected from Secret Manager via `--set-secrets`:

| Secret | Required | Description |
|--------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `TAVILY_API_KEY` | Yes | Tavily web search key |
| `HEYGEN_API_KEY` | No | HeyGen video generation key |

---

## Cost Estimate

With `min-instances=0`, both services scale to zero and you only pay during active jobs:

| Scenario | CPU Service | GPU Service | **Total** |
|----------|-----------|-----------|-----------|
| Idle (no traffic) | ~$0 | ~$0 | **~$0** |
| Text only (5 jobs/month) | ~$0.10 | $0 | **~$0.10** |
| Video (5 jobs/month) | ~$0.10 | ~$0.30 | **~$0.40** |
| Video (20 jobs/month) | ~$0.40 | ~$1.20 | **~$1.60** |
| Always-on CPU (`min-instances=1`) | ~$70/mo | ~$0 | **~$70/mo** |

Cloud Run pricing (Tier 1): $0.000024/vCPU-sec, $0.0000025/GiB-sec, $0.000187/GPU-sec (L4).

To switch to always-on (no cold starts), edit `deploy.sh` and change `--min-instances=0` to `--min-instances=1`.

---

## Troubleshooting

### Cold starts take too long

With `min-instances=0`, the first request after idle triggers a cold start (30-60s). Options:
- Set `--min-instances=1` for instant response (adds ~$137/mo)
- Add `--cpu-boost` to the deploy command for faster startup CPU

### Pipeline job fails mid-run

Check logs in Cloud Console:
```bash
gcloud run services logs read cr8-pipeline --region=europe-west2 --limit=50
```

Or use the Cloud Console: Console > Cloud Run > cr8-pipeline > Logs.

### Instance recycled during a job

Cloud Run may recycle instances during long idle periods. With `min-instances=0`, a running job could be lost if the instance is shut down. For production reliability, set `min-instances=1`.

### Out of memory

If you see OOM errors, increase memory:
```bash
gcloud run services update cr8-pipeline --memory=4Gi --region=europe-west2
```

### Secret access denied

Ensure the Cloud Run service account has `secretmanager.secretAccessor` role:
```bash
PROJECT_NUMBER=$(gcloud projects describe YOUR_PROJECT_ID --format='value(projectNumber)')
gcloud secrets add-iam-policy-binding OPENAI_API_KEY \
    --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

### GPU service not responding

Check that the CPU service is passing the correct `GPU_SERVICE_URL`. The GPU service health endpoint is `/health` (not `/healthz`):

```bash
# Check GPU service health directly (requires identity token outside GCP)
GPU_URL="https://cr8-gpu-1000325314523.europe-west1.run.app"
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
    ${GPU_URL}/health
# Expected: {"status":"ok","gpu":"Tesla T4 ..."}

# Check GPU service logs
gcloud run services logs read cr8-gpu --region=europe-west1 --limit=50
```

### Viewing logs

```bash
# Recent logs
gcloud run services logs read cr8-pipeline --region=europe-west2 --limit=100

# Stream logs in real-time
gcloud run services logs tail cr8-pipeline --region=europe-west2
```

---

## Future Enhancements

These are not needed for the initial deployment but worth considering as usage grows:

1. **CI/CD** — GitHub Actions pipeline to auto-deploy on push to main
2. **Custom Domain** — Map a domain via `gcloud run domain-mappings create`
3. **Authentication** — Add IAM or Identity-Aware Proxy to restrict access
4. **Cloud Tasks** — Decouple job submission from execution for better reliability
5. **Monitoring** — Set up Cloud Monitoring alerts for error rates and latency
