"""Job management routes for CR8 pipeline.

Handles file upload, pipeline start, progress polling, cancellation,
and artifact download. All routes require authentication via the
``AuthMiddleware`` in ``frontend/middleware.py``.
"""

import asyncio
import logging
import os
import re
import uuid
import zipfile

from fastapi import APIRouter, Request, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse

from frontend.middleware import JOB_ID_RE, MAX_UPLOAD_BYTES

_FILE_PARAM = File()

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["jobs"])

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
UPLOAD_DIR = os.path.join(PROJECT_ROOT, "uploads")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _collect_output_files(result: dict) -> list[dict]:
    """Build a list of downloadable file descriptors from pipeline result."""
    files = []
    pdf_path = result.get("pdf_path", "")
    if pdf_path and os.path.exists(pdf_path):
        files.append({
            "name": os.path.basename(pdf_path),
            "type": "pdf",
            "size": os.path.getsize(pdf_path),
        })
    ppt_path = result.get("ppt_path", "")
    if ppt_path and os.path.exists(ppt_path):
        files.append({
            "name": os.path.basename(ppt_path),
            "type": "ppt",
            "size": os.path.getsize(ppt_path),
        })
    video_dir = result.get("video_dir", "")
    if video_dir:
        scripts_dir = os.path.join(video_dir, "scripts")
        if os.path.isdir(scripts_dir) and os.listdir(scripts_dir):
            files.append({"name": "video_scripts.zip", "type": "scripts", "size": 0})
        mp4s = (
            [f for f in os.listdir(video_dir) if f.endswith(".mp4")]
            if os.path.isdir(video_dir)
            else []
        )
        if mp4s:
            files.append({"name": "videos.zip", "type": "videos", "size": 0})
    return files


def _zip_directory(dir_path: str, zip_path: str, extension: str | None = None):
    """Create a ZIP archive from a directory, optionally filtering by extension."""
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(dir_path):
            for f in files:
                if extension and not f.endswith(extension):
                    continue
                filepath = os.path.join(root, f)
                arcname = os.path.relpath(filepath, dir_path)
                zf.write(filepath, arcname)


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

@router.post("/upload")
async def upload(file: UploadFile = _FILE_PARAM):
    """Upload a curriculum file (PDF or PPTX) and receive a job ID.

    Validates file extension, magic bytes, and size before saving.

    Args:
        file: The uploaded file.

    Returns:
        JSON with ``job_id`` and ``filename``.
    """
    if not file.filename:
        return JSONResponse({"error": "Please upload a PDF or PPTX file"}, status_code=400)
    ext = file.filename.lower().rsplit(".", 1)[-1] if "." in file.filename else ""
    if ext not in ("pdf", "pptx"):
        return JSONResponse({"error": "Please upload a PDF or PPTX file"}, status_code=400)

    content = await file.read()

    if len(content) > MAX_UPLOAD_BYTES:
        from backend.config import settings as _settings
        return JSONResponse(
            {"error": f"File too large (max {_settings.max_upload_size_mb} MB)"},
            status_code=413,
        )

    if ext == "pdf" and not content.startswith(b"%PDF-"):
        return JSONResponse({"error": "File is not a valid PDF"}, status_code=400)
    if ext == "pptx" and not content.startswith(b"PK\x03\x04"):
        return JSONResponse({"error": "File is not a valid PPTX"}, status_code=400)

    safe_filename = os.path.basename(file.filename)
    safe_filename = re.sub(r"[^\w\-.]", "_", safe_filename) or "upload.pdf"

    job_id = uuid.uuid4().hex[:8]
    job_dir = os.path.join(UPLOAD_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    filepath = os.path.join(job_dir, safe_filename)
    with open(filepath, "wb") as f:
        f.write(content)

    logger.info("Upload: job=%s file=%s size=%d", job_id, safe_filename, len(content))
    return {"job_id": job_id, "filename": safe_filename}


# ---------------------------------------------------------------------------
# Start pipeline
# ---------------------------------------------------------------------------

@router.post("/start")
async def start(request: Request, body: dict):
    """Start the pipeline for a previously uploaded job.

    Args:
        request: FastAPI request (accesses ``app.state.jobs``).
        body: JSON body with ``job_id`` and optional ``formats`` list.

    Returns:
        JSON with ``status: running`` or error.
    """
    from frontend.app import ProgressCapture, _run_pipeline_sync

    jobs = request.app.state.jobs
    job_id = body.get("job_id")
    formats = body.get("formats", ["pdf"])

    if not job_id or not JOB_ID_RE.match(str(job_id)):
        return JSONResponse({"error": "Invalid job_id"}, status_code=400)

    valid_formats = frozenset({"pdf", "ppt", "script", "video"})
    if not isinstance(formats, list) or not all(f in valid_formats for f in formats):
        return JSONResponse({"error": "Invalid formats. Allowed: pdf, ppt, script, video"}, status_code=422)

    for jid, cap in jobs.items():
        if cap.status == "running":
            return JSONResponse(
                {"error": f"A job is already running (job {jid}). Please wait."},
                status_code=409,
            )

    job_dir = os.path.join(UPLOAD_DIR, job_id)
    if not os.path.exists(job_dir):
        return JSONResponse({"error": "Job not found. Upload a file first."}, status_code=404)

    input_files = [
        os.path.join(job_dir, f)
        for f in os.listdir(job_dir)
        if f.lower().endswith((".pdf", ".pptx"))
    ]
    if not input_files:
        return JSONResponse({"error": "No PDF or PPTX found for this job"}, status_code=404)

    capture = ProgressCapture()
    jobs[job_id] = capture
    logger.info("Starting pipeline: job=%s formats=%s files=%d", job_id, formats, len(input_files))

    asyncio.get_running_loop().run_in_executor(
        None, _run_pipeline_sync, input_files, formats, capture
    )

    return {"status": "running"}


# ---------------------------------------------------------------------------
# Progress polling
# ---------------------------------------------------------------------------

@router.get("/progress/{job_id}")
async def progress(request: Request, job_id: str):
    """Poll the current progress of a running pipeline job.

    Args:
        request: FastAPI request.
        job_id: 8-char hex job identifier.

    Returns:
        JSON with status, stage, percent, logs, and other state.
    """
    if not JOB_ID_RE.match(job_id):
        return JSONResponse({"error": "Invalid job_id"}, status_code=400)

    jobs = request.app.state.jobs
    capture = jobs.get(job_id)
    if not capture:
        return JSONResponse({"error": "Job not found"}, status_code=404)

    await _maybe_persist_result(request, job_id, capture)

    return capture.get_state()


async def _maybe_persist_result(request: Request, job_id: str, capture) -> None:
    """Persist pipeline result data to DB on first completion detection.

    Args:
        request: FastAPI request (for DB pool access).
        job_id: Job identifier (short_id from URL).
        capture: ProgressCapture instance.
    """
    if capture.status != "complete" or capture._db_persisted:
        return
    pool = getattr(request.app.state, "db_pool", None)
    user = getattr(request.state, "user", None)
    if not pool or not user:
        return

    capture._db_persisted = True
    result = capture.result or {}

    from backend.services.db_client import get_job_by_short_id, update_job_result

    job = await get_job_by_short_id(pool, job_id)
    if not job:
        return

    await update_job_result(
        pool,
        str(job["id"]),
        "complete",
        result.get("result_meta"),
        pipeline_data={
            "topics": result.get("topics"),
            "gap_summary": result.get("gap_summary"),
            "modules_md": result.get("modules_md"),
            "curriculum_scope": result.get("curriculum_scope"),
        },
    )
    logger.info("Persisted pipeline result to DB: job_id=%s", job_id)


# --- Cancel endpoint ------------------------------------------------------

@router.post("/cancel/{job_id}")
async def cancel(request: Request, job_id: str):
    """Cancel a running pipeline job.

    Args:
        request: FastAPI request.
        job_id: 8-char hex job identifier.

    Returns:
        JSON with ``status: cancelling`` or error.
    """
    if not JOB_ID_RE.match(job_id):
        return JSONResponse({"error": "Invalid job_id"}, status_code=400)

    jobs = request.app.state.jobs
    capture = jobs.get(job_id)
    if not capture:
        return JSONResponse({"error": "Job not found"}, status_code=404)

    if capture.status in ("complete", "error", "cancelled"):
        return JSONResponse(
            {"error": f"Job already {capture.status}"},
            status_code=409,
        )

    capture.request_cancel()
    return {"status": "cancelling"}


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

def _resolve_artifact(result: dict, file_type: str) -> FileResponse | None:
    """Look up and return a FileResponse for the given artifact type.

    Args:
        result: Pipeline result dict with paths.
        file_type: One of ``pdf``, ``ppt``, ``scripts``, ``videos``.

    Returns:
        FileResponse if the artifact exists, else None.
    """
    if file_type == "pdf":
        pdf_path = result.get("pdf_path", "")
        if pdf_path and os.path.exists(pdf_path):
            return FileResponse(pdf_path, filename=os.path.basename(pdf_path))

    elif file_type == "ppt":
        ppt_path = result.get("ppt_path", "")
        if ppt_path and os.path.exists(ppt_path):
            return FileResponse(ppt_path, filename=os.path.basename(ppt_path))

    elif file_type == "scripts":
        video_dir = result.get("video_dir", "")
        if video_dir:
            scripts_dir = os.path.join(video_dir, "scripts")
            if os.path.isdir(scripts_dir):
                zip_path = scripts_dir.rstrip("/") + ".zip"
                _zip_directory(scripts_dir, zip_path)
                return FileResponse(zip_path, filename="video_scripts.zip")

    elif file_type == "videos":
        video_dir = result.get("video_dir", "")
        if video_dir and os.path.isdir(video_dir):
            zip_path = video_dir.rstrip("/") + "_videos.zip"
            _zip_directory(video_dir, zip_path, extension=".mp4")
            return FileResponse(zip_path, filename="videos.zip")

    return None


@router.get("/download/{job_id}/{file_type}")
async def download(request: Request, job_id: str, file_type: str):
    """Download a generated artifact from a completed job.

    Args:
        request: FastAPI request.
        job_id: 8-char hex job identifier.
        file_type: One of ``pdf``, ``ppt``, ``scripts``, ``videos``.

    Returns:
        FileResponse with the artifact, or 404.
    """
    if not JOB_ID_RE.match(job_id):
        return JSONResponse({"error": "Invalid job_id"}, status_code=400)

    valid_types = frozenset({"pdf", "ppt", "scripts", "videos"})
    if file_type not in valid_types:
        return JSONResponse({"error": "Invalid file type"}, status_code=400)

    jobs = request.app.state.jobs
    capture = jobs.get(job_id)
    if not capture or not capture.result:
        return JSONResponse({"error": "Job not found or not complete"}, status_code=404)

    response = _resolve_artifact(capture.result, file_type)
    if response is not None:
        return response
    return JSONResponse({"error": "File not found"}, status_code=404)


# ---------------------------------------------------------------------------
# Job list (DB-backed)
# ---------------------------------------------------------------------------

@router.get("/jobs")
async def list_jobs(request: Request):
    """List jobs for the current user from the database.

    Args:
        request: FastAPI request (needs ``db_pool`` and authenticated user).

    Returns:
        JSON list of jobs, or 503 if DB unavailable.
    """
    pool = getattr(request.app.state, "db_pool", None)
    if pool is None:
        return JSONResponse({"error": "Database not available"}, status_code=503)

    from backend.services import db_client as dbc

    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    user_id = user.get("user_id", "")
    if user_id == "legacy-session":
        return JSONResponse(
            {"error": "JWT authentication required for job list"}, status_code=403
        )

    try:
        limit = min(int(request.query_params.get("limit", "20")), 100)
        offset = int(request.query_params.get("offset", "0"))
    except ValueError:
        return JSONResponse({"error": "Invalid limit or offset"}, status_code=400)
    return await dbc.list_jobs(pool, user_id, limit=limit, offset=offset)


@router.get("/jobs/{job_id}")
async def get_job(request: Request, job_id: str):
    """Get a single job by ID from the database.

    Args:
        request: FastAPI request.
        job_id: UUID string of the job.

    Returns:
        JSON job dict or 404.
    """
    pool = getattr(request.app.state, "db_pool", None)
    if pool is None:
        return JSONResponse({"error": "Database not available"}, status_code=503)

    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    user_id = user.get("user_id", "")
    if user_id == "legacy-session":
        return JSONResponse(
            {"error": "JWT authentication required"}, status_code=403
        )

    from backend.services import db_client as dbc

    job = await dbc.get_job(pool, job_id)
    if not job or str(job.get("user_id", "")) != user_id:
        return JSONResponse({"error": "Job not found"}, status_code=404)
    return job
