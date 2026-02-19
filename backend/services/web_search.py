from tavily import TavilyClient
from backend.config import settings


_client = None


def _get_client() -> TavilyClient:
    global _client
    if _client is None:
        _client = TavilyClient(api_key=settings.tavily_api_key)
    return _client


def search(query: str, max_results: int = 5) -> list[dict]:
    """Search the web using Tavily.

    Returns a list of dicts with keys: title, url, content, score
    """
    client = _get_client()
    response = client.search(query=query, max_results=max_results, search_depth="basic")
    return response.get("results", [])
