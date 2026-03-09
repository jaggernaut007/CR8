# Research: Tavily Python SDK

**Date researched:** 2026-03-09
**Library version:** >=0.5 (tavily-python, latest: v0.7.22)
**Researched by:** Research Assistant Agent
**Status:** Current

---

## Question Being Answered

How do we use the Tavily Python SDK to perform web searches for the Research agent in the CR8 pipeline, including initialization, result handling, rate limits, and security considerations?

## Sources Consulted

| Source | URL | Date accessed |
|--------|-----|---------------|
| SDK Reference | https://docs.tavily.com/sdk/python/reference | 2026-03-09 |
| GitHub Repository | https://github.com/tavily-ai/tavily-python | 2026-03-09 |
| Credits & Pricing | https://docs.tavily.com/documentation/api-credits | 2026-03-09 |
| API Key Management | https://docs.tavily.com/documentation/best-practices/api-key-management | 2026-03-09 |
| LangChain Integration | https://docs.tavily.com/documentation/integrations/langchain | 2026-03-09 |
| Snyk Package Health | https://snyk.io/advisor/python/tavily-python | 2026-03-09 |

## What We Found

### The Correct Approach

```python
from tavily import TavilyClient
from backend.config import settings

_client = None

def _get_client() -> TavilyClient:
    """Lazily initialise a singleton Tavily client."""
    global _client
    if _client is None:
        _client = TavilyClient(api_key=settings.tavily_api_key)
    return _client

def search(query: str, max_results: int = 5) -> list[dict]:
    """Search with graceful degradation — never crash the pipeline."""
    client = _get_client()
    try:
        response = client.search(
            query=query,
            max_results=max_results,
            search_depth="basic",  # 1 credit; "advanced" = 2 credits
        )
    except Exception:
        logger.error("Tavily search failed: %s", query[:80], exc_info=True)
        return []
    return response.get("results", [])
```

### Key API Methods / Concepts

| Method / Concept | Purpose | Notes / Gotchas |
|-----------------|---------|----------------|
| `TavilyClient(api_key)` | Initialize client | Must pass key explicitly; no automatic env var loading |
| `client.search(query, **kwargs)` | Execute search | Returns dict with `results` key |
| `AsyncTavilyClient` | Async variant | Available since v0.3.4; identical interface |
| `search_depth` | `"basic"` or `"advanced"` | Basic = 1 credit, faster; Advanced = 2 credits, deeper |
| `max_results` | Number of results (1–20) | Default 5; sorted by relevance score |
| `include_domains` / `exclude_domains` | URL domain filtering | List of domain strings |
| `topic` | `"general"` or `"news"` | General for web, news for recent articles |
| `include_answer` | Quick answer summary | Adds 1–2 credits; `"basic"` or `"advanced"` |
| `include_raw_content` | Full page HTML | Adds 1 credit per result; use sparingly |

### Response Structure

```python
response = client.search(query="AI breakthroughs", max_results=5)
# {
#     "results": [
#         {"title": "...", "url": "...", "content": "...", "score": 0.95},
#         ...
#     ],
#     "query": "AI breakthroughs",
#     "response_time": 0.23
# }
```

### Rate Limits and Quotas

| Tier | Credits/Month | Rate Limit | Cost |
|------|---------------|------------|------|
| Free | 1,000 | 100 req/min | $0 |
| Starter | 10,000 | Higher | $99/mo |
| Professional | 50,000 | Higher | $299/mo |
| Enterprise | 100,000 | Higher | $500/mo |

- Credits never roll over — unused expire at month-end
- Basic search = 1 credit; Advanced = 2 credits
- Pay-as-you-go overages: $0.008/credit

### Configuration Required

```bash
# .env
TAVILY_API_KEY=tvly-YOUR_API_KEY
```

```python
# backend/config.py
class Settings(BaseSettings):
    tavily_api_key: str = Field(default="", alias="TAVILY_API_KEY")
```

## What We Ruled Out (and Why)

| Approach | Why Rejected |
|----------|-------------|
| Google Custom Search API | More complex setup, less relevant results for academic content |
| SerpAPI | More expensive, heavier SDK |
| Bing Search API | Requires Azure subscription |
| langchain-tavily (LangChain tool) | More indirection; CR8 uses direct SDK for simpler mocking/debugging |

## Known Gotchas / Edge Cases

1. **Always use `.get("results", [])` defensively** — key may be missing on API errors
2. **Some result fields may be absent** — use `.get()` for title, url, content, score
3. **Free tier credits expire monthly** — monitor at https://app.tavily.com/home
4. **Rate limit (100 req/min on free)** — unlikely to hit in normal pipeline use
5. **No built-in caching** — CR8 should cache results in ChromaDB to avoid duplicate searches

## Security Assessment

| Check | Result | Notes |
|-------|--------|-------|
| Open CVEs (critical/high) | None | Clean as of 2026-03-09 |
| License | MIT | Fully compatible |
| Last release | 2026-01-18 (v0.7.22) | Active maintenance |
| Maintainer count | 2+ | Tavily.AI team |
| Transitive dependencies | 4–5 packages | httpx, requests — well-established HTTP libs |
| Known security incidents | CVE-2026-30856 (MEDIUM) | Affects MCP servers, not the Python SDK itself |

### Data Privacy

- Search queries are sent to Tavily servers and may be logged for analytics
- Do not search for PII or sensitive student data
- API key should only be in env vars, never in code

**Verdict:** SAFE to use. Minimal dependencies, MIT license, no direct CVEs.

## Decision Made

Based on this research, we will:
> Continue using `tavily-python>=0.5` with the singleton pattern in `web_search.py`. Use `search_depth="basic"` (1 credit) by default to conserve the 1,000 monthly free credits. Reserve `"advanced"` for critical topics. Store API key in env vars only. Cache results in ChromaDB to avoid duplicate queries.

## Files This Affects

- `backend/services/web_search.py` — TavilyClient singleton, search logic, error handling
- `backend/config.py` — `TAVILY_API_KEY` setting
- `backend/pipeline/agent_research.py` — Calls `web_search.search()` for topic enrichment
- `.env.example` — Documents `TAVILY_API_KEY` requirement

---
*If this research is more than 6 months old or the library has had a major version bump, re-verify before implementing.*
