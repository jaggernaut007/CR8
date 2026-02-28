#!/usr/bin/env bash
# deploy.sh — Build, push, and deploy CR8 Pipeline to GCP Cloud Run.
#
# Usage:
#   ./deploy.sh <GCP_PROJECT_ID> [REGION]
#
# Prerequisites:
#   - gcloud CLI installed and authenticated (`gcloud auth login`)
#   - Docker installed and running
#   - Secrets already created in Secret Manager (see --setup flag)
#
# Flags:
#   --setup   Run one-time GCP project setup (enable APIs, create
#             Artifact Registry, create secrets) instead of deploying.

set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────
SERVICE_NAME="cr8-pipeline"
REPO_NAME="cr8"

# ── Parse arguments ───────────────────────────────────────────────
if [[ "${1:-}" == "--setup" ]]; then
    RUN_SETUP=true
    PROJECT_ID="${2:?Usage: ./deploy.sh --setup <GCP_PROJECT_ID> [REGION]}"
    REGION="${3:-europe-west2}"
else
    RUN_SETUP=false
    PROJECT_ID="${1:?Usage: ./deploy.sh <GCP_PROJECT_ID> [REGION]}"
    REGION="${2:-europe-west2}"
fi

REGISTRY="${REGION}-docker.pkg.dev"
IMAGE="${REGISTRY}/${PROJECT_ID}/${REPO_NAME}/${SERVICE_NAME}"
TAG="$(git rev-parse --short HEAD 2>/dev/null || date +%Y%m%d%H%M%S)"

echo "Project:  ${PROJECT_ID}"
echo "Region:   ${REGION}"
echo "Image:    ${IMAGE}:${TAG}"
echo ""

# ── One-time setup ────────────────────────────────────────────────
if [[ "${RUN_SETUP}" == "true" ]]; then
    echo "==> Setting GCP project..."
    gcloud config set project "${PROJECT_ID}"

    echo "==> Enabling required APIs..."
    gcloud services enable \
        run.googleapis.com \
        artifactregistry.googleapis.com \
        secretmanager.googleapis.com

    echo "==> Creating Artifact Registry repository..."
    gcloud artifacts repositories create "${REPO_NAME}" \
        --repository-format=docker \
        --location="${REGION}" \
        --description="CR8 Pipeline container images" \
        2>/dev/null || echo "    (repository already exists)"

    echo ""
    echo "==> Now create your secrets. Run these commands, replacing the values:"
    echo ""
    echo "  echo -n 'sk-YOUR-KEY' | gcloud secrets create OPENAI_API_KEY --data-file=- --replication-policy=automatic"
    echo "  echo -n 'tvly-YOUR-KEY' | gcloud secrets create TAVILY_API_KEY --data-file=- --replication-policy=automatic"
    echo ""
    echo "  # Optional (for video generation):"
    echo "  echo -n 'YOUR-KEY' | gcloud secrets create HEYGEN_API_KEY --data-file=- --replication-policy=automatic"
    echo ""
    echo "  # Local development only — add to .env to allow HTTP cookies:"
    echo "  # COOKIE_SECURE=false"
    echo ""
    echo "==> Then grant the Cloud Run service account access to secrets:"
    echo ""
    echo "  PROJECT_NUMBER=\$(gcloud projects describe ${PROJECT_ID} --format='value(projectNumber)')"
    echo "  for SECRET in OPENAI_API_KEY TAVILY_API_KEY; do"
    echo "    gcloud secrets add-iam-policy-binding \$SECRET \\"
    echo "      --member=\"serviceAccount:\${PROJECT_NUMBER}-compute@developer.gserviceaccount.com\" \\"
    echo "      --role=\"roles/secretmanager.secretAccessor\""
    echo "  done"
    echo ""
    echo "Setup complete. Run ./deploy.sh ${PROJECT_ID} to deploy."
    exit 0
fi

# ── Build & Push ──────────────────────────────────────────────────
echo "==> Configuring Docker for Artifact Registry..."
gcloud auth configure-docker "${REGISTRY}" --quiet

echo "==> Building Docker image..."
docker buildx build --platform linux/amd64 --provenance=false -t "${IMAGE}:${TAG}" --push .

# ── Deploy to Cloud Run ───────────────────────────────────────────
echo "==> Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
    --image="${IMAGE}:${TAG}" \
    --region="${REGION}" \
    --platform=managed \
    --allow-unauthenticated \
    --port=8080 \
    --memory=2Gi \
    --cpu=2 \
    --timeout=3600 \
    --min-instances=0 \
    --max-instances=1 \
    --no-cpu-throttling \
    --set-secrets="OPENAI_API_KEY=OPENAI_API_KEY:latest,TAVILY_API_KEY=TAVILY_API_KEY:latest,HEYGEN_API_KEY=HEYGEN_API_KEY:latest" \
    --set-env-vars="OPENAI_MODEL=gpt-5.1,OPENAI_MODEL_PREMIUM=gpt-5.1,OPENAI_MODEL_MINI=gpt-5-mini,OPENAI_MODEL_NANO=gpt-5-nano,CHROMA_PERSIST_DIR=./chroma_db,LANGCHAIN_TRACING_V2=true,LANGCHAIN_PROJECT=cr8-prototype,MAX_WORKERS=12,VIDEO_MAX_WORKERS=6,COOKIE_SECURE=true"

echo ""
echo "==> Deployment complete!"
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --region="${REGION}" --format='value(status.url)')
echo "URL: ${SERVICE_URL}"
echo "Health: ${SERVICE_URL}/health"
