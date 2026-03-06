"""GCS helpers for the CPU video service (download inputs, upload outputs)."""

from __future__ import annotations

import json
import logging
import os

logger = logging.getLogger(__name__)


class CPUGCSClient:
    """Download slide images from GCS and upload completed videos back."""

    def __init__(self, bucket_name: str):
        from google.cloud import storage

        self._client = storage.Client()
        self._bucket = self._client.bucket(bucket_name)

    def download_manifest(self, gcs_prefix: str, local_dir: str) -> dict:
        """Download and parse ``manifest.json`` from the GCS job prefix."""
        try:
            prefix = _strip_gs_prefix(gcs_prefix)
            blob = self._bucket.blob(f"{prefix}/input/manifest.json")
            local_path = os.path.join(local_dir, "manifest.json")
            blob.download_to_filename(local_path)
            with open(local_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            raise RuntimeError(f"GCS manifest download failed ({gcs_prefix}): {exc}") from exc

    def download_slides(
        self, gcs_prefix: str, slide_names: list[str], local_dir: str
    ) -> list[str]:
        """Download slide PNGs from GCS to *local_dir*. Returns local paths."""
        try:
            prefix = _strip_gs_prefix(gcs_prefix)
            os.makedirs(local_dir, exist_ok=True)
            paths: list[str] = []
            for name in slide_names:
                blob = self._bucket.blob(f"{prefix}/input/{name}")
                local_path = os.path.join(local_dir, name)
                blob.download_to_filename(local_path)
                paths.append(local_path)
            return paths
        except Exception as exc:
            raise RuntimeError(f"GCS slide download failed ({gcs_prefix}): {exc}") from exc

    def upload_videos(self, gcs_prefix: str, local_paths: list[str]) -> list[str]:
        """Upload MP4 files to ``{gcs_prefix}/output/``. Returns GCS blob names."""
        try:
            prefix = _strip_gs_prefix(gcs_prefix)
            gcs_paths: list[str] = []
            for path in local_paths:
                name = os.path.basename(path)
                blob = self._bucket.blob(f"{prefix}/output/{name}")
                blob.upload_from_filename(path, content_type="video/mp4")
                gcs_paths.append(f"{prefix}/output/{name}")
                logger.debug("Uploaded video: %s", blob.name)
            return gcs_paths
        except Exception as exc:
            raise RuntimeError(f"GCS video upload failed ({gcs_prefix}): {exc}") from exc

    def upload_status(self, gcs_prefix: str, status: dict) -> None:
        """Write ``status.json`` to GCS for fallback polling."""
        try:
            prefix = _strip_gs_prefix(gcs_prefix)
            blob = self._bucket.blob(f"{prefix}/output/status.json")
            blob.upload_from_string(
                json.dumps(status, ensure_ascii=False),
                content_type="application/json",
            )
        except Exception as exc:
            raise RuntimeError(f"GCS status upload failed ({gcs_prefix}): {exc}") from exc


_GS_SPLIT_PARTS = 3  # gs://bucket/path → split into 4 parts, path index is 3


def _strip_gs_prefix(gcs_prefix: str) -> str:
    """Remove ``gs://bucket-name/`` prefix, returning just the path portion."""
    if gcs_prefix.startswith("gs://"):
        parts = gcs_prefix.split("/", _GS_SPLIT_PARTS)
        return parts[_GS_SPLIT_PARTS] if len(parts) > _GS_SPLIT_PARTS else ""
    return gcs_prefix
