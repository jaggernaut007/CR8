"""CPU video service configuration.

Hardcodes ``video_device="cpu"`` — no GPU detection or CUDA dependencies.
"""

from __future__ import annotations

import os

from pydantic_settings import BaseSettings


class CPUVideoSettings(BaseSettings):
    """Settings for the CPU-only video generation service."""

    # GCS
    gcs_bucket: str = "cr8-jobs"

    # Kokoro TTS
    kokoro_voice: str = "af_heart"
    kokoro_lang: str = "a"
    video_fps: int = 24
    video_max_workers: int = 6  # 8 vCPU / 6 = ~1.3 threads per ffmpeg worker
    video_device: str = "cpu"  # always CPU — no GPU detection

    # HuggingFace (faster model downloads)
    hf_token: str = ""

    # Server
    max_concurrent_jobs: int = 1  # 32 GiB RAM — safe for 1 concurrent Kokoro job

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


cpu_video_settings = CPUVideoSettings()

# Propagate HF_TOKEN for authenticated downloads
if cpu_video_settings.hf_token:
    os.environ.setdefault("HF_TOKEN", cpu_video_settings.hf_token)
