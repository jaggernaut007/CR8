"""GPU video service configuration."""

from __future__ import annotations

import os

from pydantic_settings import BaseSettings


class GPUServiceSettings(BaseSettings):
    """Settings for the GPU video generation service."""

    # GCS
    gcs_bucket: str = "cr8-jobs"

    # Kokoro TTS
    kokoro_voice: str = "af_heart"
    kokoro_lang: str = "a"
    video_fps: int = 2
    video_max_workers: int = 6
    video_device: str = "auto"  # auto → cuda on Cloud Run GPU

    # HuggingFace (faster model downloads)
    hf_token: str = ""

    # Server
    max_concurrent_jobs: int = 1  # L4 has 24 GB VRAM — one job at a time

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


gpu_settings = GPUServiceSettings()

# Propagate HF_TOKEN for authenticated downloads
if gpu_settings.hf_token:
    os.environ.setdefault("HF_TOKEN", gpu_settings.hf_token)
