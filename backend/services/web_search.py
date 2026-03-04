import logging

from tavily import TavilyClient
from backend.config import settings

logger = logging.getLogger(__name__)

_client = None


def _get_client() -> TavilyClient:
    """Lazily initialise a singleton Tavily client (one per process)."""
    global _client
    if _client is None:
        _client = TavilyClient(api_key=settings.tavily_api_key)
    return _client


def search(query: str, max_results: int = 5) -> list[dict]:
    """Search the web using Tavily.

    Args:
        query: Natural-language search query.
        max_results: Maximum number of results to return.

    Returns:
        List of result dicts, each containing ``title``, ``url``,
        ``content``, and ``score`` keys.
    """
    client = _get_client()
    logger.debug("Tavily search: %s (max_results=%d)", query[:80], max_results)
    response = client.search(query=query, max_results=max_results, search_depth="basic")
    results = response.get("results", [])
    logger.debug("Tavily returned %d results", len(results))
    return results
