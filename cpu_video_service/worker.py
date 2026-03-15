"""Background worker: downloads from GCS, runs TTS + compose on CPU, uploads results.

Reuses ``backend.services.tts_engine.TTSEngine`` and
``backend.services.video_builder._compose_video`` — identical logic to
``gpu_service/worker.py`` but forces CPU device and libx264 encoding.
"""

from __future__ import annotations

import logging
import os
import tempfile
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TypedDict

from cpu_video_service.config import cpu_video_settings
from cpu_video_service.gcs_client import CPUGCSClient

logger = logging.getLogger(__name__)


def _export_slides_from_pptx(
    gcs: CPUGCSClient,
    gcs_prefix: str,
    pptx_name: str,
    workdir: str,
    slide_dir: str,
) -> list[str]:
    """Download PPTX from GCS and export slide PNGs via LibreOffice.

    Args:
        gcs: GCS client instance.
        gcs_prefix: GCS job prefix.
        pptx_name: Filename of the PPTX in GCS input folder.
        workdir: Temporary working directory.
        slide_dir: Output directory for slide PNGs.

    Returns:
        Sorted list of exported slide image paths.
    """
    from backend.services.file_parser import export_slides_as_images

    logger.info("No pre-exported slides — converting PPTX on CPU worker: %s", pptx_name)
    pptx_path = gcs.download_pptx(gcs_prefix, pptx_name, workdir)
    images = export_slides_as_images(pptx_path, slide_dir, dpi=144)
    logger.info("Exported %d slide images from PPTX", len(images))
    return images


# In-memory job store (single instance, max 1 concurrent job)
_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()
# Per-job cancellation events
_cancel_events: dict[str, threading.Event] = {}


class JobContext(TypedDict):
    """Shared context passed between pipeline phases."""

    video_job_id: str
    gcs_prefix: str
    gcs: CPUGCSClient
    job_start: float


def get_job(video_job_id: str) -> dict | None:
    """Return a snapshot of the job state, or None if not found."""
    with _jobs_lock:
        job = _jobs.get(video_job_id)
        return dict(job) if job else None


def cancel_job(video_job_id: str) -> bool:
    """Request cancellation of a running job. Returns True if job was found."""
    evt = _cancel_events.get(video_job_id)
    if evt:
        evt.set()
        _update_job(video_job_id, status="cancelling",
                    progress={"phase": "cancelling", "percent": 0})
        logger.info("Cancellation requested for %s", video_job_id)
        return True
    return False


def _is_cancelled(video_job_id: str) -> bool:
    """Check if a job has been flagged for cancellation."""
    evt = _cancel_events.get(video_job_id)
    return evt is not None and evt.is_set()


def _update_job(video_job_id: str, **kwargs: object) -> None:
    """Update in-memory job state."""
    with _jobs_lock:
        if video_job_id in _jobs:
            _jobs[video_job_id].update(kwargs)


def _elapsed(ctx: JobContext) -> int:
    """Seconds since job started."""
    return int(time.monotonic() - ctx["job_start"])


def _estimate_eta(pct: int, elapsed_s: int) -> int | None:
    """Estimate remaining seconds from current percent and elapsed time."""
    if pct <= 0:
        return None
    return int(elapsed_s / pct * (100 - pct))


def run_video_job(video_job_id: str, gcs_prefix: str) -> None:
    """Execute a full video generation job on CPU (runs in a background thread).

    Phases:
        1. Download manifest + slide images from GCS
        2. TTS synthesis (Kokoro on CPU — sequential)
        3. Video composition (ffmpeg libx264 — parallel)
        4. Upload MP4s to GCS
    """
    _cancel_events[video_job_id] = threading.Event()

    with _jobs_lock:
        _jobs[video_job_id] = {
            "video_job_id": video_job_id,
            "status": "downloading",
            "progress": {"phase": "downloading", "percent": 0},
        }

    gcs = CPUGCSClient(cpu_video_settings.gcs_bucket)
    ctx: JobContext = {
        "video_job_id": video_job_id,
        "gcs_prefix": gcs_prefix,
        "gcs": gcs,
        "job_start": time.monotonic(),
    }

    try:
        with tempfile.TemporaryDirectory() as workdir:
            _execute_pipeline(ctx, workdir)
    except InterruptedError:
        _handle_cancellation(ctx)
    except Exception as exc:
        _handle_error(ctx, exc)
    finally:
        _cancel_events.pop(video_job_id, None)


def _execute_pipeline(ctx: JobContext, workdir: str) -> None:
    """Run the 4-phase video pipeline inside a temp directory."""
    # Phase 1: Download
    manifest, slide_images = _phase_download(ctx, workdir)
    topics = manifest["topics"]
    scripts = manifest["scripts"]
    config = manifest.get("config", {})
    total = len(topics)

    # Pad scripts if fewer than topics
    if scripts and len(scripts) < total:
        scripts = list(scripts) + [scripts[-1]] * (total - len(scripts))

    output_dir = os.path.join(workdir, "output")
    os.makedirs(output_dir, exist_ok=True)

    scripts_dir = os.path.join(output_dir, "scripts")
    os.makedirs(scripts_dir, exist_ok=True)

    # Phase 2: TTS
    tts_data: _TtsData = {
        "topics": topics, "scripts": scripts, "slide_images": slide_images,
        "topic_slide_map": manifest.get("topic_slide_map"), "config": config,
        "workdir": workdir, "output_dir": output_dir, "scripts_dir": scripts_dir,
    }
    tts_results, errors = _phase_tts(ctx, tts_data)

    # Phase 3: Compose
    video_paths, compose_errors = _phase_compose(ctx, tts_results, config)
    errors.extend(compose_errors)

    # Phase 4: Upload
    _phase_upload(ctx, video_paths, errors, total)


class _TtsData(TypedDict):
    """Input data for the TTS phase."""

    topics: list[dict]
    scripts: list[str]
    slide_images: list[str]
    topic_slide_map: dict[str, list[int]] | None
    config: dict
    workdir: str
    output_dir: str
    scripts_dir: str


def _phase_download(ctx: JobContext, workdir: str) -> tuple[dict, list[str]]:
    """Download manifest and slide images from GCS."""
    vid = ctx["video_job_id"]
    gcs = ctx["gcs"]
    gcs_prefix = ctx["gcs_prefix"]

    _update_job(vid, status="downloading",
                progress={"phase": "downloading", "percent": 2})

    manifest = gcs.download_manifest(gcs_prefix, workdir)
    slide_dir = os.path.join(workdir, "slides")
    slide_names = manifest["slide_images"]
    pptx_name = manifest.get("pptx_name")

    if slide_names:
        slide_images = gcs.download_slides(gcs_prefix, slide_names, slide_dir)
    elif pptx_name:
        slide_images = _export_slides_from_pptx(gcs, gcs_prefix, pptx_name, workdir, slide_dir)
    else:
        slide_images = []

    if not slide_images:
        raise RuntimeError("No slide images available (no PNGs or PPTX provided)")

    logger.info("Downloaded %d slides for job %s", len(slide_images), vid)
    return manifest, slide_images


def _phase_tts(
    ctx: JobContext, data: _TtsData,
) -> tuple[list[tuple | None], list[str]]:
    """Run sequential Kokoro TTS on CPU for each topic."""
    from backend.services.tts_engine import TTSEngine

    vid = ctx["video_job_id"]
    topics = data["topics"]
    total = len(topics)
    config = data["config"]
    voice = config.get("voice", cpu_video_settings.kokoro_voice)
    lang = config.get("lang", cpu_video_settings.kokoro_lang)

    _update_job(vid, status="tts",
                progress={"phase": "tts", "current_topic": 0, "total_topics": total,
                          "percent": 5, "elapsed_s": _elapsed(ctx)})

    os.environ["VIDEO_DEVICE"] = "cpu"
    engine = TTSEngine(voice=voice, lang=lang)

    tts_results: list[tuple | None] = []
    errors: list[str] = []

    for i in range(total):
        if _is_cancelled(vid):
            raise InterruptedError("Job cancelled during TTS")

        result = _synthesize_topic(ctx, data, engine, i)
        if isinstance(result, str):
            errors.append(result)
            tts_results.append(None)
        else:
            tts_results.append(result)

        _update_tts_progress(ctx, i + 1, total)

    logger.info("TTS phase complete for %d topics", total)
    return tts_results, errors


def _synthesize_topic(
    ctx: JobContext, data: _TtsData, engine: object, idx: int,
) -> tuple | str:
    """Synthesize TTS for a single topic. Returns result tuple or error string."""
    from backend.services.script_parser import parse_script
    from backend.services.video_builder import _get_topic_images, _slugify

    topics = data["topics"]
    scripts = data["scripts"]
    slide_images = data["slide_images"]
    topic_slide_map = data["topic_slide_map"]
    output_dir = data["output_dir"]
    scripts_dir = data["scripts_dir"]
    workdir = data["workdir"]

    slug = _slugify(topics[idx]["name"])
    prefix_num = f"{idx + 1:02d}"
    video_path = os.path.join(output_dir, f"{prefix_num}_{slug}_slide.mp4")
    script_path = os.path.join(scripts_dir, f"{prefix_num}_{slug}_slide.txt")

    with open(script_path, "w", encoding="utf-8") as f:
        f.write(scripts[idx])

    topic_name = topics[idx]["name"]
    topic_images = _get_topic_images(topic_name, slide_images, topic_slide_map)

    try:
        segments = parse_script(scripts[idx], num_slides=len(topic_images))
        audio_dir = os.path.join(workdir, f"_audio_{prefix_num}")
        audio_paths = engine.synthesize_segments(segments, audio_dir)
        return (segments, audio_paths, topic_images, video_path)
    except Exception as exc:
        logger.exception("TTS failed for '%s': %s", topic_name, exc)
        return f"'{topic_name}' TTS failed: {exc}"


def _update_tts_progress(ctx: JobContext, done: int, total: int) -> None:
    """Emit a progress update after completing one TTS topic."""
    pct = 5 + int(50 * done / total)
    elapsed_s = _elapsed(ctx)
    _update_job(ctx["video_job_id"],
                progress={"phase": "tts", "current_topic": done, "total_topics": total,
                          "percent": pct, "elapsed_s": elapsed_s,
                          "eta_s": _estimate_eta(pct, elapsed_s)})


def _phase_compose(
    ctx: JobContext, tts_results: list[tuple | None], config: dict,
) -> tuple[list[str | None], list[str]]:
    """Run parallel ffmpeg composition (CPU-bound, libx264)."""
    vid = ctx["video_job_id"]
    total = len(tts_results)

    if _is_cancelled(vid):
        raise InterruptedError("Job cancelled before composition")

    fps = config.get("fps", cpu_video_settings.video_fps)
    _update_job(vid, status="composing",
                progress={"phase": "composing", "percent": 55,
                          "elapsed_s": _elapsed(ctx),
                          "completed_videos": 0, "total_videos": total})

    compose_jobs = [(i, r) for i, r in enumerate(tts_results) if r is not None]
    cpu_count = os.cpu_count() or 4
    pool_size = min(cpu_video_settings.video_max_workers, cpu_count, len(compose_jobs) or 1)
    threads_per = max(1, cpu_count // pool_size)

    results = _run_compose_pool(ctx, compose_jobs, fps, pool_size, threads_per)

    video_paths: list[str | None] = [None] * total
    errors: list[str] = []
    for idx, path, error in results:
        video_paths[idx] = path
        if error:
            errors.append(error)

    logger.info("Compose phase complete: %d videos", sum(1 for p in video_paths if p))
    return video_paths, errors


class _ComposeArgs(TypedDict):
    """Arguments for a single video compose task."""

    vid: str
    segments: list
    audio_paths: list[str]
    topic_images: list[str]
    vpath: str
    fps: int
    threads: int


def _compose_one_video(args: _ComposeArgs) -> str:
    """Compose a single video (runs inside thread pool)."""
    from backend.services.video_builder import _compose_video

    if _is_cancelled(args["vid"]):
        raise InterruptedError("Job cancelled")
    _compose_video(
        args["segments"], args["audio_paths"], args["topic_images"],
        args["vpath"], args["fps"], threads=args["threads"],
    )
    return args["vpath"]


def _run_compose_pool(
    ctx: JobContext, compose_jobs: list[tuple], fps: int,
    pool_size: int, threads_per: int,
) -> list[tuple[int, str | None, str | None]]:
    """Execute ffmpeg composition in a thread pool.

    Returns:
        List of (idx, path_or_none, error_or_none) tuples.
    """
    vid = ctx["video_job_id"]
    results: list[tuple[int, str | None, str | None]] = []
    completed = 0

    with ThreadPoolExecutor(max_workers=pool_size) as pool:
        futures = {
            pool.submit(_compose_one_video, _ComposeArgs(
                vid=vid, segments=r[0], audio_paths=r[1],
                topic_images=r[2], vpath=r[3], fps=fps, threads=threads_per,
            )): i
            for i, r in compose_jobs
        }
        for future in as_completed(futures):
            idx = futures[future]
            completed += 1
            try:
                path = future.result()
                results.append((idx, path, None))
            except InterruptedError:
                pool.shutdown(wait=False, cancel_futures=True)
                raise
            except Exception as exc:
                logger.exception("Compose failed for topic %d: %s", idx, exc)
                results.append((idx, None, f"Topic {idx} compose failed: {exc}"))

            _update_compose_progress(ctx, completed, len(compose_jobs))
            if _is_cancelled(vid):
                pool.shutdown(wait=False, cancel_futures=True)
                raise InterruptedError("Job cancelled during composition")

    return results


def _update_compose_progress(ctx: JobContext, done: int, total: int) -> None:
    """Emit a progress update after completing one compose job."""
    pct = 55 + int(35 * done / total)
    elapsed_s = _elapsed(ctx)
    _update_job(ctx["video_job_id"],
                progress={"phase": "composing", "percent": pct, "elapsed_s": elapsed_s,
                          "eta_s": _estimate_eta(pct, elapsed_s),
                          "completed_videos": done, "total_videos": total})


def _phase_upload(
    ctx: JobContext, video_paths: list[str | None], errors: list[str], total: int,
) -> None:
    """Upload completed MP4s to GCS and mark job complete."""
    vid = ctx["video_job_id"]
    gcs = ctx["gcs"]
    gcs_prefix = ctx["gcs_prefix"]

    _update_job(vid, status="uploading",
                progress={"phase": "uploading", "percent": 90, "elapsed_s": _elapsed(ctx)})

    mp4_paths = [p for p in video_paths if p is not None]
    gcs.upload_videos(gcs_prefix, mp4_paths)

    total_elapsed = _elapsed(ctx)
    output_names = [os.path.basename(p) for p in mp4_paths]
    final_status: dict = {
        "video_job_id": vid,
        "status": "complete",
        "progress": {"phase": "complete", "percent": 100, "elapsed_s": total_elapsed},
        "output_paths": output_names,
        "elapsed_s": total_elapsed,
    }
    if errors:
        final_status["warnings"] = errors

    with _jobs_lock:
        _jobs[vid] = final_status

    gcs.upload_status(gcs_prefix, final_status)
    logger.info("CPU video job %s complete in %ds: %d/%d videos",
                vid, total_elapsed, len(mp4_paths), total)


def _handle_cancellation(ctx: JobContext) -> None:
    """Mark a cancelled job and upload status to GCS."""
    vid = ctx["video_job_id"]
    logger.info("CPU video job %s cancelled", vid)
    cancel_status = {
        "video_job_id": vid,
        "status": "cancelled",
        "progress": {"phase": "cancelled", "percent": 0},
    }
    with _jobs_lock:
        _jobs[vid] = cancel_status
    try:
        ctx["gcs"].upload_status(ctx["gcs_prefix"], cancel_status)
    except Exception:
        logger.warning("Failed to upload cancel status for %s", vid, exc_info=True)


def _handle_error(ctx: JobContext, exc: Exception) -> None:
    """Mark a failed job and upload error status to GCS."""
    vid = ctx["video_job_id"]
    logger.error("CPU video job %s failed: %s\n%s",
                 vid, exc, traceback.format_exc())
    error_status = {
        "video_job_id": vid,
        "status": "error",
        "error": str(exc),
        "progress": {"phase": "error", "percent": 0},
    }
    with _jobs_lock:
        _jobs[vid] = error_status
    try:
        ctx["gcs"].upload_status(ctx["gcs_prefix"], error_status)
    except Exception:
        logger.warning("Failed to upload error status for %s", vid, exc_info=True)
