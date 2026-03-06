"""CR8 CPU Video Generation Service.

Lightweight FastAPI microservice that runs Kokoro TTS + ffmpeg video
composition on CPU only. Deployed to Cloud Run with ``--cpu=8 --memory=32Gi``.

Same API contract as ``gpu_service/app.py`` so ``VideoServiceClient``
can route to it as a fallback tier.

Endpoints:
    GET  /health                           — service status
    POST /api/v1/video-jobs                — submit a video generation job
    GET  /api/v1/video-jobs/{id}           — poll job status/progress
    POST /api/v1/video-jobs/{id}/cancel    — cancel a running job
"""

from __future__ import annotations

import logging
import threading
import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from cpu_video_service.worker import _jobs, _jobs_lock, cancel_job, get_job, run_video_job

app = FastAPI(title="CR8 CPU Video Service", version="0.1.0")
logger = logging.getLogger(__name__)

# Track active jobs to enforce max_concurrent_jobs
_active_count = 0
_active_lock = threading.Lock()


# ---- Request/Response models ------------------------------------------------


class VideoJobRequest(BaseModel):
    """Incoming video generation request from the CPU pipeline service."""

    job_id: str
    gcs_prefix: str


class VideoJobResponse(BaseModel):
    """Returned immediately on job creation (HTTP 202)."""

    video_job_id: str
    status: str


class JobProgress(BaseModel):
    """Real-time progress update for a running video job."""

    phase: str
    percent: int
    current_topic: int | None = None
    total_topics: int | None = None
    elapsed_s: int | None = None
    eta_s: int | None = None
    completed_videos: int | None = None
    total_videos: int | None = None


class JobStatusResponse(BaseModel):
    """Full job status returned by the polling endpoint."""

    video_job_id: str
    status: str
    progress: JobProgress | None = None
    output_paths: list[str] | None = None
    error: str | None = None
    warnings: list[str] | None = None
    elapsed_s: int | None = None


class CancelJobResponse(BaseModel):
    """Response from the cancel endpoint."""

    video_job_id: str
    status: str
    message: str | None = None


# ---- Endpoints ---------------------------------------------------------------


@app.get("/health")
async def health():
    """Lightweight health check for Cloud Run startup probe."""
    return {"status": "ok", "type": "cpu-video"}


@app.post("/api/v1/video-jobs", status_code=202, response_model=VideoJobResponse)
async def create_video_job(req: VideoJobRequest):
    """Accept a video generation job and run it in a background thread."""
    global _active_count

    from cpu_video_service.config import cpu_video_settings

    with _active_lock:
        if _active_count >= cpu_video_settings.max_concurrent_jobs:
            raise HTTPException(
                status_code=429,
                detail=f"Max concurrent jobs ({cpu_video_settings.max_concurrent_jobs}) reached",
            )
        _active_count += 1

    video_job_id = f"vj_{req.job_id}_{uuid.uuid4().hex[:6]}"
    logger.info("Accepted CPU video job: %s (gcs_prefix=%s)", video_job_id, req.gcs_prefix)

    # Register job BEFORE starting thread so polling finds it immediately
    with _jobs_lock:
        _jobs[video_job_id] = {
            "video_job_id": video_job_id,
            "status": "accepted",
            "progress": {"phase": "accepted", "percent": 0},
        }

    def _run_and_release():
        global _active_count
        try:
            run_video_job(video_job_id, req.gcs_prefix)
        finally:
            with _active_lock:
                _active_count -= 1

    t = threading.Thread(target=_run_and_release, daemon=True)
    t.start()

    return VideoJobResponse(video_job_id=video_job_id, status="accepted")


@app.get("/api/v1/video-jobs/{video_job_id}", response_model=JobStatusResponse)
async def get_video_job_status(video_job_id: str) -> JobStatusResponse:
    """Poll the current status and progress of a video job."""
    job = get_job(video_job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatusResponse(**job)


@app.post("/api/v1/video-jobs/{video_job_id}/cancel", response_model=CancelJobResponse)
async def cancel_video_job(video_job_id: str) -> CancelJobResponse:
    """Cancel a running video job. Takes effect at the next phase boundary."""
    job = get_job(video_job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] in ("complete", "error", "cancelled"):
        return CancelJobResponse(
            video_job_id=video_job_id, status=job["status"], message="Job already finished",
        )
    if cancel_job(video_job_id):
        return CancelJobResponse(video_job_id=video_job_id, status="cancelling")
    raise HTTPException(status_code=409, detail="Job cannot be cancelled")
