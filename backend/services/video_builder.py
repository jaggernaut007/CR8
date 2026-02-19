"""HeyGen API client for generating avatar-narrated educational videos.

Usage:
    from backend.services.video_builder import build_videos

    paths = build_videos(
        topics=[{"name": "Word2Vec"}, {"name": "GloVe"}],
        scripts=["Welcome to this lesson on Word2Vec...", "In this video..."],
        output_dir="outputs/20260219_videos",
        avatar_id="your_avatar_id",
        voice_id="your_voice_id",
    )
"""

import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

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


def _create_video(
    api_key: str,
    script: str,
    avatar_id: str,
    voice_id: str,
    title: str,
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
                    "speed": 1.0,
                    "emotion": "Friendly",
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
) -> str:
    """Generate, poll, and download a single video. Returns the output path."""
    slug = _slugify(topic_name)
    prefix = f"{idx + 1:02d}"
    video_path = os.path.join(output_dir, f"{prefix}_{slug}.mp4")
    script_path = os.path.join(scripts_dir, f"{prefix}_{slug}.txt")

    # Save script to disk
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script)
    print(f"[Video]   Script saved: {script_path}")

    # Submit to HeyGen
    title = f"{prefix} - {topic_name}"
    print(f"[Video] Topic {idx + 1}/{total}: {topic_name} — submitting to HeyGen...")
    video_id = _create_video(api_key, script, avatar_id, voice_id, title)
    print(f"[Video]   {topic_name}: video_id={video_id}, polling for completion...")

    # Poll until done
    status_data = _poll_status(api_key, video_id)
    duration = status_data.get("duration", 0)
    print(f"[Video]   {topic_name}: completed — {duration:.1f}s duration")

    # Download
    _download_video(status_data["video_url"], video_path)
    print(f"[Video]   {topic_name}: saved to {video_path}")

    return video_path


def build_videos(
    topics: list[dict],
    scripts: list[str],
    output_dir: str,
    api_key: str,
    avatar_id: str,
    voice_id: str,
) -> list[str]:
    """Build videos for the given topics and scripts.

    Creates the output directory structure, saves scripts to disk,
    submits each video to HeyGen in parallel, and downloads the results.

    Returns a list of file paths to the downloaded videos.
    """
    os.makedirs(output_dir, exist_ok=True)
    scripts_dir = os.path.join(output_dir, "scripts")
    os.makedirs(scripts_dir, exist_ok=True)

    total = len(topics)
    video_paths = [None] * total

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_to_idx = {
            executor.submit(
                _process_single_video,
                i,
                topics[i]["name"],
                scripts[i],
                output_dir,
                scripts_dir,
                api_key,
                avatar_id,
                voice_id,
                total,
            ): i
            for i in range(total)
        }
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            video_paths[idx] = future.result()

    return video_paths
