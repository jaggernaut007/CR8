"""GCS client for transferring video job data between CPU and GPU services.

Usage (CPU side):
    from backend.services.gcs_client import GCSVideoClient

    gcs = GCSVideoClient()
    gcs_prefix = gcs.upload_job_inputs("job123", slide_images, manifest)
    gcs.download_videos("job123", "outputs/videos")
    gcs.cleanup_job("job123")
"""

from __future__ import annotations

import json
import logging
import os
import re

from backend.config import settings

_VALID_JOB_ID = re.compile(r"^[a-zA-Z0-9_-]{1,128}$")

logger = logging.getLogger(__name__)


class GCSVideoClient:
    """Upload slide images / download completed videos via Google Cloud Storage."""

    def __init__(self, bucket_name: str | None = None):
        from google.cloud import storage

        self._client = storage.Client()
        self._bucket = self._client.bucket(bucket_name or settings.gcs_bucket)

    def upload_job_inputs(
        self,
        job_id: str,
        slide_images: list[str],
        manifest: dict,
    ) -> str:
        """Upload slide PNGs and manifest.json to GCS.

        Returns:
            The GCS prefix string, e.g. ``gs://cr8-jobs/job123``.
        """
        if not _VALID_JOB_ID.match(job_id):
            raise ValueError(f"Invalid job_id for GCS path: {job_id!r}")
        try:
            prefix = job_id

            # Upload manifest
            blob = self._bucket.blob(f"{prefix}/input/manifest.json")
            blob.upload_from_string(
                json.dumps(manifest, ensure_ascii=False),
                content_type="application/json",
            )
            logger.debug("Uploaded manifest to gs://%s/%s/input/manifest.json", self._bucket.name, prefix)

            # Upload slide images
            for path in slide_images:
                name = os.path.basename(path)
                blob = self._bucket.blob(f"{prefix}/input/{name}")
                blob.upload_from_filename(path, content_type="image/png")
                logger.debug("Uploaded slide: gs://%s/%s/input/%s", self._bucket.name, prefix, name)

            return f"gs://{self._bucket.name}/{prefix}"
        except Exception as exc:
            raise RuntimeError(f"GCS upload failed for job {job_id}: {exc}") from exc

    def download_videos(self, job_id: str, local_dir: str) -> list[str]:
        """Download completed MP4s from ``{job_id}/output/`` to *local_dir*.

        Returns:
            Sorted list of local MP4 file paths.
        """
        if not _VALID_JOB_ID.match(job_id):
            raise ValueError(f"Invalid job_id for GCS path: {job_id!r}")
        try:
            os.makedirs(local_dir, exist_ok=True)
            prefix = f"{job_id}/output/"
            blobs = self._client.list_blobs(self._bucket, prefix=prefix)
            paths: list[str] = []
            for blob in blobs:
                if blob.name.endswith(".mp4"):
                    local_path = os.path.join(local_dir, os.path.basename(blob.name))
                    blob.download_to_filename(local_path)
                    paths.append(local_path)
                    logger.debug("Downloaded video: %s", local_path)
            return sorted(paths)
        except Exception as exc:
            raise RuntimeError(f"GCS download failed for job {job_id}: {exc}") from exc

    def cleanup_job(self, job_id: str) -> int:
        """Delete all blobs under ``{job_id}/``. Returns count of deleted blobs."""
        if not _VALID_JOB_ID.match(job_id):
            raise ValueError(f"Invalid job_id for GCS path: {job_id!r}")
        try:
            prefix = f"{job_id}/"
            blobs = list(self._client.list_blobs(self._bucket, prefix=prefix))
            for blob in blobs:
                blob.delete()
            logger.info("Cleaned up %d blobs for job %s", len(blobs), job_id)
            return len(blobs)
        except Exception as exc:
            raise RuntimeError(f"GCS cleanup failed for job {job_id}: {exc}") from exc
