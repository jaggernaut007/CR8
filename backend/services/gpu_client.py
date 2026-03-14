"""HTTP client for CR8 video generation services (GPU and CPU-video).

Supports a 2-tier fallback chain:
    Tier 1: GPU primary (europe-west4)
    Tier 2: CPU-video (europe-west2)

Usage:
    from backend.services.gpu_client import VideoServiceClient

    client = VideoServiceClient()
    video_job_id = client.submit_job("job123", "gs://cr8-jobs/job123")
    result = client.poll_until_complete(video_job_id)
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

import requests

from backend.config import settings

logger = logging.getLogger(__name__)

# Polling defaults
_DEFAULT_POLL_INTERVAL = 10  # seconds
_DEFAULT_POLL_TIMEOUT = 3600  # 1 hour

# Timeouts tuned for Cloud Run cold starts
_HEALTH_TIMEOUT = 10  # Cloud Run cold start (2-5s) + app startup (3-5s)
_SUBMIT_TIMEOUT = 60  # cold start + request processing
_POLL_TIMEOUT = 15  # service is already warm during polling
_CANCEL_TIMEOUT = 10
_HTTP_OK = 200


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


class VideoServiceClient:
    """Talks to CR8 video services (GPU or CPU-video) over HTTP.

    Iterates through an ordered list of service tiers on infrastructure
    failures. Once a tier accepts a job, all subsequent polling stays
    on that tier.
    """

    def __init__(
        self,
        base_url: str | None = None,
        cpu_video_url: str | None = None,
    ):
        self._tiers = _build_tier_list(base_url, cpu_video_url)
        self._current_tier_idx = 0
        self.base_url = self._tiers[0] if self._tiers else ""

    def _headers(self) -> dict[str, str]:
        """Build request headers, including auth token when available."""
        headers: dict[str, str] = {"Content-Type": "application/json"}
        token = _get_identity_token(self.base_url)
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _try_next_tier(self) -> bool:
        """Advance to the next tier. Returns True if a new tier is available."""
        next_idx = self._current_tier_idx + 1
        if next_idx < len(self._tiers):
            self._current_tier_idx = next_idx
            self.base_url = self._tiers[next_idx]
            logger.warning("Falling back to tier %d: %s", next_idx + 1, self.base_url)
            return True
        return False

    def is_available(self) -> bool:
        """Return True if any video service healthcheck responds 200.

        Tries each tier in order.
        """
        for idx, url in enumerate(self._tiers):
            try:
                resp = requests.get(
                    f"{url}/health",
                    headers=self._headers_for(url),
                    timeout=_HEALTH_TIMEOUT,
                )
                if resp.status_code == _HTTP_OK:
                    self._current_tier_idx = idx
                    self.base_url = url
                    return True
            except Exception:
                continue
        return False

    def submit_job(self, job_id: str, gcs_prefix: str) -> str:
        """Submit a video generation job. Returns the ``video_job_id``.

        Tries each tier on infrastructure errors (ConnectionError, Timeout, 5xx).
        """
        last_exc = None
        for idx in range(self._current_tier_idx, len(self._tiers)):
            url = self._tiers[idx]
            try:
                self._current_tier_idx = idx
                self.base_url = url
                return self._do_submit(job_id, gcs_prefix)
            except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as exc:
                last_exc = exc
                logger.warning("Tier %d (%s) failed: %s", idx + 1, url, exc)
                continue
        raise last_exc or RuntimeError("No video service tiers configured")

    def _do_submit(self, job_id: str, gcs_prefix: str) -> str:
        """POST to the current tier's video-jobs endpoint."""
        resp = requests.post(
            f"{self.base_url}/api/v1/video-jobs",
            json={"job_id": job_id, "gcs_prefix": gcs_prefix},
            headers=self._headers(),
            timeout=_SUBMIT_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        video_job_id = data.get("video_job_id")
        if not video_job_id:
            raise RuntimeError(
                "GPU service response missing 'video_job_id': %r" % data
            )
        logger.info("Video job submitted to %s: %s", self.base_url, video_job_id)
        return video_job_id

    def cancel_job(self, video_job_id: str) -> bool:
        """Cancel a running video job. Best-effort — returns True on success."""
        try:
            resp = requests.post(
                f"{self.base_url}/api/v1/video-jobs/{video_job_id}/cancel",
                headers=self._headers(),
                timeout=_CANCEL_TIMEOUT,
            )
            if resp.status_code in (200, 409):
                logger.info("Video job cancel sent: %s (status=%s)", video_job_id, resp.status_code)
                return True
            resp.raise_for_status()
            return True
        except Exception:
            logger.warning("Failed to cancel video job %s", video_job_id, exc_info=True)
            return False

    def poll_until_complete(
        self,
        video_job_id: str,
        interval: int = _DEFAULT_POLL_INTERVAL,
        timeout: int = _DEFAULT_POLL_TIMEOUT,
        cancel_check: Callable[[], None] | None = None,
    ) -> dict:
        """Poll the video service until the job completes or fails.

        Prints structured ``[Video] GPU_*`` lines so the CPU-side
        ProgressCapture can track video-stage progress.

        Args:
            cancel_check: Optional callable invoked each poll iteration.
                Should raise if cancellation is requested.

        Returns:
            The final job status dict on success.

        Raises:
            RuntimeError: If the service reports an error or is cancelled.
            TimeoutError: If the job does not complete within *timeout* seconds.
        """
        elapsed = 0
        while elapsed < timeout:
            if cancel_check:
                try:
                    cancel_check()
                except Exception:
                    self.cancel_job(video_job_id)
                    raise

            resp = requests.get(
                f"{self.base_url}/api/v1/video-jobs/{video_job_id}",
                headers=self._headers(),
                timeout=_POLL_TIMEOUT,
            )
            resp.raise_for_status()
            status = resp.json()

            job_status = status.get("status")
            if job_status == "complete":
                logger.info("Video job %s complete", video_job_id)
                return status
            if job_status == "error":
                error_msg = status.get("error", "unknown error")
                raise RuntimeError(f"Video job failed: {error_msg}")
            if job_status == "cancelled":
                raise RuntimeError("Video job was cancelled")

            _emit_progress(status)

            time.sleep(interval)
            elapsed += interval

        raise TimeoutError(
            f"Video job {video_job_id} not complete after {timeout}s"
        )

    def _headers_for(self, url: str) -> dict[str, str]:
        """Build headers with an identity token scoped to a specific URL."""
        headers: dict[str, str] = {"Content-Type": "application/json"}
        token = _get_identity_token(url)
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers


# Backward-compatible alias
GPUVideoClient = VideoServiceClient


def _build_tier_list(
    base_url: str | None,
    cpu_video_url: str | None,
) -> list[str]:
    """Build an ordered list of service URLs, skipping empty values."""
    candidates = [
        (base_url or settings.gpu_service_url).rstrip("/"),
        (cpu_video_url or settings.cpu_video_service_url).rstrip("/"),
    ]
    return [url for url in candidates if url]


def _emit_progress(status: dict) -> None:
    """Print structured progress lines for ProgressCapture."""
    progress = status.get("progress", {})
    phase = progress.get("phase", "unknown")
    pct = progress.get("percent", 0)
    print(f"[Video] GPU: {phase} ({pct}%)")  # noqa: T201

    completed = progress.get("completed_videos")
    total_v = progress.get("total_videos")
    if completed is not None and total_v is not None:
        print(f"[Video] GPU_COMPOSE: {completed}/{total_v}")  # noqa: T201

    current_topic = progress.get("current_topic")
    total_topics = progress.get("total_topics")
    if current_topic is not None and total_topics is not None:
        print(f"[Video] GPU_TTS: {current_topic}/{total_topics}")  # noqa: T201

    elapsed_s = progress.get("elapsed_s") or status.get("elapsed_s")
    eta_s = progress.get("eta_s")
    if elapsed_s is not None:
        eta_str = str(eta_s) if eta_s is not None else "?"
        print(f"[Video] GPU_TIME: elapsed={elapsed_s} eta={eta_str}")  # noqa: T201
