"""CR8 GPU Video Generation Service.

Lightweight FastAPI microservice that runs Kokoro TTS + ffmpeg video
composition on an NVIDIA L4 GPU. Deployed to Cloud Run with
``--gpu=1 --gpu-type=nvidia-l4``.

Endpoints:
    GET  /health                      — GPU status + model info
    POST /api/v1/video-jobs           — submit a video generation job
    GET  /api/v1/video-jobs/{id}      — poll job status/progress
"""

from __future__ import annotations

import logging
import threading
import uuid

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from gpu_service.worker import _jobs, _jobs_lock, cancel_job, get_job, run_video_job

app = FastAPI(title="CR8 GPU Video Service", version="0.1.0")
logger = logging.getLogger(__name__)

# Track active jobs to enforce max_concurrent_jobs
_active_count = 0
_active_lock = threading.Lock()


# ---- Request/Response models ------------------------------------------------


class VideoJobRequest(BaseModel):
    job_id: str
    gcs_prefix: str


class VideoJobResponse(BaseModel):
    video_job_id: str
    status: str


class JobProgress(BaseModel):
    phase: str
    percent: int
    current_topic: int | None = None
    total_topics: int | None = None
    elapsed_s: int | None = None
    eta_s: int | None = None
    completed_videos: int | None = None
    total_videos: int | None = None


class JobStatusResponse(BaseModel):
    video_job_id: str
    status: str
    progress: JobProgress | None = None
    output_paths: list[str] | None = None
    error: str | None = None
    warnings: list[str] | None = None
    elapsed_s: int | None = None


# ---- Endpoints ---------------------------------------------------------------


@app.get("/health")
async def health():
    """Lightweight health check — must respond fast for Cloud Run startup probe."""
    return {"status": "ok"}


@app.get("/health/detailed")
async def health_detailed():
    """Full diagnostics including GPU detection and encoder probe (slow on first call)."""
    gpu_info = "none"
    try:
        import torch

        if torch.cuda.is_available():
            gpu_info = torch.cuda.get_device_name(0)
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            gpu_info = "apple-mps"
    except ImportError:
        gpu_info = "torch-not-installed"

    from backend.services.gpu_utils import get_ffmpeg_encoder

    encoder = get_ffmpeg_encoder()
    return {"status": "ok", "gpu": gpu_info, "ffmpeg_encoder": encoder}


@app.get("/debug/encoder")
async def debug_encoder():
    """Diagnostic endpoint — test each encoder and return raw ffmpeg output."""
    import glob
    import os
    import subprocess
    import tempfile

    results = {}

    # Check for NVENC libraries
    nvenc_libs = glob.glob("/usr/lib/**/libnvidia-encode*", recursive=True)
    nvenc_libs += glob.glob("/usr/local/lib/**/libnvidia-encode*", recursive=True)
    results["libnvidia_encode_paths"] = nvenc_libs or "NOT FOUND"

    # Check NVIDIA_DRIVER_CAPABILITIES
    results["NVIDIA_DRIVER_CAPABILITIES"] = os.environ.get("NVIDIA_DRIVER_CAPABILITIES", "unset")
    results["NVIDIA_VISIBLE_DEVICES"] = os.environ.get("NVIDIA_VISIBLE_DEVICES", "unset")

    # List all nvidia libs mounted
    try:
        nvidia_libs = subprocess.run(
            ["find", "/usr", "-name", "libnvidia*", "-type", "f"],
            capture_output=True, text=True, timeout=5, check=False,
        )
        results["nvidia_libs"] = nvidia_libs.stdout.strip().split("\n") if nvidia_libs.stdout.strip() else []
    except Exception as e:
        results["nvidia_libs"] = str(e)

    # Test each encoder
    for enc in ("h264_nvenc", "h264_videotoolbox", "h264_qsv", "h264_amf", "libx264"):
        fd, tmp = tempfile.mkstemp(suffix=".mp4")
        os.close(fd)
        try:
            r = subprocess.run(
                ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                 "-f", "lavfi", "-i", "color=c=black:s=64x64:d=0.04",
                 "-frames:v", "1", "-c:v", enc, tmp],
                capture_output=True, text=True, timeout=15, check=False,
            )
            size = os.path.getsize(tmp) if os.path.exists(tmp) else 0
            results[enc] = {
                "returncode": r.returncode,
                "file_size": size,
                "ok": r.returncode == 0 and size > 0,
                "stderr": r.stderr.strip()[:500] if r.stderr else "",
            }
        except Exception as e:
            results[enc] = {"error": str(e)}
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    return results


@app.post("/api/v1/video-jobs", status_code=202, response_model=VideoJobResponse)
async def create_video_job(req: VideoJobRequest):
    global _active_count

    from gpu_service.config import gpu_settings

    with _active_lock:
        if _active_count >= gpu_settings.max_concurrent_jobs:
            raise HTTPException(
                status_code=429,
                detail=f"Max concurrent jobs ({gpu_settings.max_concurrent_jobs}) reached",
            )
        _active_count += 1

    video_job_id = f"vj_{req.job_id}_{uuid.uuid4().hex[:6]}"
    logger.info("Accepted video job: %s (gcs_prefix=%s)", video_job_id, req.gcs_prefix)

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
    job = get_job(video_job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatusResponse(**job)


@app.post("/api/v1/video-jobs/{video_job_id}/cancel")
async def cancel_video_job(video_job_id: str):
    """Cancel a running video job. Takes effect at the next phase boundary."""
    job = get_job(video_job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] in ("complete", "error", "cancelled"):
        return {"video_job_id": video_job_id, "status": job["status"], "message": "Job already finished"}
    if cancel_job(video_job_id):
        return {"video_job_id": video_job_id, "status": "cancelling"}
    raise HTTPException(status_code=409, detail="Job cannot be cancelled")
