#!/usr/bin/env bash
# Poll a Cloud Build until it reaches a terminal state.
#
# The Deploy workflow submits builds with `--async` and waits here because the
# `github-deploy` service account cannot stream the regional default logs
# bucket, which makes a foreground `gcloud builds submit` exit 1 even when the
# build succeeds. `gcloud builds describe` only needs cloudbuild.builds.get,
# which the SA has via roles/cloudbuild.builds.editor.
#
# Usage: wait-build.sh <BUILD_ID> <PROJECT_ID> <REGION>
set -euo pipefail

BUILD_ID="${1:?build id required}"
PROJECT="${2:?project id required}"
REGION="${3:?region required}"

echo "Waiting for Cloud Build ${BUILD_ID} (${REGION})..."
while true; do
  STATUS="$(gcloud builds describe "${BUILD_ID}" \
    --project="${PROJECT}" --region="${REGION}" --format='value(status)')"
  case "${STATUS}" in
    SUCCESS)
      echo "Build ${BUILD_ID}: SUCCESS"
      exit 0
      ;;
    FAILURE | INTERNAL_ERROR | TIMEOUT | CANCELLED | EXPIRED)
      echo "::error::Cloud Build ${BUILD_ID} ended with status: ${STATUS}"
      echo "Logs: https://console.cloud.google.com/cloud-build/builds;region=${REGION}/${BUILD_ID}?project=${PROJECT}"
      exit 1
      ;;
    *)
      echo "  status=${STATUS:-QUEUED}; sleeping 15s"
      sleep 15
      ;;
  esac
done
