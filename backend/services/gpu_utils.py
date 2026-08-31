"""GPU / hardware-acceleration detection for TTS and video encoding.

Provides two helpers:

- ``get_torch_device(preference)`` — best PyTorch device (cuda > mps > cpu).
- ``get_ffmpeg_encoder()`` — best H.264 encoder available to ffmpeg.

Both fall back gracefully to CPU / software encoding.
"""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile

logger = logging.getLogger(__name__)

# Cache the detected encoder so we only probe once per process.
_cached_encoder: str | None = None


def get_torch_device(preference: str = "auto") -> str:
    """Return the best available PyTorch device string.

    Args:
        preference: ``"auto"`` to auto-detect, or force a specific device
            (``"cpu"``, ``"mps"``, ``"cuda"``).

    Returns:
        One of ``"cuda"``, ``"mps"``, or ``"cpu"``.
    """
    if preference != "auto":
        return preference

    try:
        import torch
    except ImportError:
        return "cpu"

    if torch.cuda.is_available():
        logger.info("GPU detected: CUDA (%s)", torch.cuda.get_device_name(0))
        return "cuda"

    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        logger.info("GPU detected: Apple Metal (MPS)")
        return "mps"

    logger.info("No GPU detected — using CPU")
    return "cpu"


def get_ffmpeg_encoder() -> str:
    """Return the best available H.264 encoder for ffmpeg.

    Checks for hardware encoders in order of preference:

    1. ``h264_videotoolbox`` — macOS VideoToolbox (Apple Silicon / Intel)
    2. ``h264_nvenc`` — NVIDIA NVENC
    3. ``h264_qsv`` — Intel Quick Sync Video
    4. ``h264_amf`` — AMD Advanced Media Framework
    5. ``libx264`` — software fallback (always available)

    The result is cached for the lifetime of the process.

    Returns:
        Encoder name string suitable for ``-c:v`` or moviepy's ``codec`` param.
    """
    global _cached_encoder
    if _cached_encoder is not None:
        return _cached_encoder

    for encoder in ("h264_videotoolbox", "h264_nvenc", "h264_qsv", "h264_amf"):
        if _encoder_available(encoder):
            logger.info("Hardware encoder available: %s", encoder)
            _cached_encoder = encoder
            return encoder

    logger.info("Using software encoder: libx264")
    _cached_encoder = "libx264"
    return "libx264"


def _encoder_available(name: str) -> bool:
    """Check whether ffmpeg can actually encode to a real file with a given encoder.

    Writes a real MP4 to a temp file (not ``-f null``) to catch cases where
    the encoder name is recognised but the hardware library (e.g.
    ``libnvidia-encode.so``) is missing at runtime.
    """
    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(suffix=".mp4")
        os.close(fd)
        result = subprocess.run(
            [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-f", "lavfi", "-i", "color=c=black:s=256x256:d=0.04",
                "-frames:v", "1", "-c:v", name, tmp_path,
            ],
            capture_output=True,
            timeout=15,
            check=False,
        )
        ok = result.returncode == 0 and os.path.getsize(tmp_path) > 0
        if not ok:
            stderr = result.stderr.decode(errors="replace").strip()
            logger.debug("Encoder %s probe failed (rc=%d): %s", name, result.returncode, stderr)
        return ok
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        logger.debug("Encoder %s probe error: %s", name, exc)
        return False
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
