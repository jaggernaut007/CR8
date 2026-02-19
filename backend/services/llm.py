from langchain_openai import ChatOpenAI
from backend.config import settings


def get_llm(model: str = "mini") -> ChatOpenAI:
    """Get an OpenAI chat model.

    Args:
        model: "mini" for GPT-5-mini (extraction/analysis), "full" for GPT-5 (generation)
    """
    model_name = settings.openai_model_mini if model == "mini" else settings.openai_model
    return ChatOpenAI(
        model=model_name,
        api_key=settings.openai_api_key,
        temperature=0.3,
    )
