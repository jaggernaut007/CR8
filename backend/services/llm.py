import logging

from langchain_openai import ChatOpenAI
from backend.config import settings

logger = logging.getLogger(__name__)

# Tier → (config attribute for model name, config attribute for temperature)
# Severity-based routing in agent_generate.py uses these tiers:
#   critical gaps → premium (GPT-5.1), moderate/minor → mini (GPT-5-mini)
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
    logger.debug("Creating LLM: tier=%s model=%s temp=%.2f", model, model_name, temp)
    return ChatOpenAI(
        model=model_name,
        api_key=settings.openai_api_key,
        temperature=temp,
    )
