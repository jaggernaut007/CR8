from pydantic_settings import BaseSettings


class EvalSettings(BaseSettings):
    # DeepSeek judge model
    judge_model: str = "deepseek-chat"
    judge_temperature: float = 0.1
    judge_max_tokens: int = 2000

    # DeepSeek API (reads from main .env)
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"

    # Eval thresholds
    min_weighted_score: float = 3.0       # Minimum acceptable aggregate score (1-5)
    regression_threshold: float = 0.5     # Flag regressions > this delta
    consistency_threshold: float = 0.5    # Max acceptable score variance across runs

    # Paths
    datasets_dir: str = "backend/evals/datasets"
    reports_dir: str = "backend/evals/reports"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    def require_judge_key(self) -> None:
        """Raise early if the DeepSeek API key is missing, before any LLM call."""
        if not self.deepseek_api_key:
            raise ValueError(
                "DEEPSEEK_API_KEY is not set. Add it to your .env file to run L2 evals."
            )


eval_settings = EvalSettings()
