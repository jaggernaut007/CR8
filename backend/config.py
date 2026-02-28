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
        - **Output formats** -- which artifacts to produce.
        - **Concurrency** -- thread pool sizes.
        - **LangSmith** -- tracing configuration.
        - **DeepSeek** -- eval judge credentials.
    """

    # OpenAI — model tiers
    openai_api_key: str
    openai_model: str = "gpt-5.1"              # backward-compat alias (maps to premium)
    openai_model_premium: str = "gpt-5.1"      # creative generation, critical modules
    openai_model_mini: str = "gpt-5-mini"      # analysis, structured output
    openai_model_nano: str = "gpt-5-nano"      # summarization, extraction, validation

    # Temperature presets (per-task)
    temp_analysis: float = 0.2                  # gap analysis, summarization, extraction
    temp_structured: float = 0.3               # module generation, PPT structuring
    temp_creative: float = 0.55                # video scripts, creative writing

    # Tavily
    tavily_api_key: str

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
    video_provider: str = "heygen"           # "heygen" or "synthesia"
    video_avatar_emotion: str = "Friendly"
    video_avatar_speed: float = 1.05         # slightly faster for natural enthusiasm

    # Output formats — comma-separated: "pdf", "script", "video", or combinations like "pdf,script"
    output_formats: str = "pdf"
    video_topic_limit: int = 5  # max topics to generate scripts/videos for

    # Concurrency
    max_workers: int = 12
    video_max_workers: int = 6                 # parallel video generation jobs

    # LangSmith
    langchain_tracing_v2: bool = True
    langchain_project: str = "cr8-prototype"

    # DeepSeek (eval judge)
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    @property
    def output_formats_list(self) -> list[str]:
        """Parse comma-separated output_formats string into a list."""
        if isinstance(self.output_formats, list):
            return self.output_formats
        return [f.strip() for f in self.output_formats.split(",")]


settings = Settings()
