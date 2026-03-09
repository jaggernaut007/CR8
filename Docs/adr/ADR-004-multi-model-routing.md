# ADR-004: Multi-Model Routing (Nano / Mini / Premium Tiers)
<!-- Architecture Decision Record
     Place in: docs/adr/ADR-004-multi-model-routing.md
     Reference from AGENTS.md so the agent knows these exist.
     The agent reads ADRs before making structural decisions. -->

**Date:** 2026-02-15
**Status:** Accepted
**Deciders:** Shreyas Jagannath (engineering lead)

---

## Context

CR8's 3-agent pipeline (Ingest, Research, Generate) makes dozens of LLM calls per run. These calls vary dramatically in complexity:

- **Ingest** extracts topics and keywords from parsed PDFs -- deterministic, low-reasoning work.
- **Research** synthesises gap analyses from curriculum chunks and web search results -- moderate structured reasoning.
- **Generate** produces learning modules, PPT slide structures, executive summaries, and video scripts -- ranging from simple aggregation to creative writing.

Using a single premium model (GPT-5.1) for all calls was the initial prototype approach. A typical 10-topic run made ~40 LLM calls, and profiling showed that 60% of those calls (extraction, validation, slide structuring) produced identical quality with cheaper models. At OpenAI's pricing, the premium model costs ~10-20x more per token than nano-class models. For a pipeline designed to run at scale (multiple users, multiple PDFs), cost was the primary constraint forcing a decision.

A secondary concern was temperature alignment. Extraction tasks need near-deterministic output (temp 0.2), structured generation needs slight creativity (temp 0.3), and video scripts need higher creativity (temp 0.55). A single-model approach required per-call temperature overrides scattered across agents, making defaults meaningless.

## Decision

> We will use a 3-tier model routing system (nano, mini, premium) with task-appropriate defaults for model selection and temperature, centralised in `get_llm()`.

**Tier definitions:**

| Tier | Default Model | Default Temp | Purpose |
|------|--------------|-------------|---------|
| `nano` | `gpt-5-nano` | 0.2 (`temp_analysis`) | Extraction, validation, summarisation |
| `mini` | `gpt-5-mini` | 0.3 (`temp_structured`) | Structured generation, gap analysis, slide structuring |
| `premium` | `gpt-5.1` | 0.55 (`temp_creative`) | Creative writing, critical-severity modules, video scripts |

**Severity-based routing** in the Generate agent adds a dynamic dimension: when generating learning modules, topics with `severity: "critical"` (largest curriculum-to-industry gaps) are routed to premium, while `moderate` and `minor` topics use mini. This ensures the highest-quality output where it matters most without paying premium cost for every module.

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **3-tier routing by task complexity (chosen)** | ~60-70% cost reduction vs single-model; temperature defaults match task needs; severity routing adds quality where it matters | Tier assignments are static per call site; "full" backward-compat alias adds minor confusion; no runtime validation of tier effectiveness |
| **Single model for everything** | Zero routing logic; consistent quality ceiling; simplest code | ~10-20x more expensive for extraction tasks; temperature must be overridden per-call; wasteful for deterministic work |
| **2-tier (cheap / expensive) only** | Simpler than 3 tiers; still captures the main cost split | Conflates extraction (temp 0.2, minimal reasoning) with structured generation (temp 0.3, moderate reasoning); loses the nano cost advantage |
| **Dynamic model selection based on input analysis** | Adapts to actual input complexity; potentially optimal per-call | Adds latency (classification LLM call before each real call); classification errors cause cascading quality issues; over-engineered for a pipeline with well-defined stages |

## Consequences

**Positive:**
- Bulk pipeline cost reduced ~60-70% by routing extraction and structuring to cheaper tiers
- Temperature presets are environment-configurable (`TEMP_ANALYSIS`, `TEMP_STRUCTURED`, `TEMP_CREATIVE`) -- tuning without code changes
- Severity-based routing in Generate automatically allocates premium capacity to the highest-impact topics
- All tiers share the same `ChatOpenAI` interface -- swapping a model is a single env var change
- `get_llm()` is the sole LLM entry point -- agents never instantiate `ChatOpenAI` directly

**Negative / Trade-offs:**
- Tier assignments are hardcoded at each call site -- if a "mini" task produces poor quality, code must change (not just config)
- The `"full"` alias (mapping to premium) exists for backward compatibility and adds a fourth name to explain
- No runtime metrics yet to validate that tier assignments are optimal -- relies on eval framework (`backend/evals/`) for offline quality checks

**Neutral:**
- Model names are configurable via env vars (`OPENAI_MODEL_NANO`, `OPENAI_MODEL_MINI`, `OPENAI_MODEL_PREMIUM`) -- the tiers are abstract, not tied to specific OpenAI model versions
- Temperature can be overridden per-call via the `temperature` parameter on `get_llm()`, so the defaults are not constraints

## Implementation Notes

- **Central routing**: `backend/services/llm.py` -- `_TIER_MAP` dict maps tier names to config attributes; `get_llm()` is the only public function
- **Config**: `backend/config.py` -- `openai_model_nano`, `openai_model_mini`, `openai_model_premium`, `temp_analysis`, `temp_structured`, `temp_creative`
- **Call sites by tier**:
  - `nano`: `agent_ingest.py` (topic extraction), `agent_generate.py` (executive summary)
  - `mini`: `agent_research.py` (gap analysis), `agent_generate.py` (PPT slide structuring, moderate/minor modules)
  - `premium`: `agent_generate.py` (critical modules, video scripts)
- **Severity routing**: `agent_generate.py::_generate_module()` -- checks `gap_data.get("severity")`, routes `"critical"` to premium, all others to mini
- **Pattern to follow**: Always call `get_llm("tier_name")` -- never instantiate `ChatOpenAI` directly in agents
- **Anti-patterns ruled out**: No per-agent model instantiation; no hardcoded model names outside `config.py`; no dynamic tier selection based on token counting or input analysis

## References

- LLM service: `backend/services/llm.py`
- Config: `backend/config.py`
- Severity routing: `backend/pipeline/agent_generate.py::_generate_module()`
- Tier tests: `backend/tests/test_services.py::TestGetLLM`
- Eval framework: `backend/evals/` (offline quality validation per tier)
