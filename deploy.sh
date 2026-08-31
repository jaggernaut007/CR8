#!/usr/bin/env bash
# deploy.sh — Build, push, and deploy CR8 Pipeline to GCP Cloud Run.
#
# Secrets are supplied by Doppler at deploy time — run this script through
# `doppler run` so secret values are present in the environment:
#
#   doppler run -- ./deploy.sh <GCP_PROJECT_ID> [REGION]
#
# Usage:
#   doppler run -- ./deploy.sh <GCP_PROJECT_ID> [REGION]        # deploy all services
#   doppler run -- ./deploy.sh <GCP_PROJECT_ID> --cpu            # deploy CPU pipeline only
#   doppler run -- ./deploy.sh <GCP_PROJECT_ID> --gpu            # deploy GPU services only
#   doppler run -- ./deploy.sh <GCP_PROJECT_ID> --cpu-video      # deploy CPU video fallback only
#   ./deploy.sh --setup <GCP_PROJECT_ID> [REGION]                # one-time GCP setup
#
# Prerequisites:
#   - gcloud CLI installed and authenticated (`gcloud auth login`)
#   - Docker installed and running
#   - Doppler CLI installed and configured (`doppler login` + `doppler setup`),
#     or a DOPPLER_TOKEN service token exported in the environment (see --setup)

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

# ── Secret plumbing (Doppler → Cloud Run env-vars file) ───────────
# Secret values arrive as environment variables (via `doppler run` or a
# DOPPLER_TOKEN in the environment). We never pass them on the gcloud
# command line — instead each service gets a mode 600 --env-vars-file
# that is deleted on exit.

ENV_FILES=()
cleanup_env_files() {
    for f in "${ENV_FILES[@]:-}"; do
        [[ -n "${f}" ]] && rm -f "${f}"
    done
}
trap cleanup_env_files EXIT

# write_env_file <path> KEY=VALUE [KEY=VALUE ...]
# Emits a YAML env-vars file (double-quoted scalars, safely escaped).
write_env_file() {
    local path="$1"
    shift
    : >"${path}"
    chmod 600 "${path}"
    python3 - "$@" >"${path}" <<'PY'
import sys

for pair in sys.argv[1:]:
    key, _, value = pair.partition("=")
    if value == "":
        continue  # unset — let the app fall back to its default
    esc = value.replace("\\", "\\\\").replace('"', '\\"')
    print(f'{key}: "{esc}"')
PY
    ENV_FILES+=("${path}")
}

# Guard: required secrets must be present in the environment for a deploy.
if [[ "${RUN_SETUP}" != "true" ]]; then
    _missing=()
    for _var in OPENAI_API_KEY TAVILY_API_KEY AUTH_PASSWORD DATABASE_URL JWT_SECRET; do
        [[ -z "${!_var:-}" ]] && _missing+=("${_var}")
    done
    if [[ ${#_missing[@]} -gt 0 ]]; then
        echo "ERROR: missing required secret(s) in environment: ${_missing[*]}" >&2
        echo "       Run this script through Doppler:  doppler run -- ./deploy.sh ${PROJECT_ID}" >&2
        echo "       (or export a DOPPLER_TOKEN service token first)" >&2
        exit 1
    fi
fi

# ── One-time setup ────────────────────────────────────────────────
if [[ "${RUN_SETUP}" == "true" ]]; then
    echo "==> Setting GCP project..."
    gcloud config set project "${PROJECT_ID}"

    echo "==> Enabling required APIs..."
    gcloud services enable \
        run.googleapis.com \
        artifactregistry.googleapis.com \
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
    echo "==> Secrets live in Doppler (not GCP Secret Manager)."
    echo "    One-time: install the Doppler CLI, then create a project + config and"
    echo "    populate it. Replace the placeholder values:"
    echo ""
    echo "  doppler login"
    echo "  doppler projects create cr8"
    echo "  doppler setup --project cr8 --config prd"
    echo ""
    echo "  # Required"
    echo "  doppler secrets set OPENAI_API_KEY='sk-YOUR-KEY'"
    echo "  doppler secrets set TAVILY_API_KEY='tvly-YOUR-KEY'"
    echo "  doppler secrets set AUTH_PASSWORD='your-web-ui-password'"
    echo "  doppler secrets set DATABASE_URL='postgresql://user:pass@host/db?sslmode=require'"
    echo "  doppler secrets set JWT_SECRET=\"\$(openssl rand -hex 32)\""
    echo ""
    echo "  # Optional"
    echo "  doppler secrets set HF_TOKEN='hf_YOUR-TOKEN'          # GPU model downloads"
    echo "  doppler secrets set HEYGEN_API_KEY='YOUR-KEY'         # HeyGen video"
    echo "  doppler secrets set LANGCHAIN_API_KEY='ls_YOUR-KEY'   # LangSmith tracing"
    echo ""
    echo "==> Deploy with secrets injected from Doppler:"
    echo ""
    echo "  doppler run --project cr8 --config prd -- ./deploy.sh ${PROJECT_ID}"
    echo ""
    echo "  # For CI / non-interactive deploys, use a service token instead:"
    echo "  #   export DOPPLER_TOKEN=\$(doppler configs tokens create ci --project cr8 --config prd --plain)"
    echo "  #   ./deploy.sh ${PROJECT_ID}"
    echo ""
    echo "==> Grant the Cloud Run service account access to GCS:"
    echo ""
    echo "  PROJECT_NUMBER=\$(gcloud projects describe ${PROJECT_ID} --format='value(projectNumber)')"
    echo "  SA=\"\${PROJECT_NUMBER}-compute@developer.gserviceaccount.com\""
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
    GPU_ENV_FILE="$(mktemp -t cr8-gpu-env.XXXXXX)"
    write_env_file "${GPU_ENV_FILE}" \
        "HF_TOKEN=${HF_TOKEN:-}" \
        "GCS_BUCKET=${GCS_BUCKET}" \
        "VIDEO_DEVICE=auto" \
        "VIDEO_MAX_WORKERS=6" \
        "KOKORO_VOICE=af_heart" \
        "KOKORO_LANG=a" \
        "VIDEO_FPS=2"
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
        --env-vars-file="${GPU_ENV_FILE}" \
        --clear-secrets

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
    CPU_ENV_FILE="$(mktemp -t cr8-cpu-env.XXXXXX)"
    write_env_file "${CPU_ENV_FILE}" \
        "OPENAI_API_KEY=${OPENAI_API_KEY}" \
        "TAVILY_API_KEY=${TAVILY_API_KEY}" \
        "AUTH_PASSWORD=${AUTH_PASSWORD}" \
        "HF_TOKEN=${HF_TOKEN:-}" \
        "HEYGEN_API_KEY=${HEYGEN_API_KEY:-}" \
        "LANGCHAIN_API_KEY=${LANGCHAIN_API_KEY:-}" \
        "DATABASE_URL=${DATABASE_URL}" \
        "JWT_SECRET=${JWT_SECRET}" \
        "GPU_SERVICE_URL=${GPU_URL}" \
        "CPU_VIDEO_SERVICE_URL=${CPU_VIDEO_URL}" \
        "GCS_BUCKET=${GCS_BUCKET}" \
        "OPENAI_MODEL=gpt-5.1" \
        "OPENAI_MODEL_PREMIUM=gpt-5.1" \
        "OPENAI_MODEL_MINI=gpt-5-mini" \
        "OPENAI_MODEL_NANO=gpt-5-nano" \
        "CHROMA_PERSIST_DIR=./chroma_db" \
        "LANGCHAIN_TRACING_V2=true" \
        "LANGCHAIN_PROJECT=cr8-prototype" \
        "MAX_WORKERS=12" \
        "VIDEO_MAX_WORKERS=6" \
        "VIDEO_PROVIDER=kokoro" \
        "COOKIE_SECURE=true"
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
        --env-vars-file="${CPU_ENV_FILE}" \
        --clear-secrets

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
