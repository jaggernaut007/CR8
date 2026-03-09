"""Content viewer routes for CR8 pipeline artifacts.

Serves generated content inline for the React SPA's viewer components:
- PDF via iframe (inline Content-Disposition)
- PPT as slide image carousel (PNG listing + individual images)
- Video via HTML5 player (MP4 streaming with Range support)

All routes require authentication via ``AuthMiddleware``.
"""

import logging
import os

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse

from frontend.middleware import JOB_ID_RE

logger = logging.getLogger(__name__)

_OUTPUTS_DIR = os.path.realpath(
    os.path.join(os.path.dirname(__file__), "..", "outputs")
)

router = APIRouter(prefix="/api/view", tags=["viewers"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_path(path: str) -> str | None:
    """Return the resolved path only if it is inside the outputs directory.

    Args:
        path: Absolute or relative path to validate.

    Returns:
        Resolved path if safe, None if it escapes the outputs directory.
    """
    resolved = os.path.realpath(path)
    if resolved.startswith(_OUTPUTS_DIR + os.sep) or resolved == _OUTPUTS_DIR:
        return resolved
    logger.warning("Path traversal guard blocked path: %s", path)
    return None


def _get_completed_result(request: Request, job_id: str) -> dict | None:
    """Return the pipeline result dict for a completed job, or None.

    Args:
        request: FastAPI request (accesses ``app.state.jobs``).
        job_id: 8-char hex job identifier.

    Returns:
        Result dict if job is complete, else None.
    """
    capture = request.app.state.jobs.get(job_id)
    if not capture or capture.status != "complete" or not capture.result:
        return None
    return capture.result


def _validate_job_id(job_id: str) -> JSONResponse | None:
    """Return a 400 JSONResponse if job_id is invalid, else None.

    Args:
        job_id: The job identifier to validate.

    Returns:
        JSONResponse with error if invalid, None if valid.
    """
    if not JOB_ID_RE.match(job_id):
        return JSONResponse({"error": "Invalid job_id"}, status_code=400)
    return None


def _list_mp4_files(video_dir: str) -> list[str]:
    """Return sorted list of MP4 filenames in the given directory.

    Args:
        video_dir: Path to the video output directory.

    Returns:
        Sorted list of .mp4 filenames.
    """
    if not video_dir or not os.path.isdir(video_dir):
        return []
    return sorted(f for f in os.listdir(video_dir) if f.endswith(".mp4"))


# ---------------------------------------------------------------------------
# PDF inline view
# ---------------------------------------------------------------------------

@router.get("/{job_id}/pdf")
async def view_pdf(request: Request, job_id: str):
    """Serve a generated PDF inline for iframe embedding.

    Args:
        request: FastAPI request.
        job_id: 8-char hex job identifier.

    Returns:
        FileResponse with Content-Disposition: inline, or 404.
    """
    error = _validate_job_id(job_id)
    if error:
        return error

    result = _get_completed_result(request, job_id)
    if not result:
        return JSONResponse({"error": "Job not found or not complete"}, status_code=404)

    pdf_path = result.get("pdf_path", "")
    safe = _safe_path(pdf_path) if pdf_path else None
    if not safe or not os.path.exists(safe):
        return JSONResponse({"error": "PDF not found"}, status_code=404)

    logger.info("Serving PDF inline: job=%s", job_id)
    return FileResponse(
        safe,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline"},
    )


# ---------------------------------------------------------------------------
# Slide image listing
# ---------------------------------------------------------------------------

@router.get("/{job_id}/slides")
async def list_slides(request: Request, job_id: str):
    """List available slide images for the PPT carousel.

    Args:
        request: FastAPI request.
        job_id: 8-char hex job identifier.

    Returns:
        JSON with ``slides`` (list of URLs) and ``total`` count.
    """
    error = _validate_job_id(job_id)
    if error:
        return error

    result = _get_completed_result(request, job_id)
    if not result:
        return JSONResponse({"error": "Job not found or not complete"}, status_code=404)

    slide_images = result.get("slide_images", [])
    # Filter to only existing files
    existing = [s for s in slide_images if os.path.exists(s)]

    slides = [
        f"/api/view/{job_id}/slide/{i + 1}"
        for i in range(len(existing))
    ]

    return {"slides": slides, "total": len(existing)}


# ---------------------------------------------------------------------------
# Individual slide image
# ---------------------------------------------------------------------------

@router.get("/{job_id}/slide/{index}")
async def view_slide(request: Request, job_id: str, index: int):
    """Serve an individual slide image by 1-based index.

    Args:
        request: FastAPI request.
        job_id: 8-char hex job identifier.
        index: 1-based slide index.

    Returns:
        FileResponse with PNG image, or 404.
    """
    error = _validate_job_id(job_id)
    if error:
        return error

    result = _get_completed_result(request, job_id)
    if not result:
        return JSONResponse({"error": "Job not found or not complete"}, status_code=404)

    slide_images = result.get("slide_images", [])
    existing = [s for s in slide_images if os.path.exists(s)]

    if index < 1 or index > len(existing):
        return JSONResponse({"error": "Slide not found"}, status_code=404)

    slide_path = existing[index - 1]
    safe = _safe_path(slide_path)
    if not safe:
        return JSONResponse({"error": "Slide not found"}, status_code=404)
    return FileResponse(safe, media_type="image/png")


# ---------------------------------------------------------------------------
# Video listing
# ---------------------------------------------------------------------------

@router.get("/{job_id}/videos")
async def list_videos(request: Request, job_id: str):
    """List available videos with display names and stream URLs.

    Args:
        request: FastAPI request.
        job_id: 8-char hex job identifier.

    Returns:
        JSON with ``videos`` list (each has ``name`` and ``url``).
    """
    error = _validate_job_id(job_id)
    if error:
        return error

    result = _get_completed_result(request, job_id)
    if not result:
        return JSONResponse({"error": "Job not found or not complete"}, status_code=404)

    video_dir = result.get("video_dir", "")
    mp4_files = _list_mp4_files(video_dir)

    videos = []
    for i, filename in enumerate(mp4_files):
        name = filename.rsplit(".", 1)[0].replace("_", " ")
        videos.append({
            "name": name,
            "url": f"/api/view/{job_id}/video/{i}",
        })

    return {"videos": videos}


# ---------------------------------------------------------------------------
# Video streaming
# ---------------------------------------------------------------------------

@router.get("/{job_id}/video/{index}")
async def view_video(request: Request, job_id: str, index: int):
    """Stream a video file by 0-based index.

    Starlette's FileResponse handles HTTP Range requests natively,
    enabling seeking in the HTML5 video player.

    Args:
        request: FastAPI request.
        job_id: 8-char hex job identifier.
        index: 0-based video index.

    Returns:
        FileResponse with video/mp4 content type, or 404.
    """
    error = _validate_job_id(job_id)
    if error:
        return error

    result = _get_completed_result(request, job_id)
    if not result:
        return JSONResponse({"error": "Job not found or not complete"}, status_code=404)

    video_dir = result.get("video_dir", "")
    mp4_files = _list_mp4_files(video_dir)

    if index < 0 or index >= len(mp4_files):
        return JSONResponse({"error": "Video not found"}, status_code=404)

    video_path = os.path.join(video_dir, mp4_files[index])
    safe = _safe_path(video_path)
    if not safe:
        return JSONResponse({"error": "Video not found"}, status_code=404)
    logger.info("Streaming video: job=%s index=%d file=%s", job_id, index, mp4_files[index])
    return FileResponse(safe, media_type="video/mp4")
