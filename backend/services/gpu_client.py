"""HTTP client for the CR8 GPU video generation service.

Usage:
    from backend.services.gpu_client import GPUVideoClient

    gpu = GPUVideoClient()
    video_job_id = gpu.submit_job("job123", "gs://cr8-jobs/job123")
    result = gpu.poll_until_complete(video_job_id)
"""

from __future__ import annotations

import logging
import time

import requests

from backend.config import settings

logger = logging.getLogger(__name__)

# Polling defaults
_DEFAULT_POLL_INTERVAL = 10  # seconds
_DEFAULT_POLL_TIMEOUT = 3600  # 1 hour


def _get_identity_token(audience: str) -> str | None:
    """Fetch a Cloud Run identity token for service-to-service auth.

    Returns ``None`` when running outside GCP (local development).
    """
    try:
        import google.auth.transport.requests
        import google.oauth2.id_token

        auth_req = google.auth.transport.requests.Request()
        return google.oauth2.id_token.fetch_id_token(auth_req, audience)
    except Exception:
        logger.debug("Could not fetch identity token (expected in local dev)")
        return None


class GPUVideoClient:
    """Talks to the CR8 GPU video service over HTTP.

    Supports automatic failover to a fallback GPU service (e.g. europe-west1)
    when the primary (e.g. europe-west4) is unavailable.
    """

    def __init__(self, base_url: str | None = None, fallback_url: str | None = None):
        self._primary_url = (base_url or settings.gpu_service_url).rstrip("/")
        self._fallback_url = (fallback_url or settings.gpu_fallback_url).rstrip("/") or ""
        self.base_url = self._primary_url

    def _headers(self) -> dict[str, str]:
        """Build request headers, including auth token when available."""
        headers: dict[str, str] = {"Content-Type": "application/json"}
        token = _get_identity_token(self.base_url)
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _try_fallback(self) -> bool:
        """Switch to the fallback URL if available. Returns True if switched."""
        if self._fallback_url and self.base_url != self._fallback_url:
            logger.warning(
                "Primary GPU service unavailable, trying fallback: %s",
                self._fallback_url,
            )
            self.base_url = self._fallback_url
            return True
        return False

    def is_available(self) -> bool:
        """Return True if the GPU service healthcheck responds 200.

        Tries the primary first, then the fallback.
        """
        try:
            resp = requests.get(
                f"{self.base_url}/health",
                headers=self._headers(),
                timeout=5,
            )
            if resp.status_code == 200:
                return True
        except Exception:
            pass

        # Try fallback
        if self._try_fallback():
            try:
                resp = requests.get(
                    f"{self.base_url}/health",
                    headers=self._headers(),
                    timeout=5,
                )
                return resp.status_code == 200
            except Exception:
                pass

        return False

    def submit_job(self, job_id: str, gcs_prefix: str) -> str:
        """Submit a video generation job. Returns the ``video_job_id``.

        Falls back to the secondary GPU region on connection/server errors.
        """
        try:
            return self._do_submit(job_id, gcs_prefix)
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as exc:
            if self._try_fallback():
                logger.info("Retrying submit on fallback after: %s", exc)
                return self._do_submit(job_id, gcs_prefix)
            raise

    def _do_submit(self, job_id: str, gcs_prefix: str) -> str:
        resp = requests.post(
            f"{self.base_url}/api/v1/video-jobs",
            json={"job_id": job_id, "gcs_prefix": gcs_prefix},
            headers=self._headers(),
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        video_job_id = data["video_job_id"]
        logger.info("GPU job submitted to %s: %s", self.base_url, video_job_id)
        return video_job_id

    def cancel_job(self, video_job_id: str) -> bool:
        """Cancel a running GPU video job. Best-effort — returns True on success."""
        try:
            resp = requests.post(
                f"{self.base_url}/api/v1/video-jobs/{video_job_id}/cancel",
                headers=self._headers(),
                timeout=10,
            )
            if resp.status_code in (200, 409):
                logger.info("GPU job cancel sent: %s (status=%s)", video_job_id, resp.status_code)
                return True
            resp.raise_for_status()
            return True
        except Exception:
            logger.warning("Failed to cancel GPU job %s", video_job_id, exc_info=True)
            return False

    def poll_until_complete(
        self,
        video_job_id: str,
        interval: int = _DEFAULT_POLL_INTERVAL,
        timeout: int = _DEFAULT_POLL_TIMEOUT,
        cancel_check: "callable | None" = None,
    ) -> dict:
        """Poll the GPU service until the job completes or fails.

        Prints structured ``[Video] GPU_*`` lines so the CPU-side
        ProgressCapture can track video-stage progress.

        Args:
            cancel_check: Optional callable invoked each poll iteration.
                Should raise if cancellation is requested.

        Returns:
            The final job status dict on success.

        Raises:
            RuntimeError: If the GPU service reports an error or is cancelled.
            TimeoutError: If the job does not complete within *timeout* seconds.
        """
        elapsed = 0
        while elapsed < timeout:
            # Check for user cancellation — cancel the GPU job before re-raising
            if cancel_check:
                try:
                    cancel_check()
                except Exception:
                    self.cancel_job(video_job_id)
                    raise

            resp = requests.get(
                f"{self.base_url}/api/v1/video-jobs/{video_job_id}",
                headers=self._headers(),
                timeout=15,
            )
            resp.raise_for_status()
            status = resp.json()

            job_status = status.get("status")
            if job_status == "complete":
                logger.info("GPU job %s complete", video_job_id)
                return status
            if job_status == "error":
                error_msg = status.get("error", "unknown error")
                raise RuntimeError(f"GPU video job failed: {error_msg}")
            if job_status == "cancelled":
                raise RuntimeError("GPU video job was cancelled")

            # Emit structured progress lines for ProgressCapture
            progress = status.get("progress", {})
            phase = progress.get("phase", "unknown")
            pct = progress.get("percent", 0)
            print(f"[Video] GPU: {phase} ({pct}%)")

            # Per-video compose progress
            completed = progress.get("completed_videos")
            total_v = progress.get("total_videos")
            if completed is not None and total_v is not None:
                print(f"[Video] GPU_COMPOSE: {completed}/{total_v}")

            # TTS topic progress
            current_topic = progress.get("current_topic")
            total_topics = progress.get("total_topics")
            if current_topic is not None and total_topics is not None:
                print(f"[Video] GPU_TTS: {current_topic}/{total_topics}")

            # Elapsed/ETA
            elapsed_s = progress.get("elapsed_s") or status.get("elapsed_s")
            eta_s = progress.get("eta_s")
            if elapsed_s is not None:
                eta_str = str(eta_s) if eta_s is not None else "?"
                print(f"[Video] GPU_TIME: elapsed={elapsed_s} eta={eta_str}")

            time.sleep(interval)
            elapsed += interval

        raise TimeoutError(
            f"GPU video job {video_job_id} not complete after {timeout}s"
        )
