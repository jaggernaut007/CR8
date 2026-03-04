"""Background worker: downloads from GCS, runs TTS + compose, uploads results.

The heavy lifting reuses ``backend.services.tts_engine.TTSEngine`` and
``backend.services.video_builder._compose_video`` which are copied into
the GPU container image.
"""

from __future__ import annotations

import logging
import os
import tempfile
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

from gpu_service.config import gpu_settings
from gpu_service.gcs_client import GPUGCSClient

logger = logging.getLogger(__name__)

# In-memory job store (single instance, max 1 concurrent job)
_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()
# Per-job cancellation events
_cancel_events: dict[str, threading.Event] = {}


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
    evt = _cancel_events.get(video_job_id)
    return evt is not None and evt.is_set()


def _update_job(video_job_id: str, **kwargs: object) -> None:
    with _jobs_lock:
        if video_job_id in _jobs:
            _jobs[video_job_id].update(kwargs)


def run_video_job(video_job_id: str, gcs_prefix: str) -> None:
    """Execute a full video generation job (runs in a background thread).

    1. Download manifest + slide images from GCS
    2. TTS synthesis (Kokoro, sequential, on GPU)
    3. Video composition (ffmpeg, parallel, CPU-bound)
    4. Upload MP4s to GCS
    """
    import time

    from backend.services.script_parser import parse_script
    from backend.services.tts_engine import TTSEngine
    from backend.services.video_builder import _compose_video, _get_topic_images, _slugify

    _cancel_events[video_job_id] = threading.Event()

    with _jobs_lock:
        _jobs[video_job_id] = {
            "video_job_id": video_job_id,
            "status": "downloading",
            "progress": {"phase": "downloading", "percent": 0},
        }

    gcs = GPUGCSClient(gpu_settings.gcs_bucket)
    job_start = time.monotonic()

    try:
        with tempfile.TemporaryDirectory() as workdir:
            # ---- Step 1: Download inputs from GCS ----
            _update_job(
                video_job_id,
                status="downloading",
                progress={"phase": "downloading", "percent": 2},
            )

            manifest = gcs.download_manifest(gcs_prefix, workdir)
            topics = manifest["topics"]
            scripts = manifest["scripts"]
            slide_names = manifest["slide_images"]
            topic_slide_map = manifest.get("topic_slide_map")
            config = manifest.get("config", {})

            voice = config.get("voice", gpu_settings.kokoro_voice)
            lang = config.get("lang", gpu_settings.kokoro_lang)
            fps = config.get("fps", gpu_settings.video_fps)

            slide_dir = os.path.join(workdir, "slides")
            slide_images = gcs.download_slides(gcs_prefix, slide_names, slide_dir)

            total = len(topics)
            output_dir = os.path.join(workdir, "output")
            os.makedirs(output_dir, exist_ok=True)
            scripts_dir = os.path.join(output_dir, "scripts")
            os.makedirs(scripts_dir, exist_ok=True)

            if not slide_images:
                raise RuntimeError("No slide images downloaded from GCS")

            # Pad scripts if fewer scripts than topics: replay the last script.
            # This handles edge cases where script generation partially failed.
            if len(scripts) < total:
                scripts = list(scripts) + [scripts[-1]] * (total - len(scripts))

            # ---- Step 2: Sequential TTS (GPU) ----
            # TTS runs sequentially (not parallel) because the Kokoro model
            # shares a single GPU and peaks at ~3.4 GB VRAM.  Running multiple
            # TTS calls concurrently would OOM on an L4 (24 GB) with >6 topics.
            tts_start = time.monotonic()
            elapsed_s = int(tts_start - job_start)
            _update_job(
                video_job_id,
                status="tts",
                progress={"phase": "tts", "current_topic": 0, "total_topics": total,
                          "percent": 5, "elapsed_s": elapsed_s},
            )

            engine = TTSEngine(voice=voice, lang=lang)
            tts_results: list[tuple[list[dict], list[str], list[str], str] | None] = []
            errors: list[str] = []

            for i in range(total):
                if _is_cancelled(video_job_id):
                    raise InterruptedError("Job cancelled during TTS")

                slug = _slugify(topics[i]["name"])
                prefix_num = f"{i + 1:02d}"
                video_path = os.path.join(output_dir, f"{prefix_num}_{slug}_slide.mp4")
                script_path = os.path.join(scripts_dir, f"{prefix_num}_{slug}_slide.txt")

                with open(script_path, "w", encoding="utf-8") as f:
                    f.write(scripts[i])

                topic_name = topics[i]["name"]
                topic_images = _get_topic_images(topic_name, slide_images, topic_slide_map)

                try:
                    segments = parse_script(scripts[i], num_slides=len(topic_images))
                    audio_dir = os.path.join(workdir, f"_audio_{prefix_num}")
                    audio_paths = engine.synthesize_segments(segments, audio_dir)
                    tts_results.append((segments, audio_paths, topic_images, video_path))
                except Exception as exc:
                    logger.error("TTS failed for '%s': %s\n%s", topic_name, exc, traceback.format_exc())
                    errors.append(f"'{topic_name}' TTS failed: {exc}")
                    tts_results.append(None)

                # Update progress with elapsed time and ETA
                pct = 5 + int(50 * (i + 1) / total)
                elapsed_s = int(time.monotonic() - job_start)
                eta_s = int(elapsed_s / max(pct, 1) * (100 - pct)) if pct > 0 else None
                _update_job(
                    video_job_id,
                    progress={"phase": "tts", "current_topic": i + 1, "total_topics": total,
                              "percent": pct, "elapsed_s": elapsed_s, "eta_s": eta_s},
                )

            tts_elapsed = int(time.monotonic() - tts_start)
            logger.info("TTS phase complete in %ds for %d topics", tts_elapsed, total)

            # ---- Step 3: Parallel composition (CPU-bound ffmpeg) ----
            # Composition is CPU-bound (image scaling, audio muxing, H.264 encoding)
            # so we parallelise across CPU cores.  Each ffmpeg process gets
            # (cpu_count // max_workers) threads to avoid oversubscription.
            if _is_cancelled(video_job_id):
                raise InterruptedError("Job cancelled before composition")

            compose_start = time.monotonic()
            elapsed_s = int(compose_start - job_start)
            _update_job(
                video_job_id,
                status="composing",
                progress={"phase": "composing", "percent": 55, "elapsed_s": elapsed_s,
                          "completed_videos": 0, "total_videos": total},
            )

            compose_jobs = [(i, r) for i, r in enumerate(tts_results) if r is not None]
            cpu_count = os.cpu_count() or 4
            max_workers = min(
                gpu_settings.video_max_workers,
                cpu_count,
                len(compose_jobs) or 1,
            )
            threads_per_worker = max(1, cpu_count // max_workers)
            video_paths: list[str | None] = [None] * total
            composed_count = 0

            def _compose_one(idx, segments, audio_paths, topic_images, vpath):
                if _is_cancelled(video_job_id):
                    raise InterruptedError("Job cancelled")
                _compose_video(segments, audio_paths, topic_images, vpath, fps, threads=threads_per_worker)
                return idx, vpath

            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                futures = {pool.submit(_compose_one, i, *r): i for i, r in compose_jobs}
                for future in as_completed(futures):
                    idx = futures[future]
                    try:
                        _, path = future.result()
                        video_paths[idx] = path
                        composed_count += 1
                    except InterruptedError:
                        pool.shutdown(wait=False, cancel_futures=True)
                        raise
                    except Exception as exc:
                        logger.error(
                            "Compose failed for topic %d: %s\n%s",
                            idx, exc, traceback.format_exc(),
                        )
                        errors.append(f"Topic {idx} compose failed: {exc}")
                        composed_count += 1

                    # Update compose progress with per-video tracking
                    pct = 55 + int(35 * composed_count / len(compose_jobs))
                    elapsed_s = int(time.monotonic() - job_start)
                    eta_s = int(elapsed_s / max(pct, 1) * (100 - pct)) if pct > 0 else None
                    _update_job(
                        video_job_id,
                        progress={"phase": "composing", "percent": pct, "elapsed_s": elapsed_s,
                                  "eta_s": eta_s, "completed_videos": composed_count,
                                  "total_videos": len(compose_jobs)},
                    )

                    if _is_cancelled(video_job_id):
                        pool.shutdown(wait=False, cancel_futures=True)
                        raise InterruptedError("Job cancelled during composition")

            compose_elapsed = int(time.monotonic() - compose_start)
            logger.info("Compose phase complete in %ds for %d videos", compose_elapsed, composed_count)

            # ---- Step 4: Upload results to GCS ----
            elapsed_s = int(time.monotonic() - job_start)
            _update_job(
                video_job_id,
                status="uploading",
                progress={"phase": "uploading", "percent": 90, "elapsed_s": elapsed_s},
            )

            mp4_paths = [p for p in video_paths if p is not None]
            gcs.upload_videos(gcs_prefix, mp4_paths)

            # ---- Done ----
            total_elapsed = int(time.monotonic() - job_start)
            output_names = [os.path.basename(p) for p in mp4_paths]
            final_status = {
                "video_job_id": video_job_id,
                "status": "complete",
                "progress": {"phase": "complete", "percent": 100, "elapsed_s": total_elapsed},
                "output_paths": output_names,
                "elapsed_s": total_elapsed,
            }
            if errors:
                final_status["warnings"] = errors

            with _jobs_lock:
                _jobs[video_job_id] = final_status

            gcs.upload_status(gcs_prefix, final_status)
            logger.info("Video job %s complete in %ds: %d/%d videos", video_job_id, total_elapsed, len(mp4_paths), total)

    except InterruptedError:
        logger.info("Video job %s cancelled", video_job_id)
        cancel_status = {
            "video_job_id": video_job_id,
            "status": "cancelled",
            "progress": {"phase": "cancelled", "percent": 0},
        }
        with _jobs_lock:
            _jobs[video_job_id] = cancel_status
        try:
            gcs.upload_status(gcs_prefix, cancel_status)
        except Exception:
            pass

    except Exception as exc:
        logger.error("Video job %s failed: %s\n%s", video_job_id, exc, traceback.format_exc())
        error_status = {
            "video_job_id": video_job_id,
            "status": "error",
            "error": str(exc),
            "progress": {"phase": "error", "percent": 0},
        }
        with _jobs_lock:
            _jobs[video_job_id] = error_status

        try:
            gcs.upload_status(gcs_prefix, error_status)
        except Exception:
            pass

    finally:
        _cancel_events.pop(video_job_id, None)
