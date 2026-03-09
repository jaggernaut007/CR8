# Web Search

**File**: `backend/services/web_search.py`

Wrapper around Tavily's search API for finding industry context.

## Usage

```python
from backend.services.web_search import search

results = search("transformer models job requirements 2025", max_results=5)
# Returns: [
#   {"title": "...", "url": "...", "content": "...", "score": 0.95},
#   ...
# ]
```

## Function Signature

```python
def search(query: str, max_results: int = 5) -> list[dict]
```

Searches the web via Tavily and returns a list of result dicts.

Each returned dict contains:

| Field | Type | Description |
|-------|------|-------------|
| `title` | `str` | Page title |
| `url` | `str` | Source URL |
| `content` | `str` | Extracted page content |
| `score` | `float` | Relevance score (0-1) |

## Error Handling

`search()` wraps the Tavily API call in a `try/except`. If Tavily raises any exception (network timeout, rate limit, API error), the function logs the error with `exc_info=True` and returns `[]`. This prevents a single failed web search from crashing the Research agent — the topic continues with empty search results rather than failing the entire pipeline.

## Configuration Notes

- Uses `search_depth="basic"` for fast results
- The Tavily client is lazily initialised as a singleton on first call
- Requires `TAVILY_API_KEY` environment variable
- The research agent runs two searches per topic in parallel (job requirements + industry trends)
- Returns `[]` on any Tavily API error — the pipeline continues with empty results for that topic
