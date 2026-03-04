"""Video generation client supporting HeyGen, Synthesia (scaffold), and Kokoro (local).

Usage:
    from backend.services.video_builder import build_videos

    # Cloud providers (HeyGen/Synthesia — not yet available):
    paths = build_videos(
        topics=[{"name": "Word2Vec"}], scripts=["..."],
        output_dir="outputs/videos", api_key="key",
        avatar_id="av", voice_id="v",
    )

    # Local Kokoro TTS pipeline:
    paths = build_videos(
        topics=[{"name": "Word2Vec"}], scripts=["[SLIDE 1]\\nWelcome..."],
        output_dir="outputs/videos", api_key="", avatar_id="", voice_id="",
        provider="kokoro", slide_images=["slide_001.png"],
    )
"""

from __future__ import annotations

import logging
import os
import re
import time
import traceback

import requests

from backend.config import settings

try:
    from langsmith import traceable
except ImportError:  # pragma: no cover
    def traceable(**kwargs):
        def decorator(func):
            return func
        return decorator

logger = logging.getLogger(__name__)

HEYGEN_BASE_URL = "https://api.heygen.com"
HEYGEN_SCENE_CHAR_LIMIT = 5000


def _slugify(name: str) -> str:
    """Convert a topic name to a filesystem-safe slug."""
    slug = re.sub(r"[^\w\s-]", "", name)
    slug = re.sub(r"[\s]+", "_", slug).strip("_")
    return slug[:80]


def _split_into_scenes(script: str) -> list[str]:
    """Split a script into chunks that each fit within HeyGen's per-scene character limit.

    Splits on paragraph boundaries first, falling back to sentence boundaries.
    """
    if len(script) <= HEYGEN_SCENE_CHAR_LIMIT:
        return [script]

    paragraphs = script.split("\n\n")
    scenes = []
    current = ""

    for para in paragraphs:
        candidate = f"{current}\n\n{para}".strip() if current else para
        if len(candidate) <= HEYGEN_SCENE_CHAR_LIMIT:
            current = candidate
        else:
            if current:
                scenes.append(current)
            # If a single paragraph is too long, split by sentences
            if len(para) > HEYGEN_SCENE_CHAR_LIMIT:
                sentences = re.split(r"(?<=[.!?])\s+", para)
                current = ""
                for sent in sentences:
                    candidate = f"{current} {sent}".strip() if current else sent
                    if len(candidate) <= HEYGEN_SCENE_CHAR_LIMIT:
                        current = candidate
                    else:
                        if current:
                            scenes.append(current)
                        current = sent
            else:
                current = para

    if current:
        scenes.append(current)

    return scenes


# ---------------------------------------------------------------------------
# HeyGen client (full implementation)
# ---------------------------------------------------------------------------


def _create_video(
    api_key: str,
    script: str,
    avatar_id: str,
    voice_id: str,
    title: str,
    emotion: str = "Friendly",
    speed: float = 1.05,
) -> str:
    """Submit a video generation job to HeyGen. Returns the video_id."""
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
    }

    scenes = _split_into_scenes(script)
    video_inputs = []
    for scene_text in scenes:
        video_inputs.append(
            {
                "character": {
                    "type": "avatar",
                    "avatar_id": avatar_id,
                    "scale": 1,
                    "avatar_style": "normal",
                },
                "voice": {
                    "type": "text",
                    "voice_id": voice_id,
                    "input_text": scene_text,
                    "speed": speed,
                    "emotion": emotion,
                },
                "background": {
                    "type": "color",
                    "value": "#FFFFFF",
                },
            }
        )

    payload = {
        "video_inputs": video_inputs,
        "dimension": {"width": 1920, "height": 1080},
        "caption": False,
        "title": title,
    }

    resp = requests.post(
        f"{HEYGEN_BASE_URL}/v2/video/generate",
        headers=headers,
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    result = resp.json()

    if result.get("error"):
        raise RuntimeError(f"HeyGen API error: {result['error']}")

    return result["data"]["video_id"]


def _poll_status(api_key: str, video_id: str, interval: int = 10, timeout: int = 600) -> dict:
    """Poll HeyGen until the video is completed or failed. Returns status data."""
    headers = {"x-api-key": api_key}
    elapsed = 0

    while elapsed < timeout:
        resp = requests.get(
            f"{HEYGEN_BASE_URL}/v1/video_status.get",
            headers=headers,
            params={"video_id": video_id},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        status = data["status"]

        if status == "completed":
            return data
        if status == "failed":
            raise RuntimeError(f"HeyGen video generation failed: {data.get('error')}")

        time.sleep(interval)
        elapsed += interval

    raise TimeoutError(f"HeyGen video not ready after {timeout}s (video_id={video_id})")


# ---------------------------------------------------------------------------
# Synthesia client (scaffold — stubs only)
# ---------------------------------------------------------------------------


def _create_video_synthesia(api_key: str, script: str, avatar_id: str, title: str) -> str:
    """Submit a video generation job to Synthesia. Returns the video_id.

    Synthesia API differences from HeyGen:
    - Auth header: Authorization: <key> (not x-api-key)
    - No separate voice_id — voice is tied to the avatar
    - Endpoint: POST https://api.synthesia.io/v2/videos
    - Payload structure:
        {
            "title": "...",
            "input": [{"scriptText": "...", "avatar": "avatar_id"}],
            "test": true  # for development
        }
    """
    raise NotImplementedError(
        "Synthesia client not yet implemented. "
        "Set VIDEO_PROVIDER=heygen or implement this function."
    )


def _poll_status_synthesia(api_key: str, video_id: str, interval: int = 15, timeout: int = 900) -> dict:
    """Poll Synthesia until the video is completed or failed. Returns status data.

    Synthesia polling differences from HeyGen:
    - Endpoint: GET https://api.synthesia.io/v2/videos/{video_id}
    - Auth header: Authorization: <key>
    - Status field: response["status"] (not response["data"]["status"])
    - Download URL: response["download"] when status == "complete"
    - Longer processing times — default timeout 15 min
    """
    raise NotImplementedError(
        "Synthesia polling not yet implemented. "
        "Set VIDEO_PROVIDER=heygen or implement this function."
    )


# ---------------------------------------------------------------------------
# Kokoro local video pipeline
# ---------------------------------------------------------------------------

_moviepy_patched = False


def _patch_moviepy_pix_fmt():
    """Fix MoviePy v2 bug: it adds ``-pix_fmt yuva420p`` (alpha) for
    h264_nvenc/libx264 when both dimensions are even.  H.264 videos don't
    need alpha — ``yuv420p`` is correct.

    We swap the ``sp`` (subprocess) module reference inside MoviePy's
    ffmpeg_writer with a lightweight proxy whose ``Popen`` rewrites the
    flag.  Only MoviePy is affected; all other subprocess usage is untouched.
    """
    global _moviepy_patched
    if _moviepy_patched:
        return

    import subprocess
    import types

    try:
        import moviepy.video.io.ffmpeg_writer as _fw
    except (ImportError, AttributeError):
        # moviepy is mocked in tests — patch not needed
        return

    _RealPopen = subprocess.Popen

    class _FixedPopen(_RealPopen):
        """Popen wrapper that rewrites yuva420p -> yuv420p in ffmpeg cmds."""

        def __init__(self, cmd, *args, **kwargs):
            if isinstance(cmd, list) and "yuva420p" in cmd:
                cmd = [("yuv420p" if x == "yuva420p" else x) for x in cmd]
                logger.debug("Patched MoviePy pix_fmt: yuva420p -> yuv420p")
            super().__init__(cmd, *args, **kwargs)

    # Create a proxy module so only ffmpeg_writer sees the patched Popen
    _proxy_sp = types.ModuleType("subprocess_proxy")
    _proxy_sp.__dict__.update(subprocess.__dict__)
    _proxy_sp.Popen = _FixedPopen
    _fw.sp = _proxy_sp

    _moviepy_patched = True
    logger.info("MoviePy yuva420p bug patched (yuv420p will be used)")


def _compose_video(
    segments: list[dict],
    audio_paths: list[str],
    slide_images: list[str],
    output_path: str,
    fps: int = 5,
    threads: int = 0,
) -> str:
    """Compose slide images + audio into a single MP4.

    This is the CPU-bound encoding step that can run in parallel across
    videos (each invocation is independent).  If the detected hardware
    encoder fails at write time, automatically retries with ``libx264``.

    Args:
        threads: CPU threads for this ffmpeg encode. 0 = auto (all cores).
    """
    from moviepy import AudioFileClip, ImageClip, concatenate_videoclips

    from backend.services.gpu_utils import get_ffmpeg_encoder

    # Target resolution for output videos (even dimensions required by h264)
    target_size = (1920, 1080)

    clips = []
    for seg, audio_path in zip(segments, audio_paths):
        # Match segment to slide image by slide_num (1-based), clamp to bounds
        img_idx = max(0, min(seg["slide_num"] - 1, len(slide_images) - 1))
        img_path = slide_images[img_idx]

        audio_clip = AudioFileClip(audio_path)
        img_clip = ImageClip(img_path)
        # Only resize if source dimensions don't already match (skip no-op)
        if img_clip.size != list(target_size):
            img_clip = img_clip.resized(target_size)
        img_clip = (
            img_clip
            .with_duration(audio_clip.duration)
            .with_audio(audio_clip)
        )
        clips.append(img_clip)

    if not clips:
        raise RuntimeError("No video clips produced — script may be empty")

    _patch_moviepy_pix_fmt()

    encoder = get_ffmpeg_encoder()
    base_params: list[str] = []
    if threads > 0:
        base_params += ["-threads", str(threads)]

    def _build_params(enc: str) -> list[str] | None:
        """Build ffmpeg_params for the given encoder with quality controls."""
        params = list(base_params)
        if enc == "libx264":
            params += ["-crf", "20"]
        elif enc == "h264_videotoolbox":
            params += ["-q:v", "65"]
        elif enc == "h264_nvenc":
            params += ["-cq", "20", "-b:v", "0"]
        elif enc == "h264_qsv":
            params += ["-global_quality", "20"]
        return params or None

    final = concatenate_videoclips(clips, method="compose")
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    fname = os.path.basename(output_path)
    used_encoder = encoder
    t0 = time.monotonic()

    try:
        logger.info("Composing %s with encoder=%s", fname, encoder)
        final.write_videofile(
            output_path, fps=fps, audio_codec="aac",
            preset="fast", logger=None,
            codec=encoder,
            ffmpeg_params=_build_params(encoder),
        )
    except Exception as exc:
        if encoder == "libx264":
            raise
        logger.warning(
            "Encoder %s failed for %s — retrying with libx264. Error: %s",
            encoder, fname, exc,
        )
        used_encoder = "libx264"
        final.write_videofile(
            output_path, fps=fps, audio_codec="aac",
            preset="fast", logger=None,
            codec="libx264",
            ffmpeg_params=_build_params("libx264"),
        )

    elapsed = time.monotonic() - t0
    logger.info("Composed %s in %.1fs (encoder=%s)", fname, elapsed, used_encoder)
    return output_path


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _download_video(video_url: str, output_path: str) -> None:
    """Download a video from a URL to disk."""
    resp = requests.get(video_url, stream=True, timeout=120)
    resp.raise_for_status()
    with open(output_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)


def _process_single_video(
    idx: int,
    topic_name: str,
    script: str,
    output_dir: str,
    scripts_dir: str,
    api_key: str,
    avatar_id: str,
    voice_id: str,
    total: int,
    provider: str = "heygen",
    emotion: str = "Friendly",
    speed: float = 1.05,
) -> str:
    """Generate, poll, and download a single video. Returns the output path."""
    slug = _slugify(topic_name)
    prefix = f"{idx + 1:02d}"
    video_path = os.path.join(output_dir, f"{prefix}_{slug}_slide.mp4")
    script_path = os.path.join(scripts_dir, f"{prefix}_{slug}_slide.txt")

    # Save script to disk
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script)
    print(f"[Video]   Script saved: {script_path}")

    # Submit to video provider
    title = f"{prefix} - {topic_name} (Slide)"
    print(f"[Video] Topic {idx + 1}/{total}: {topic_name} — submitting to {provider}...")

    if provider == "synthesia":
        video_id = _create_video_synthesia(api_key, script, avatar_id, title)
    else:
        video_id = _create_video(api_key, script, avatar_id, voice_id, title, emotion, speed)

    print(f"[Video]   {topic_name}: video_id={video_id}, polling for completion...")

    # Poll until done
    if provider == "synthesia":
        status_data = _poll_status_synthesia(api_key, video_id)
    else:
        status_data = _poll_status(api_key, video_id)

    duration = status_data.get("duration", 0)
    print(f"[Video]   {topic_name}: completed — {duration:.1f}s duration")

    # Download
    video_url = status_data.get("video_url") or status_data.get("download", "")
    if not video_url:
        raise RuntimeError(f"No download URL in status response for '{topic_name}': {status_data}")
    _download_video(video_url, video_path)
    print(f"[Video]   {topic_name}: saved to {video_path}")

    return video_path


@traceable(run_type="tool", name="build_videos")
def build_videos(
    topics: list[dict],
    scripts: list[str],
    output_dir: str,
    api_key: str = "",
    avatar_id: str = "",
    voice_id: str = "",
    provider: str = "heygen",
    emotion: str = "Friendly",
    speed: float = 1.05,
    max_workers: int = 4,
    slide_images: list[str] | None = None,
    topic_slide_map: dict[str, list[int]] | None = None,
    kokoro_voice: str = "af_heart",
    kokoro_lang: str = "a",
    video_fps: int = 5,
    cancel_check: "callable | None" = None,
) -> list[str]:
    """Build videos for the given topics and scripts.

    For ``provider="kokoro"``, videos are generated locally using Kokoro TTS
    and MoviePy (requires *slide_images*).  For cloud providers (heygen,
    synthesia), a ``NotImplementedError`` is raised until those integrations
    are completed.

    Args:
        topics: List of topic dicts; each must have a ``"name"`` key.
        scripts: Parallel list of spoken-word script strings, one per topic.
        output_dir: Root directory for video outputs and scripts.
        api_key: API key for the video generation provider (not needed for kokoro).
        avatar_id: Provider-specific avatar identifier (not needed for kokoro).
        voice_id: Provider-specific voice identifier (not needed for kokoro).
        provider: ``"kokoro"``, ``"heygen"``, or ``"synthesia"``.
        emotion: Avatar emotion preset (cloud providers only).
        speed: Speech speed multiplier (cloud providers only).
        max_workers: Maximum parallel video generation jobs.
        slide_images: Ordered list of slide PNG paths (required for kokoro).
        topic_slide_map: Maps topic names to 0-based slide indices in the
            PPT.  Used to select per-topic slides for each video.
        kokoro_voice: Kokoro voice name.
        kokoro_lang: Kokoro language code.
        video_fps: Video frame rate for local generation.

    Returns:
        List of filesystem paths to the ``.mp4`` files, in the same order
        as *topics*.
    """
    if provider == "kokoro":
        return _build_kokoro_videos(
            topics, scripts, output_dir,
            slide_images=slide_images or [],
            topic_slide_map=topic_slide_map,
            voice=kokoro_voice, lang=kokoro_lang, fps=video_fps,
            cancel_check=cancel_check,
        )

    raise NotImplementedError(
        f"Video generation via '{provider}' is not yet available. "
        "Set VIDEO_PROVIDER=kokoro for local video generation, "
        "or use output formats: pdf, ppt, script."
    )


@traceable(run_type="chain", name="build_kokoro_videos")
def _build_kokoro_videos(
    topics: list[dict],
    scripts: list[str],
    output_dir: str,
    slide_images: list[str],
    topic_slide_map: dict[str, list[int]] | None = None,
    voice: str = "af_heart",
    lang: str = "a",
    fps: int = 5,
    cancel_check: "callable | None" = None,
) -> list[str]:
    """Build Kokoro videos in two phases for performance.

    Phase 1 (sequential): TTS synthesis with a shared engine (memory-heavy).
    Phase 2 (parallel): MoviePy composition + ffmpeg encoding (CPU-bound).
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    from backend.services.script_parser import parse_script
    from backend.services.tts_engine import TTSEngine

    os.makedirs(output_dir, exist_ok=True)
    scripts_dir = os.path.join(output_dir, "scripts")
    os.makedirs(scripts_dir, exist_ok=True)

    total = len(topics)
    video_paths: list[str | None] = [None] * total
    errors: list[str] = []

    logger.info("Starting Kokoro video generation: %d topics, %d slide images", total, len(slide_images))

    if not slide_images:
        msg = "No slide images provided — cannot generate videos"
        logger.error(msg)
        print(f"[Video] ERROR: {msg}")
        raise RuntimeError(msg)

    # Pad scripts list if fewer scripts than topics (single-script mode)
    if len(scripts) < total:
        scripts = list(scripts) + [scripts[-1]] * (total - len(scripts))

    # ---- Phase 1: Sequential TTS (shared engine, ~3.4 GB peak RAM) ----
    print("[Video] Phase 1: Synthesizing audio (sequential, shared TTS engine)...")
    engine = TTSEngine(voice=voice, lang=lang)
    tts_results: list[tuple[list[dict], list[str], list[str], str] | None] = []

    for i in range(total):
        # Check for cancellation between topics (~60s+ per topic)
        if cancel_check:
            cancel_check()

        slug = _slugify(topics[i]["name"])
        prefix = f"{i + 1:02d}"
        video_path = os.path.join(output_dir, f"{prefix}_{slug}_slide.mp4")
        script_path = os.path.join(scripts_dir, f"{prefix}_{slug}_slide.txt")

        # Save script
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(scripts[i])
        print(f"[Video]   Script saved: {script_path}")

        topic_name = topics[i]["name"]
        topic_images = _get_topic_images(topic_name, slide_images, topic_slide_map)

        print(f"[Video] Topic {i + 1}/{total}: {topic_name} — TTS ({len(topic_images)} slides)...")
        try:
            segments = parse_script(scripts[i], num_slides=len(topic_images))
            audio_dir = os.path.join(output_dir, f"_audio_{prefix}")
            audio_paths = engine.synthesize_segments(segments, audio_dir)
            tts_results.append((segments, audio_paths, topic_images, video_path))
        except Exception as exc:
            tb = traceback.format_exc()
            error_msg = f"'{topic_name}' TTS failed — {exc}"
            errors.append(error_msg)
            logger.error("TTS failed for '%s': %s\n%s", topic_name, exc, tb)
            print(f"[Video] ERROR: {error_msg}")
            tts_results.append(None)

    # Check before starting expensive composition phase
    if cancel_check:
        cancel_check()

    # ---- Phase 2: Parallel video composition (CPU-bound ffmpeg) ----
    compose_jobs = [(i, r) for i, r in enumerate(tts_results) if r is not None]
    cpu_count = os.cpu_count() or 4
    max_workers = min(
        settings.video_max_workers,
        cpu_count,
        len(compose_jobs) or 1,
    )
    # Distribute CPU threads evenly across workers to prevent over-subscription
    threads_per_worker = max(1, cpu_count // max_workers)
    print(
        f"[Video] Phase 2: Composing {len(compose_jobs)} videos "
        f"({max_workers} workers, {threads_per_worker} threads each)..."
    )

    def _compose_one(idx: int, segments, audio_paths, topic_images, video_path):
        if cancel_check:
            cancel_check()
        _compose_video(
            segments, audio_paths, topic_images, video_path,
            fps, threads=threads_per_worker,
        )
        return idx, video_path

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_compose_one, i, *r): i
            for i, r in compose_jobs
        }
        for future in as_completed(futures):
            # Check cancellation as each video completes (~4 min each)
            if cancel_check:
                try:
                    cancel_check()
                except Exception:
                    # Cancel remaining futures before re-raising
                    for f in futures:
                        f.cancel()
                    pool.shutdown(wait=False, cancel_futures=True)
                    raise

            idx = futures[future]
            topic_name = topics[idx]["name"]
            try:
                _, path = future.result()
                video_paths[idx] = path
                logger.info("Video saved: %s", path)
                print(f"[Video]   {topic_name}: saved to {path}")
            except Exception as exc:
                tb = traceback.format_exc()
                error_msg = f"'{topic_name}' compose failed — {exc}"
                errors.append(error_msg)
                logger.error("Video composition failed for '%s': %s\n%s", topic_name, exc, tb)
                print(f"[Video] ERROR: {error_msg}")

    succeeded = sum(1 for p in video_paths if p is not None)
    logger.info("Video generation complete: %d/%d succeeded", succeeded, total)
    if errors:
        logger.warning("Video errors summary: %s", "; ".join(errors))
        print(f"[Video] WARNING: {len(errors)}/{total} videos failed:")
        for err in errors:
            print(f"[Video]   - {err}")

    return video_paths


def _get_topic_images(
    topic_name: str,
    slide_images: list[str],
    topic_slide_map: dict[str, list[int]] | None,
) -> list[str]:
    """Return only the slide images that belong to a specific topic.

    If *topic_slide_map* is provided and contains the topic, the
    corresponding indices are used to slice *slide_images*.  Otherwise
    all images are returned as a fallback.
    """
    if topic_slide_map and topic_name in topic_slide_map:
        indices = topic_slide_map[topic_name]
        images = [slide_images[idx] for idx in indices if idx < len(slide_images)]
        if images:
            return images
        logger.warning("topic_slide_map indices out of range for '%s' — using all images", topic_name)

    return slide_images
