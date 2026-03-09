# Research: LangGraph Core Pipeline Orchestration

**Date researched:** 2026-03-09
**Library version:** >=0.2 (v1.0 stable released late 2025)
**Researched by:** Research Assistant Agent
**Status:** Current

---

## Question Being Answered

How do we use LangGraph's StateGraph to orchestrate the 3-agent pipeline (Ingest → Research → Generate) in CR8, and what are the security/stability implications?

## Sources Consulted

| Source | URL | Date accessed |
|--------|-----|---------------|
| LangGraph Official Docs | https://langchain-ai.github.io/langgraph/ | 2026-03-09 |
| LangGraph GitHub | https://github.com/langchain-ai/langgraph | 2026-03-09 |
| LangGraph API Reference | https://langchain-ai.github.io/langgraph/reference/ | 2026-03-09 |
| CVE Database (NVD) | https://nvd.nist.gov/ | 2026-03-09 |

> **Agent note:** Always use official LangGraph documentation. Pin the exact version in pyproject.toml.

## What We Found

### The Correct Approach

CR8's current implementation is idiomatic and correct:

```python
from langgraph.graph import StateGraph, END
from backend.pipeline.state import PipelineState

# Build the graph
graph = StateGraph(PipelineState)
graph.add_node("ingest", ingest_node)
graph.add_node("research", research_node)
graph.add_node("generate", generate_node)

graph.set_entry_point("ingest")
graph.add_edge("ingest", "research")
graph.add_edge("research", "generate")
graph.add_edge("generate", END)

app = graph.compile()

# Run the pipeline
result = app.invoke(initial_state)
```

### Key API Methods / Concepts

| Method / Concept | Purpose | Notes / Gotchas |
|-----------------|---------|----------------|
| `StateGraph(state_schema)` | Create graph with typed state | Uses TypedDict for state shape |
| `graph.add_node(name, fn)` | Register a node function | Function receives full state, returns partial state dict |
| `graph.add_edge(a, b)` | Connect nodes sequentially | Linear pipeline — no conditional routing needed for CR8 |
| `graph.add_conditional_edges()` | Route based on state | Available for future branching (e.g., skip video if not requested) |
| `graph.set_entry_point(name)` | Set first node | Must be called before compile |
| `graph.compile()` | Build executable graph | Returns CompiledGraph with `.invoke()` and `.stream()` |
| `app.invoke(state)` | Run synchronously | Returns final state; used in `backend/run_pipeline.py` |
| `app.stream(state)` | Run with streaming | Yields intermediate state updates per node |

### State Management with TypedDict

```python
from typing import TypedDict

class PipelineState(TypedDict):
    # Ingest agent owns these
    raw_text: str
    modules_md: str
    # Research agent owns these
    research_context: list[dict]
    # Generate agent owns these
    pdf_path: str
    ppt_path: str
    script_path: str
    video_paths: list[str]
```

**Key behavior:** Node functions return partial state dicts. LangGraph merges them into the full state. Fields not returned are preserved from prior state.

### Configuration Required

```toml
# pyproject.toml
[project]
dependencies = [
    "langgraph>=0.2",
    "langchain-core>=0.4",  # IMPORTANT: CVE mitigation
    "langchain-openai>=0.3",
]
```

## What We Ruled Out (and Why)

| Approach | Why Rejected |
|----------|-------------|
| Raw asyncio orchestration | No state management, no graph visualization, no retry |
| Prefect / Airflow | Overkill for single-pipeline; designed for batch DAGs |
| Custom state machine | Reinventing LangGraph; no community support |
| LangGraph checkpointing | Not needed yet (stateless HTTP pipeline); defer to Phase 2 |

## Known Gotchas / Edge Cases

1. **State merging is shallow** — nested dicts are replaced, not deep-merged. If two nodes return `{"metadata": {...}}`, the second overwrites the first entirely.
2. **Node functions must return dicts** — returning `None` or a non-dict causes silent failures.
3. **compile() is not idempotent** — calling it twice on the same graph object can cause issues. Build fresh graphs.
4. **Streaming requires explicit handling** — `.stream()` yields `(node_name, state_update)` tuples, not final state.
5. **Error in any node stops the pipeline** — no built-in retry. CR8 handles this with try/except in each node.

## Security Assessment

| Check | Result | Notes |
|-------|--------|-------|
| Open CVEs (critical/high) | 2 (low risk for CR8) | See details below |
| License | MIT | Fully compatible with any deployment |
| Last release | Active (weekly) | 20+ maintainers (LangChain AI team) |
| Maintainer count | 20+ | Enterprise-backed, healthy project |
| Transitive dependencies | ~15 packages | msgpack, pydantic, typing-extensions — all stable |
| Known security incidents | None direct | CVEs are in adjacent packages |

### CVE Details

**CVE-2025-64439** (CVSS 7.4 — RCE in JsonPlusSerializer)
- Affects: `langgraph-checkpoint < 3.0`
- CR8 Impact: **NOT VULNERABLE** — CR8 doesn't use checkpointing (stateless HTTP pipeline)
- Mitigation: When checkpointing is added (Phase 2), require `langgraph-checkpoint>=3.0`

**CVE-2025-68664** (CVSS 8.6 — langchain-core serialization injection)
- Affects: `langchain-core < 0.4`
- CR8 Impact: **LOW RISK** — LLM responses processed server-side, not streamed to clients
- Mitigation: Ensure `langchain-core>=0.4` is pinned in `uv.lock`

**Verdict:** SAFE to use. No blockers. Both CVEs have clear mitigations.

## Decision Made

Based on this research, we will:
> Continue using LangGraph >=0.2 as the core pipeline orchestrator. The current StateGraph + 3 sequential nodes architecture is idiomatic, correct, and battle-tested. Ensure `langchain-core>=0.4` is pinned to mitigate CVE-2025-68664. Defer checkpointing to Phase 2 (when added, require `langgraph-checkpoint>=3.0`).

## Files This Affects

- `backend/pipeline/graph.py` — StateGraph definition, node wiring, compile
- `backend/pipeline/state.py` — PipelineState TypedDict
- `backend/pipeline/agent_ingest.py` — Ingest node function
- `backend/pipeline/agent_research.py` — Research node function
- `backend/pipeline/agent_generate.py` — Generate node function
- `backend/run_pipeline.py` — `app.invoke()` entry point
- `pyproject.toml` — Version pins

---
*If this research is more than 6 months old or the library has had a major version bump, re-verify before implementing.*
