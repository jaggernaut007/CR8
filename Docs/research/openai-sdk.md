# Research: OpenAI Python SDK (via langchain-openai)

**Date researched:** 2026-03-09
**Library version:** langchain-openai >=0.3
**Researched by:** Research Assistant Agent
**Status:** Current

---

## Question Being Answered

How do we use the OpenAI API through langchain-openai's ChatOpenAI wrapper for CR8's multi-model routing (nano/mini/premium tiers), and what are the security/cost implications?

## Sources Consulted

| Source | URL | Date accessed |
|--------|-----|---------------|
| LangChain ChatOpenAI Docs | https://python.langchain.com/api_reference/openai/ | 2026-03-09 |
| OpenAI Models Reference | https://developers.openai.com/api/docs/models | 2026-03-09 |
| OpenAI Structured Outputs | https://platform.openai.com/docs/guides/structured-outputs | 2026-03-09 |
| OpenAI Rate Limits | https://platform.openai.com/docs/guides/rate-limits | 2026-03-09 |
| OpenAI API Key Safety | https://help.openai.com/en/articles/5112595-best-practices-for-api-key-safety | 2026-03-09 |
| CVE Database | https://nvd.nist.gov/ | 2026-03-09 |
| langchain-openai PyPI | https://pypi.org/project/langchain-openai/ | 2026-03-09 |

## What We Found

### The Correct Approach

```python
from langchain_openai import ChatOpenAI

# Tier-based model routing (ADR-004)
MODELS = {
    "nano": "gpt-4o-mini",      # Extraction, temp 0.2 — $0.15/$0.60 per 1M tokens
    "mini": "gpt-4o-mini",      # Structured generation, temp 0.3
    "premium": "gpt-4o",        # Creative writing, temp 0.55 — $2.50/$10.00 per 1M tokens
}

def get_llm(tier: str = "nano", temperature: float | None = None) -> ChatOpenAI:
    model = MODELS[tier]
    return ChatOpenAI(
        model=model,
        temperature=temperature or {"nano": 0.2, "mini": 0.3, "premium": 0.55}[tier],
        max_retries=2,  # Retries on 5xx errors only; does NOT retry 429
    )
```

### Key API Methods / Concepts

| Method / Concept | Purpose | Notes / Gotchas |
|-----------------|---------|----------------|
| `ChatOpenAI(model=...)` | Create LLM wrapper | Model name must match OpenAI's current naming |
| `.invoke(messages)` | Synchronous call | Returns AIMessage; blocks until complete |
| `.ainvoke(messages)` | Async call | Returns AIMessage; use with `await` |
| `.stream(messages)` | Streaming response | Yields AIMessageChunk objects |
| `.with_structured_output(schema)` | Force JSON output matching Pydantic model | Uses OpenAI's native structured output mode |
| `.bind_tools(tools)` | Enable tool/function calling | Returns modified LLM instance |
| `max_retries` | Auto-retry on server errors | Only retries 5xx; does NOT handle 429 rate limits |
| `stream_usage=True` | Include token counts in stream | Required for cost tracking with streaming |

### Configuration Required

```bash
# .env
OPENAI_API_KEY=sk-...        # Required
OPENAI_ORG_ID=org-...        # Optional, for org billing
```

```python
# backend/config.py
class Settings(BaseSettings):
    openai_api_key: str = Field(alias="OPENAI_API_KEY")
```

### Cost Implications (ADR-004 Model Tiers)

| Tier | Model | Input $/1M tokens | Output $/1M tokens | Use Case |
|------|-------|-------------------|---------------------|----------|
| nano | gpt-4o-mini | $0.15 | $0.60 | Text extraction, parsing |
| mini | gpt-4o-mini | $0.15 | $0.60 | Structured generation |
| premium | gpt-4o | $2.50 | $10.00 | Creative writing, scripts |

## What We Ruled Out (and Why)

| Approach | Why Rejected |
|----------|-------------|
| Direct openai SDK | LangChain integration needed for pipeline state management |
| Anthropic Claude | OpenAI already integrated; would require dual-provider support |
| Local LLMs (Ollama) | Quality gap for creative writing; may revisit in v0.7 |

## Known Gotchas / Edge Cases

1. **`max_retries` does NOT handle 429 (rate limit)** — implement exponential backoff manually for rate limits
2. **Model names change** — OpenAI deprecates models; check model availability quarterly
3. **Structured output requires specific models** — `gpt-4o-mini` and `gpt-4o` support it; older models may not
4. **Token counting with streaming** — must set `stream_usage=True` or token counts are `None`
5. **API key in env** — `ChatOpenAI` auto-reads `OPENAI_API_KEY` from env; no need to pass explicitly

## Security Assessment

| Check | Result | Notes |
|-------|--------|-------|
| Open CVEs (critical/high) | 1 transitive (langchain-core) | CVE-2025-68664 (CVSS 9.3) — serialization injection |
| License | MIT (langchain-openai) | Compatible |
| Last release | Active (weekly) | LangChain team maintains |
| Maintainer count | 20+ | Enterprise-backed |
| Transitive dependencies | ~10 packages | openai, pydantic, httpx — all stable |
| Known security incidents | None in openai-python | Clean record |

### Critical Action Item

**CVE-2025-68664** in `langchain-core` (transitive dependency):
- CVSS 9.3 — serialization injection
- Fix: Update to `langchain>=1.2.5` or `langchain-core>=0.4`
- CR8 Impact: Low (server-side processing only), but should be patched

**Verdict:** SAFE to use after ensuring `langchain-core>=0.4` is pinned.

## Decision Made

Based on this research, we will:
> Continue using langchain-openai's ChatOpenAI for all LLM calls with 3-tier model routing (nano/mini/premium). Add exponential backoff for 429 rate limit errors. Ensure `langchain-core>=0.4` is pinned. Never expose API keys to frontend — all LLM calls route through backend.

## Files This Affects

- `backend/services/llm.py` — ChatOpenAI initialization, model routing
- `backend/config.py` — OPENAI_API_KEY setting, model name validation
- `backend/pipeline/agent_ingest.py` — Uses nano tier
- `backend/pipeline/agent_research.py` — Uses mini tier
- `backend/pipeline/agent_generate.py` — Uses premium tier for creative, nano for structured
- `pyproject.toml` — langchain-openai version pin

---
*If this research is more than 6 months old or the library has had a major version bump, re-verify before implementing.*
