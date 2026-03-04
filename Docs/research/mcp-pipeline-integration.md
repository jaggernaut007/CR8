# Research: MCP Pipeline Integration (Should CR8 Use MCP Internally?)

**Date researched:** 2026-03-04
**Library version:** MCP Spec 2025-11-25, langchain-mcp-adapters (pre-v1), Python MCP SDK (latest)
**Researched by:** Claude Code research-assistant agent
**Status:** Current

---

## Question Being Answered

Should CR8 replace its current direct Python service calls (Tavily, ChromaDB, PyMuPDF, etc.) with MCP server equivalents to simplify the pipeline?

> How does MCP fit as an internal transport layer for an existing LangGraph pipeline, and what are the practical tradeoffs?

## Sources Consulted

| Source | URL | Date accessed |
|--------|-----|---------------|
| MCP Specification | https://modelcontextprotocol.io/specification/2025-11-25 | 2026-03-04 |
| LangChain MCP Adapters | https://github.com/langchain-ai/langchain-mcp-adapters | 2026-03-04 |
| Tavily MCP Docs | https://docs.tavily.com/documentation/mcp | 2026-03-04 |
| ChromaDB MCP Integration | https://docs.trychroma.com/integrations/frameworks/anthropic-mcp | 2026-03-04 |
| PDF Reader MCP Server | https://github.com/SylphxAI/pdf-reader-mcp | 2026-03-04 |
| MCP vs Direct API Comparison | https://modelslab.com/blog/api/mcp-vs-direct-api-ai-integration | 2026-03-04 |
| When to Use MCP: Pros/Cons | https://www.getknit.dev/blog/the-pros-and-cons-of-adopting-mcp-today | 2026-03-04 |
| LangGraph MCP Integration Guide | https://generect.com/blog/langgraph-mcp/ | 2026-03-04 |
| Python MCP SDK | https://github.com/modelcontextprotocol/python-sdk | 2026-03-04 |

## What We Found

### MCP Architecture Overview

MCP is a JSON-RPC 2.0 protocol for AI-to-tool communication:
```
Host (CR8) → MCP Client → MCP Server (Tavily, ChromaDB, etc.)
```

Two transports:
- **stdio** (local): <1ms overhead per call
- **HTTP** (remote): 50-100ms overhead per call + JSON serialization

### Existing MCP Servers for CR8's Services

| CR8 Service | MCP Server Available | Maturity |
|-------------|---------------------|----------|
| `web_search.py` (Tavily) | `tavily-mcp` (official) | Production |
| `chromadb_store.py` | `chroma-mcp-server` (official) | Official, less battle-tested |
| `file_parser.py` (PyMuPDF) | `pdf-reader-mcp` | Production (read-only) |
| `pdf_builder.py` (fpdf2) | None | — |
| `ppt_builder.py` (python-pptx) | None | — |
| `video_builder.py` (MoviePy) | None | — |
| `llm.py` (OpenAI) | N/A | Direct is correct |

### LangChain-MCP Adapters (LangGraph Integration)

Official library: `langchain-mcp-adapters`

```python
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp import StdioClientSession

# Convert MCP tools to LangChain-compatible tools
session = StdioClientSession(command="python", args=["-m", "mcp.tavily"])
tools = await load_mcp_tools(session)  # → list of LangChain Tool objects

# Use in LangGraph agent — no code changes to graph structure
```

The agent sees standard LangChain tools regardless of source (MCP, direct API, or in-process).

### Performance Analysis

| Transport | Overhead | CR8 Context |
|-----------|----------|-------------|
| stdio (local) | +0-2ms/call | Negligible for Tavily (~1-2s) or ChromaDB (~200-500ms) |
| HTTP (remote) | +50-100ms/call | <5% of total latency for search/query ops |
| File I/O via MCP | +20% | Visible for PyMuPDF slide export (currently ~14s) |
| Write ops via MCP | +20-50% | Significant for PDF/PPT/video generation |

### Key API Methods / Concepts

| Method / Concept | Purpose | Notes |
|-----------------|---------|-------|
| `tavily-mcp` tools | `search`, `extract` | Drop-in replacement for `web_search.py` |
| `chroma-mcp-server` tools | `query_collection`, `add_documents` | Needs separate process; only helps if sharing DB |
| `langchain-mcp-adapters` | `load_mcp_tools(session)` | Converts MCP tools to LangChain tools for LangGraph |
| `StdioClientSession` | Local MCP connection | <1ms overhead, recommended for local services |

## What We Ruled Out (and Why)

| Approach | Why Rejected |
|----------|-------------|
| **Replace all services with MCP** | MCP is read-biased; CR8 is mostly write-heavy (PDF, PPT, video generation). No MCP servers exist for 3 of 6 services. Adds process management complexity for no gain. |
| **Replace Tavily with tavily-mcp now** | Current `web_search.py` is 1 file, works fine. MCP adds a process to manage. Benefit only materialises if swapping search providers frequently. |
| **Replace ChromaDB with chroma-mcp now** | Local ChromaDB is fast and CR8 is the only consumer. MCP only helps if sharing the DB across multiple independent agents. |
| **PDF parsing via pdf-reader-mcp** | Performance-critical path (slide export). MCP adds ~20% latency and `file_parser.py` already handles both PDF and PPTX formats with custom logic. |
| **Full langchain-mcp-adapters adoption** | Pre-v1 library, still maturing. Adding it now creates a dependency on an unstable API for zero functional benefit. |

## Known Gotchas / Edge Cases

- **MCP is read-biased**: Designed for AI reasoning + tool calling (search, fetch, query), not for content generation. Write operations (PDF, video) add overhead with no upside.
- **Operational burden**: Each MCP server = another process to deploy, monitor, restart. Break-even only if using the same MCP in multiple agents or swapping providers frequently.
- **Security**: Tavily MCP remote URL can leak API keys — use env vars, not URL params. ChromaDB MCP over stdio is safe; HTTP needs auth.
- **Ecosystem maturity**: `langchain-mcp-adapters` is pre-v1 (2025-2026). No breaking changes yet, but monitor.
- **Write performance**: File I/O, PDF generation, and video composition are 20-50% slower via MCP due to serialization overhead.
- **Process lifecycle**: MCP servers started via stdio are child processes — if the parent crashes, orphan servers may linger.

## Decision Made

Based on this research:

> **CR8 will NOT adopt MCP as an internal pipeline transport layer for v0.3-v0.6.**
>
> Rationale:
> 1. CR8's pipeline is write-heavy — MCP is designed for read operations
> 2. No MCP servers exist for 3 of 6 core services (PDF, PPT, video builders)
> 3. Current direct Python calls are simpler, faster, and easier to debug
> 4. Adding MCP would increase operational complexity (process management) without reducing code complexity
> 5. `langchain-mcp-adapters` is pre-v1 — premature to depend on it
>
> **Where MCP DOES fit CR8:**
> - **v0.5**: Expose CR8 itself as an MCP server via FastMCP (let other AI agents call the pipeline)
> - **v0.5+**: If the Quiz Agent needs to compose tools from multiple external sources, evaluate `langchain-mcp-adapters` then
> - **Future**: If CR8 needs to swap search providers (Tavily → Google → Brave), MCP becomes the right abstraction layer

## Files This Affects

Current version (v0.3-v0.4):
- No code changes needed — keep all services as direct Python calls

Future versions (v0.5+):
- `frontend/app.py` — mount FastMCP to expose CR8 as an MCP server (already in v0.5 plan)
- `backend/services/web_search.py` — potential Tavily MCP swap (only if provider swapping needed)
- `backend/services/chromadb_store.py` — potential ChromaDB MCP swap (only if multi-agent scenario emerges)

---
*If this research is more than 6 months old or MCP has had a major spec revision, re-verify before implementing.*
