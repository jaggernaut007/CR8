# ADR-003: LangGraph 3-Agent Pipeline Architecture
<!-- Architecture Decision Record
     Place in: docs/adr/ADR-003-langgraph-three-agent-pipeline.md
     Reference from AGENTS.md so the agent knows these exist.
     The agent reads ADRs before making structural decisions. -->

**Date:** 2026-01-15
**Status:** Accepted
**Deciders:** Shreyas Jagannath (engineering lead)

---

## Context

CR8 transforms curriculum PDFs into multi-format learning materials (PDF guides, PowerPoint gap analyses, video scripts, videos). This requires a multi-stage pipeline: parsing and embedding input documents, enriching them with web research and gap analysis, then generating outputs in several formats.

The pipeline needed to satisfy these constraints:

1. **Typed state contract** between stages -- each stage must know exactly what prior stages produced, with IDE autocompletion and static analysis support.
2. **Explicit control flow** -- the transformation is inherently sequential (you cannot research topics before extracting them, or generate outputs before researching gaps). The orchestration framework should reflect this, not hide it.
3. **Independent testability** -- each stage should be testable in isolation by mocking its input state.
4. **Intra-stage parallelism** -- while stages run sequentially, work within a stage (e.g., researching 5 topics simultaneously) must be parallelizable.
5. **Future extensibility** -- adding conditional edges (e.g., skip Research for simple reformatting jobs) or new stages should not require rewriting the orchestration layer.

## Decision

> We will use LangGraph StateGraph with a 3-agent linear pipeline (Ingest, Research, Generate) and TypedDict shared state for transforming curriculum PDFs into multi-format learning materials.

The three agents have distinct responsibilities and I/O patterns:

| Agent | Role | LLM Tier | Key Services |
|-------|------|----------|--------------|
| **Ingest** | Parse files, summarize, extract topics, embed into ChromaDB | nano | file_parser, chromadb_store |
| **Research** | Web search per topic, gap analysis, store enrichments | mini | web_search, chromadb_store |
| **Generate** | Produce PDF, PPT, scripts, videos from enriched topics | premium/mini (severity-routed) | pdf_builder, ppt_builder, video_builder |

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **LangGraph StateGraph + TypedDict (chosen)** | Typed state contract with IDE support; explicit node/edge topology; compiled graph validates structure at build time; supports conditional edges and cycles for future use; lightweight -- graph.py is 48 lines | Framework dependency (langgraph + langchain-core); TypedDict does not enforce at runtime (missing fields cause KeyError, not validation errors) |
| **Plain LangChain sequential chains** | Familiar LangChain API; no additional dependency beyond langchain | No typed state between chain steps; chain abstraction hides data flow; harder to add conditional routing or new stages; state is implicit in chain memory |
| **Direct OpenAI function calling + manual orchestration** | Zero framework overhead; full control over every API call | Reinvents state passing, error handling, and cancellation; no graph visualization or debugging tools; every new stage requires custom wiring code |
| **CrewAI or AutoGen multi-agent framework** | Built-in role definitions; agent negotiation and delegation patterns | Designed for collaborative multi-agent negotiation, not linear pipelines; role-based abstraction adds overhead for no benefit when flow is always Ingest then Research then Generate; heavier dependency; less explicit control over state passing |

## Consequences

**Positive:**
- Each agent is a pure function `(PipelineState) -> dict` -- testable by constructing input state and asserting output fields (802 tests, zero real API calls).
- Model routing per agent tier (nano for extraction, mini for analysis, premium for generation) optimizes cost vs. quality -- critical gaps get GPT-5.1, moderate/minor get GPT-5-mini (~10x cheaper).
- Adding a new pipeline stage requires only `graph.add_node()` + `graph.add_edge()` in graph.py and a new field in PipelineState.
- Cancellation propagates naturally: `_check_cancelled()` is called at checkpoints within each agent and between ThreadPoolExecutor futures.
- Prompts are separated into `backend/prompts/` (ingest.py, research.py, generate.py, ppt.py, video.py) -- not inlined in agent code.

**Negative / Trade-offs:**
- Linear graph means no parallelism between agents -- Ingest must complete before Research starts, even if some topics could be researched early.
- `agent_generate.py` is ~970 lines because 3 agents means Generate handles all output formats (PDF, PPT, Script, Video). This was a conscious trade-off: keep the graph topology simple, accept a larger Generate agent. The complexity is managed by delegating to isolated service modules (pdf_builder, ppt_builder, video_builder).
- TypedDict provides no runtime validation -- a bug in one agent that omits a field produces a KeyError in the next agent, not a descriptive validation error.
- ChromaDB acts as shared side-channel state outside PipelineState (Ingest writes curriculum collection, Research reads it and writes research collection, Generate reads both). This is invisible in the graph topology.

**Neutral:**
- Intra-stage parallelism uses `ThreadPoolExecutor` within each agent, not LangGraph's parallelism primitives. This is intentional -- the parallelism is over topics/files, not over graph nodes.
- Splitting Generate into sub-agents (separate PDF, PPT, Video nodes) is architecturally possible but not planned for any specific version. The current service-delegation pattern works because each format's logic is fully encapsulated in its builder module.

## Implementation Notes

- Files affected:
  - `backend/pipeline/graph.py` -- graph definition (3 nodes, 4 edges, 48 lines)
  - `backend/pipeline/state.py` -- PipelineState TypedDict with field ownership comments
  - `backend/pipeline/agent_ingest.py` -- Agent 1 (186 lines)
  - `backend/pipeline/agent_research.py` -- Agent 2 (171 lines)
  - `backend/pipeline/agent_generate.py` -- Agent 3 (970 lines)
  - `backend/services/llm.py` -- 3-tier model routing (nano/mini/premium)
  - `backend/run_pipeline.py` -- pipeline entry point via `run_job()`
- Patterns to follow:
  - Agent functions are named `{role}_node` and accept `PipelineState`, return `dict`
  - No LLM calls in graph.py -- it is pure orchestration
  - All LLM access goes through `get_llm(tier)`, never direct OpenAI client usage
  - State fields are grouped by producing agent with comments (`# After Agent 1`, etc.)
  - `_check_cancelled()` must be called at every `as_completed` iteration and before expensive operations
- Things to avoid:
  - Do not add business logic to graph.py -- it should remain a topology declaration
  - Do not pass mutable objects through PipelineState fields (use serializable types)
  - Do not access ChromaDB in graph.py -- side-channel state is managed within agents
  - Do not add more than one new node without updating this ADR

## References

- Graph definition: `backend/pipeline/graph.py`
- State schema: `backend/pipeline/state.py`
- Agent implementations: `backend/pipeline/agent_ingest.py`, `agent_research.py`, `agent_generate.py`
- Model routing: `backend/services/llm.py` (3-tier map: nano, mini, premium)
- Prompt templates: `backend/prompts/` (ingest.py, research.py, generate.py, ppt.py, video.py)
- LangGraph docs: https://langchain-ai.github.io/langgraph/
- ADR-001: Three-Tier Video Fallback (consequence of Generate agent's video dispatch)
