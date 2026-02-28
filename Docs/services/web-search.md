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

## Configuration Notes

- Uses `search_depth="basic"` for fast results
- The Tavily client is lazily initialized as a singleton
- Requires `TAVILY_API_KEY` environment variable
- The research agent runs two searches per topic in parallel (job requirements + trends)
