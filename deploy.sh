#!/usr/bin/env bash
# deploy.sh — Build, push, and deploy CR8 Pipeline to GCP Cloud Run.
#
# Usage:
#   ./deploy.sh <GCP_PROJECT_ID> [REGION]        # deploy all services
#   ./deploy.sh <GCP_PROJECT_ID> --cpu            # deploy CPU pipeline only
#   ./deploy.sh <GCP_PROJECT_ID> --gpu            # deploy GPU services only
#   ./deploy.sh <GCP_PROJECT_ID> --cpu-video      # deploy CPU video fallback only
#   ./deploy.sh --setup <GCP_PROJECT_ID> [REGION] # one-time GCP setup
#
# Prerequisites:
#   - gcloud CLI installed and authenticated (`gcloud auth login`)
#   - Docker installed and running
#   - Secrets already created in Secret Manager (see --setup flag)

set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────
CPU_SERVICE_NAME="cr8-pipeline"
GPU_SERVICE_NAME="cr8-gpu"
CPU_VIDEO_SERVICE_NAME="cr8-cpu-video"
REPO_NAME="cr8"

# GPU-enabled regions — europe-west4 (Netherlands) has L4 quota=3
GPU_REGION="europe-west4"

# ── Parse arguments ───────────────────────────────────────────────
DEPLOY_CPU=true
DEPLOY_GPU=true
DEPLOY_CPU_VIDEO=true
RUN_SETUP=false

if [[ "${1:-}" == "--setup" ]]; then
    RUN_SETUP=true
    PROJECT_ID="${2:?Usage: ./deploy.sh --setup <GCP_PROJECT_ID> [REGION]}"
    REGION="${3:-europe-west2}"
else
    PROJECT_ID="${1:?Usage: ./deploy.sh <GCP_PROJECT_ID> [--cpu|--gpu|--cpu-video] [REGION]}"

    # Check for service-specific flags
    if [[ "${2:-}" == "--cpu" ]]; then
        DEPLOY_GPU=false
        DEPLOY_CPU_VIDEO=false
        REGION="${3:-europe-west2}"
    elif [[ "${2:-}" == "--gpu" ]]; then
        DEPLOY_CPU=false
        DEPLOY_CPU_VIDEO=false
        REGION="${3:-europe-west2}"
    elif [[ "${2:-}" == "--cpu-video" ]]; then
        DEPLOY_CPU=false
        DEPLOY_GPU=false
        REGION="${3:-europe-west2}"
    else
        REGION="${2:-europe-west2}"
    fi
fi

REGISTRY="${REGION}-docker.pkg.dev"
GPU_REGISTRY="${GPU_REGION}-docker.pkg.dev"
CPU_IMAGE="${REGISTRY}/${PROJECT_ID}/${REPO_NAME}/${CPU_SERVICE_NAME}"
GPU_IMAGE="${GPU_REGISTRY}/${PROJECT_ID}/${REPO_NAME}/${GPU_SERVICE_NAME}"
CPU_VIDEO_IMAGE="${REGISTRY}/${PROJECT_ID}/${REPO_NAME}/${CPU_VIDEO_SERVICE_NAME}"
TAG="$(git rev-parse --short HEAD 2>/dev/null || date +%Y%m%d%H%M%S)"
GCS_BUCKET="cr8-jobs-${PROJECT_ID}"

echo "Project:    ${PROJECT_ID}"
echo "CPU Region: ${REGION}"
echo "GPU Region: ${GPU_REGION}"
echo "GCS Bucket: ${GCS_BUCKET}"
echo "Tag:        ${TAG}"
echo ""

# ── One-time setup ────────────────────────────────────────────────
if [[ "${RUN_SETUP}" == "true" ]]; then
    echo "==> Setting GCP project..."
    gcloud config set project "${PROJECT_ID}"

    echo "==> Enabling required APIs..."
    gcloud services enable \
        run.googleapis.com \
        artifactregistry.googleapis.com \
        secretmanager.googleapis.com \
        storage.googleapis.com

    echo "==> Creating Artifact Registry repositories..."
    gcloud artifacts repositories create "${REPO_NAME}" \
        --repository-format=docker \
        --location="${REGION}" \
        --description="CR8 Pipeline container images" \
        2>/dev/null || echo "    (${REGION} repository already exists)"

    if [[ "${REGION}" != "${GPU_REGION}" ]]; then
        gcloud artifacts repositories create "${REPO_NAME}" \
            --repository-format=docker \
            --location="${GPU_REGION}" \
            --description="CR8 GPU service container images" \
            2>/dev/null || echo "    (${GPU_REGION} repository already exists)"
    fi

    echo "==> Creating GCS bucket for CPU↔GPU data transfer..."
    gsutil mb -l EU "gs://${GCS_BUCKET}" 2>/dev/null || echo "    (bucket already exists)"

    echo ""
    echo "==> Now create your secrets. Run these commands, replacing the values:"
    echo ""
    echo "  # Required"
    echo "  echo -n 'sk-YOUR-KEY' | gcloud secrets create OPENAI_API_KEY --data-file=- --replication-policy=automatic"
    echo "  echo -n 'tvly-YOUR-KEY' | gcloud secrets create TAVILY_API_KEY --data-file=- --replication-policy=automatic"
    echo ""
    echo "  # Web UI login password"
    echo "  echo -n 'your-password' | gcloud secrets create AUTH_PASSWORD --data-file=- --replication-policy=automatic"
    echo ""
    echo "  # Optional — HuggingFace token (GPU service model downloads)"
    echo "  echo -n 'hf_YOUR-TOKEN' | gcloud secrets create HF_TOKEN --data-file=- --replication-policy=automatic"
    echo ""
    echo "  # Optional — HeyGen video generation"
    echo "  echo -n 'YOUR-KEY' | gcloud secrets create HEYGEN_API_KEY --data-file=- --replication-policy=automatic"
    echo ""
    echo "  # Optional — LangSmith tracing"
    echo "  echo -n 'ls_YOUR-KEY' | gcloud secrets create LANGCHAIN_API_KEY --data-file=- --replication-policy=automatic"
    echo ""
    echo "==> Then grant the Cloud Run service account access to secrets and GCS:"
    echo ""
    echo "  PROJECT_NUMBER=\$(gcloud projects describe ${PROJECT_ID} --format='value(projectNumber)')"
    echo "  SA=\"\${PROJECT_NUMBER}-compute@developer.gserviceaccount.com\""
    echo ""
    echo "  # Secrets access (all secrets)"
    echo "  for SECRET in OPENAI_API_KEY TAVILY_API_KEY AUTH_PASSWORD HF_TOKEN HEYGEN_API_KEY LANGCHAIN_API_KEY; do"
    echo "    gcloud secrets add-iam-policy-binding \$SECRET \\"
    echo "      --member=\"serviceAccount:\${SA}\" \\"
    echo "      --role=\"roles/secretmanager.secretAccessor\" 2>/dev/null || true"
    echo "  done"
    echo ""
    echo "  # GCS bucket access (all services need read/write)"
    echo "  gsutil iam ch \"serviceAccount:\${SA}:roles/storage.objectAdmin\" gs://${GCS_BUCKET}"
    echo ""
    echo "  # GPU service invocation (CPU calls both GPU services)"
    echo "  gcloud run services add-iam-policy-binding ${GPU_SERVICE_NAME} \\"
    echo "    --member=\"serviceAccount:\${SA}\" \\"
    echo "    --role=\"roles/run.invoker\" \\"
    echo "    --region=${GPU_REGION}"
    echo ""
    echo "Setup complete. Run ./deploy.sh ${PROJECT_ID} to deploy both services."
    exit 0
fi

# ── Build & Deploy GPU Service ────────────────────────────────────
if [[ "${DEPLOY_GPU}" == "true" ]]; then
    echo "==> Configuring Docker for GPU Artifact Registry..."
    gcloud auth configure-docker "${GPU_REGISTRY}" --quiet

    echo "==> Building GPU service Docker image..."
    docker buildx build --platform linux/amd64 --provenance=false \
        -f Dockerfile.gpu -t "${GPU_IMAGE}:${TAG}" --push .

    echo "==> Deploying GPU service to Cloud Run (${GPU_REGION})..."
    gcloud run deploy "${GPU_SERVICE_NAME}" \
        --image="${GPU_IMAGE}:${TAG}" \
        --region="${GPU_REGION}" \
        --platform=managed \
        --no-allow-unauthenticated \
        --port=8080 \
        --memory=16Gi \
        --cpu=4 \
        --gpu=1 \
        --gpu-type=nvidia-l4 \
        --timeout=3600 \
        --min-instances=0 \
        --max-instances=1 \
        --no-cpu-throttling \
        --set-secrets="HF_TOKEN=HF_TOKEN:latest" \
        --set-env-vars="GCS_BUCKET=${GCS_BUCKET},VIDEO_DEVICE=auto,VIDEO_MAX_WORKERS=6,KOKORO_VOICE=af_heart,KOKORO_LANG=a,VIDEO_FPS=2"

    GPU_URL=$(gcloud run services describe "${GPU_SERVICE_NAME}" \
        --region="${GPU_REGION}" --format='value(status.url)')
    echo ""
    echo "GPU service deployed: ${GPU_URL}"
    echo ""
fi

# ── Build & Deploy CPU Video Fallback Service ─────────────────────
if [[ "${DEPLOY_CPU_VIDEO}" == "true" ]]; then
    echo "==> Configuring Docker for CPU Video Artifact Registry..."
    gcloud auth configure-docker "${REGISTRY}" --quiet

    echo "==> Building CPU video service Docker image..."
    docker buildx build --platform linux/amd64 --provenance=false \
        -f Dockerfile.cpu-video -t "${CPU_VIDEO_IMAGE}:${TAG}" --push .

    echo "==> Deploying CPU video service to Cloud Run (${REGION})..."
    gcloud run deploy "${CPU_VIDEO_SERVICE_NAME}" \
        --image="${CPU_VIDEO_IMAGE}:${TAG}" \
        --region="${REGION}" \
        --platform=managed \
        --no-allow-unauthenticated \
        --port=8080 \
        --memory=32Gi \
        --cpu=8 \
        --timeout=3600 \
        --min-instances=0 \
        --max-instances=1 \
        --no-cpu-throttling \
        --set-env-vars="GCS_BUCKET=${GCS_BUCKET},VIDEO_DEVICE=cpu,VIDEO_MAX_WORKERS=6,KOKORO_VOICE=af_heart,KOKORO_LANG=a,VIDEO_FPS=2"

    CPU_VIDEO_URL=$(gcloud run services describe "${CPU_VIDEO_SERVICE_NAME}" \
        --region="${REGION}" --format='value(status.url)')
    echo ""
    echo "CPU video service deployed: ${CPU_VIDEO_URL}"
    echo ""
fi

# ── Build & Deploy CPU Service ────────────────────────────────────
if [[ "${DEPLOY_CPU}" == "true" ]]; then
    echo "==> Configuring Docker for CPU Artifact Registry..."
    gcloud auth configure-docker "${REGISTRY}" --quiet

    echo "==> Building CPU service Docker image..."
    docker buildx build --platform linux/amd64 --provenance=false \
        -f Dockerfile -t "${CPU_IMAGE}:${TAG}" --push .

    # Get video service URLs for injection
    GPU_URL=$(gcloud run services describe "${GPU_SERVICE_NAME}" \
        --region="${GPU_REGION}" --format='value(status.url)' 2>/dev/null || echo "")
    CPU_VIDEO_URL=$(gcloud run services describe "${CPU_VIDEO_SERVICE_NAME}" \
        --region="${REGION}" --format='value(status.url)' 2>/dev/null || echo "")

    if [[ -z "${GPU_URL}" && -z "${CPU_VIDEO_URL}" ]]; then
        echo "WARNING: No video services found — video generation will be unavailable"
    fi

    echo "==> Deploying CPU service to Cloud Run (${REGION})..."
    gcloud run deploy "${CPU_SERVICE_NAME}" \
        --image="${CPU_IMAGE}:${TAG}" \
        --region="${REGION}" \
        --platform=managed \
        --allow-unauthenticated \
        --port=8080 \
        --memory=4Gi \
        --cpu=2 \
        --timeout=3600 \
        --min-instances=0 \
        --max-instances=1 \
        --no-cpu-throttling \
        --set-secrets="OPENAI_API_KEY=OPENAI_API_KEY:latest,TAVILY_API_KEY=TAVILY_API_KEY:latest,AUTH_PASSWORD=AUTH_PASSWORD:latest,HF_TOKEN=HF_TOKEN:latest,HEYGEN_API_KEY=HEYGEN_API_KEY:latest,LANGCHAIN_API_KEY=LANGCHAIN_API_KEY:latest" \
        --set-env-vars="GPU_SERVICE_URL=${GPU_URL},CPU_VIDEO_SERVICE_URL=${CPU_VIDEO_URL},GCS_BUCKET=${GCS_BUCKET},OPENAI_MODEL=gpt-5.1,OPENAI_MODEL_PREMIUM=gpt-5.1,OPENAI_MODEL_MINI=gpt-5-mini,OPENAI_MODEL_NANO=gpt-5-nano,CHROMA_PERSIST_DIR=./chroma_db,LANGCHAIN_TRACING_V2=true,LANGCHAIN_PROJECT=cr8-prototype,MAX_WORKERS=12,VIDEO_MAX_WORKERS=6,VIDEO_PROVIDER=kokoro,COOKIE_SECURE=true"

    CPU_URL=$(gcloud run services describe "${CPU_SERVICE_NAME}" \
        --region="${REGION}" --format='value(status.url)')
    echo ""
    echo "CPU service deployed: ${CPU_URL}"
fi

echo ""
echo "==> Deployment complete!"
if [[ "${DEPLOY_CPU}" == "true" ]]; then
    echo "App URL:    ${CPU_URL:-unknown}"
    echo "Health:     ${CPU_URL:-unknown}/health"
fi
if [[ "${DEPLOY_GPU}" == "true" ]]; then
    echo "GPU URL:         ${GPU_URL:-unknown} (private — CPU service auth only)"
fi
if [[ "${DEPLOY_CPU_VIDEO}" == "true" ]]; then
    echo "CPU Video:       ${CPU_VIDEO_URL:-unknown} (${REGION}, private)"
fi
echo "GCS Bucket: gs://${GCS_BUCKET}"
