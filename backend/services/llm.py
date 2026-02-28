from langchain_openai import ChatOpenAI
from backend.config import settings

# Tier → (config attribute, default temperature)
_TIER_MAP = {
    "nano":    ("openai_model_nano",    "temp_analysis"),
    "mini":    ("openai_model_mini",    "temp_structured"),
    "full":    ("openai_model_premium", "temp_structured"),   # backward compat
    "premium": ("openai_model_premium", "temp_creative"),
}


def get_llm(model: str = "mini", temperature: float | None = None) -> ChatOpenAI:
    """Get an OpenAI chat model.

    Args:
        model: "nano" for extraction/validation, "mini" for analysis/structured output,
               "premium" for creative generation, "full" (alias for premium).
        temperature: Override the tier's default temperature. If None, uses the
                     tier-appropriate preset from config.
    """
    model_attr, temp_attr = _TIER_MAP.get(model, _TIER_MAP["mini"])
    model_name = getattr(settings, model_attr)
    temp = temperature if temperature is not None else getattr(settings, temp_attr)
    return ChatOpenAI(
        model=model_name,
        api_key=settings.openai_api_key,
        temperature=temp,
    )
