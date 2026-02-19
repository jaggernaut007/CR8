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

    # LangSmith
    langchain_tracing_v2: bool = True
    langchain_project: str = "cr8-prototype"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
