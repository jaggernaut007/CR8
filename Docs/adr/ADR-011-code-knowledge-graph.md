# ADR-011: Code Knowledge Graph via Nexus-MCP

**Date:** 2026-03-11 (updated 2026-03-12)
**Status:** Accepted (superseded: CodeGrok + code-graph-mcp → Nexus-MCP)
**Deciders:** Shreyas Jagannath

---

## Context

CR8 has 127 Python files (~27K LOC) across backend pipeline, services, frontend routes, and two video microservices. AI agents currently load entire files into context to understand the codebase, wasting 50-60K tokens per response. Industry standard (GitHub Copilot, Cursor, Aider) uses a hybrid approach: semantic search (embeddings) + structural analysis (AST/call graphs). We evaluated 36+ MCP servers and initially chose CodeGrok + code-graph-mcp as two complementary tools. We have now consolidated to **Nexus-MCP**, a single unified server that combines all capabilities.

## Decision

> We will use **Nexus-MCP** as the single dev-time MCP server for code intelligence. Nexus-MCP combines hybrid search (vector + BM25 + graph via Reciprocal Rank Fusion), structural analysis (callers, callees, impact, complexity), and semantic memory — replacing the previous CodeGrok + code-graph-mcp dual setup.

**Why consolidate?** Nexus-MCP provides all capabilities of both predecessors in one server with:
- Hybrid search (vector + BM25 + graph fusion) instead of vector-only (CodeGrok)
- Integrated impact analysis and architecture overview
- Token-budgeted responses (summary/detailed/full) — agents request only the detail they need
- Semantic memory with TTL — persistent knowledge across sessions
- 15 tools, one process, <350MB RAM, fully local

### Nexus-MCP Tools (15)

| Category | Tools |
|----------|-------|
| **Core** | `status`, `health`, `index`, `search` |
| **Graph Analysis** | `find_symbol`, `find_callers`, `find_callees`, `analyze`, `impact`, `explain`, `overview`, `architecture` |
| **Memory** | `remember`, `recall`, `forget` |

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **Nexus-MCP (chosen)** | Unified hybrid search+structural+memory, 15 tools/1 server, token-budgeted, MIT, <350MB RAM | Newer project (v0.1.0) |
| CodeGrok + code-graph-mcp (previous) | Proven separately, each well-tested | Two servers, 17 tools, no hybrid fusion, no memory, ~400MB combined |
| CodeGrok only | Good semantic search | No structural analysis, no memory |
| code-graph-mcp only | Good structural analysis | No semantic search |
| Axon (KuzuDB graph) | Excellent impact analysis | igraph GPL license risk, overkill for 27K LOC |

## Consequences

**Positive:**
- 10-100x token savings on code search queries (hybrid fusion improves precision over vector-only)
- Single MCP process instead of two — simpler config, less RAM
- Token-budgeted responses prevent context bloat (summary ~500 tokens, detailed ~2K, full ~8K)
- Semantic memory persists project decisions and context across sessions
- Agents can use `explain` for combined graph+vector understanding in one call
- `impact` tool provides transitive change analysis before refactors

**Negative / Trade-offs:**
- Nexus-MCP is newer (v0.1.0) — less battle-tested than individual tools
- `.nexus/` storage directory added to .gitignore (regenerated on clone)

**Neutral:**
- No impact on runtime pipeline or production deployment (dev-time only)
- CodeGrok and code-graph-mcp configs removed from `.claude/mcp.json`

## Implementation Notes

- Files affected: `.claude/mcp.json`, `.gitignore`, `AGENTS.md`, `CLAUDE.md`, `scripts/init.sh`, `Makefile`, `mk-docs/getting-started/developer-workflow.md`, all agent .md files
- Patterns to follow: MCP server configured in `.claude/mcp.json` (project-scoped)
- Things to avoid: Don't add Nexus-MCP as a runtime dependency in pyproject.toml (dev-time MCP only); don't confuse Nexus-MCP's LanceDB with CR8's ChromaDB (separate purposes)

## References

- Nexus-MCP: https://github.com/jaggernaut007/Nexus-MCP (MIT)
- Previous research: `docs/research/code-intelligence-tools.md` (2026-03-06)
- Previous tools: CodeGrok (https://github.com/dondetir/CodeGrok_mcp), code-graph-mcp (https://github.com/entrepeneur4lyf/code-graph-mcp)
