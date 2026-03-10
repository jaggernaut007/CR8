import logging
import os

from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """CR8 pipeline configuration loaded from environment variables and ``.env``.

    Uses Pydantic Settings to merge values from the ``.env`` file at the
    project root with any environment variables already set.  Unknown
    variables are silently ignored (``extra = "ignore"``).

    The settings are grouped into:
        - **OpenAI** -- model tier names and API key.
        - **Temperature presets** -- per-task creativity levels.
        - **Tavily** -- web search API key.
        - **ChromaDB** -- persistence directory.
        - **HeyGen / Synthesia** -- video generation credentials.
        - **Kokoro** -- local TTS video generation settings.
        - **Output formats** -- which artifacts to produce.
        - **Concurrency** -- thread pool sizes.
        - **LangSmith** -- tracing configuration.
        - **DeepSeek** -- eval judge credentials.
    """

    # OpenAI — model tiers
    openai_api_key: str = ""  # required for pipeline, optional for GPU video service
    openai_model: str = "gpt-5.1"              # backward-compat alias (maps to premium)
    openai_model_premium: str = "gpt-5.1"      # creative generation, critical modules
    openai_model_mini: str = "gpt-5-mini"      # analysis, structured output
    openai_model_nano: str = "gpt-5-nano"      # summarization, extraction, validation

    # Temperature presets (per-task)
    temp_analysis: float = 0.2                  # gap analysis, summarization, extraction
    temp_structured: float = 0.3               # module generation, PPT structuring
    temp_creative: float = 0.55                # video scripts, creative writing

    # Tavily
    tavily_api_key: str = ""  # required for pipeline, optional for GPU video service

    # ChromaDB
    chroma_persist_dir: str = "./chroma_db"

    # HeyGen (video generation) — optional, only needed for --format video
    heygen_api_key: str = ""
    heygen_avatar_id: str = ""
    heygen_voice_id: str = ""

    # Synthesia (alternative video provider) — scaffold only
    synthesia_api_key: str = ""
    synthesia_avatar_id: str = ""

    # Video provider and tuning
    video_provider: str = "heygen"           # "heygen", "synthesia", or "kokoro"
    video_avatar_emotion: str = "Friendly"
    video_avatar_speed: float = 1.05         # slightly faster for natural enthusiasm

    # Kokoro TTS (local video generation — no API key needed)
    kokoro_voice: str = "af_heart"
    kokoro_lang: str = "a"
    video_fps: int = 2                     # 2 fps for static slides — small file size, smooth playback

    # Slide export resolution
    slide_export_dpi: int = 144            # 144 = exactly 1920x1080 for 13.333"x7.5" slides

    # Output formats — comma-separated: "pdf", "script", "video", or combinations like "pdf,script"
    output_formats: str = "pdf"
    video_topic_limit: int = 5  # max topics to generate scripts/videos for

    # HuggingFace — authenticated downloads (faster, higher rate limits)
    hf_token: str = ""

    # Concurrency
    max_workers: int = 12
    video_max_workers: int = 12                # parallel video composition workers

    # Hardware acceleration — "auto" detects best GPU (cuda > mps > cpu)
    video_device: str = "auto"                 # auto | cpu | mps | cuda

    # LangSmith (tracing is opt-in — set LANGCHAIN_API_KEY to enable)
    langchain_api_key: str = ""
    langchain_tracing_v2: bool = False
    langchain_project: str = "cr8-prototype"

    # DeepSeek (eval judge)
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"

    # Database (Neon PostgreSQL)
    database_url: str = ""

    # Auth / JWT
    jwt_secret: str = ""  # REQUIRED: set via JWT_SECRET env var (min 32 bytes)
    jwt_algorithm: str = "HS256"
    jwt_access_expiry_minutes: int = 480  # 8 hours
    jwt_refresh_expiry_days: int = 7

    # Upload limits
    max_upload_size_mb: int = 50  # max file upload size in megabytes

    # CORS
    allowed_origins: str = "http://localhost:8080,http://localhost:5173"

    # Video services (offload to Cloud Run GPU or CPU-video instances)
    gpu_service_url: str = ""         # GPU primary (europe-west4)
    gpu_fallback_url: str = ""        # GPU fallback (europe-west1)
    cpu_video_service_url: str = ""   # CPU-only video service (europe-west2)
    gcs_bucket: str = "cr8-jobs"      # shared GCS bucket for data transfer

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    _MIN_JWT_SECRET_LEN = 32
    _MIN_API_KEY_LEN = 8

    @model_validator(mode="after")
    def _validate_required_secrets(self) -> "Settings":
        """Fail fast if critical secrets are missing or too short."""
        if self.jwt_secret and len(self.jwt_secret) < self._MIN_JWT_SECRET_LEN:
            raise ValueError("JWT_SECRET must be at least 32 characters")
        if self.openai_api_key and len(self.openai_api_key) < self._MIN_API_KEY_LEN:
            raise ValueError("OPENAI_API_KEY looks invalid (too short)")
        return self

    @property
    def output_formats_list(self) -> list[str]:
        """Parse comma-separated output_formats string into a list."""
        if isinstance(self.output_formats, list):
            return self.output_formats
        return [f.strip() for f in self.output_formats.split(",")]

    @property
    def should_use_gpu_service(self) -> bool:
        """True when a remote GPU service URL is configured."""
        return bool(self.gpu_service_url)

    @property
    def should_use_video_service(self) -> bool:
        """True when any remote video service URL is configured."""
        return bool(self.gpu_service_url or self.cpu_video_service_url)


settings = Settings()

# Configure logging for the backend package
if not logging.root.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

# Propagate HF_TOKEN so huggingface_hub uses authenticated (faster) downloads.
if settings.hf_token:
    os.environ.setdefault("HF_TOKEN", settings.hf_token)

# Apply LangSmith env vars so auto-tracing works when a key is provided.
if settings.langchain_api_key:
    os.environ.setdefault("LANGCHAIN_API_KEY", settings.langchain_api_key)
    os.environ.setdefault("LANGCHAIN_TRACING_V2", str(settings.langchain_tracing_v2).lower())
    os.environ.setdefault("LANGCHAIN_PROJECT", settings.langchain_project)
