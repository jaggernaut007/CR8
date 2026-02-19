from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # OpenAI
    openai_api_key: str
    openai_model: str = "gpt-5"
    openai_model_mini: str = "gpt-5-mini"

    # Tavily
    tavily_api_key: str

    # ChromaDB
    chroma_persist_dir: str = "./chroma_db"

    # HeyGen (video generation) — optional, only needed for --format video/both
    heygen_api_key: str = ""
    heygen_avatar_id: str = ""
    heygen_voice_id: str = ""

    # Output formats — comma-separated: "pdf", "script", "video", or combinations like "pdf,script"
    output_formats: list[str] = ["pdf"]
    video_topic_limit: int = 2  # max topics to generate scripts/videos for (prototype cap)

    # Concurrency
    max_workers: int = 8

    # LangSmith
    langchain_tracing_v2: bool = True
    langchain_project: str = "cr8-prototype"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
