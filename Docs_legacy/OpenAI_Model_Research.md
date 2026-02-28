> **DEPRECATED** — This file has been superseded by the new documentation site at `docs/`. See `docs/design/model-research.md` for the current version.
>
> This file is kept for reference only and will be removed in a future cleanup.

---

# OpenAI Model Research & Pipeline Token Budget

Reference document for model selection, pricing, and token budget management across the CR8 pipeline.

Last updated: February 2026

---

## Token Budget Constraints

| Tier | Daily Limit | Models |
|------|-------------|--------|
| **Premium** | 250,000 tokens/day | gpt-5.2, gpt-5.1, gpt-5.1-codex, gpt-5-codex, gpt-5, gpt-5-chat-latest, gpt-4.1, gpt-4o, o1, o3 |
| **Mini/Nano** | 2,500,000 tokens/day | gpt-5.1-codex-mini, gpt-5-mini, gpt-5-nano, gpt-4.1-mini, gpt-4.1-nano, gpt-4o-mini, o1-mini, o3-mini, o4-mini, codex-mini-latest |

---

## Premium Tier Models

| Model | Input $/1M | Output $/1M | Context Window | Max Output | JSON Mode | Speed | Best For |
|-------|-----------|-------------|----------------|------------|-----------|-------|----------|
| **gpt-5.2** | $2.00 | $16.00 | 1M | 32K | Yes | Medium | Highest quality, complex reasoning |
| **gpt-5.1** | $1.25 | $10.00 | 1M | 32K | Yes | Fast | Best quality/cost ratio for premium tasks |
| **gpt-5.1-codex** | $1.25 | $10.00 | 1M | 32K | Yes | Fast | Code-optimized variant of 5.1 |
| **gpt-5** | $1.00 | $8.00 | 128K | 16K | Yes | Fast | Previous gen, still capable |
| **gpt-5-codex** | $1.00 | $8.00 | 128K | 16K | Yes | Fast | Code-optimized variant of 5 |
| **gpt-5-chat-latest** | $1.00 | $8.00 | 128K | 16K | Limited | Fast | Chat-tuned, may lack structured output reliability |
| **gpt-4.1** | $2.00 | $8.00 | 1M | 32K | Yes | Medium | Legacy, being deprecated |
| **gpt-4o** | $2.50 | $10.00 | 128K | 16K | Yes | Fast | Legacy multimodal, being deprecated |
| **o1** | $15.00 | $60.00 | 200K | 100K | Yes | Slow | Deep reasoning (hidden reasoning tokens billed as output) |
| **o3** | $10.00 | $40.00 | 200K | 100K | Yes | Slow | Reasoning (hidden reasoning tokens billed as output) |

### Key Warnings — Premium Tier

- **o-series models (o1, o3)**: Use hidden "reasoning tokens" that are billed as output tokens but not visible in the response. A 500-word response might consume 5,000+ output tokens. Avoid for high-volume tasks.
- **gpt-5-chat-latest**: Optimized for conversational use, may produce less reliable structured JSON output. Not recommended for pipeline tasks requiring strict JSON schemas.
- **gpt-4.1/gpt-4o**: Older generation, scheduled for deprecation. Avoid for new implementations.
- **Prompt caching**: All gpt-5.x models support prompt caching at 50% input cost discount for cached prefixes. Useful when the same system prompt is reused across calls.

---

## Mini/Nano Tier Models

| Model | Input $/1M | Output $/1M | Context Window | Max Output | JSON Mode | Speed | Best For |
|-------|-----------|-------------|----------------|------------|-----------|-------|----------|
| **gpt-5-mini** | $0.25 | $2.00 | 1M | 16K | Yes | Very Fast | Analysis, structured output, JSON generation |
| **gpt-5-nano** | $0.05 | $0.40 | 1M | 16K | Yes | Very Fast | Summarization, extraction, validation |
| **gpt-5.1-codex-mini** | $0.25 | $2.00 | 1M | 16K | Yes | Very Fast | Code tasks at mini tier |
| **gpt-4.1-mini** | $0.40 | $1.60 | 1M | 16K | Yes | Fast | Legacy mini, being deprecated |
| **gpt-4.1-nano** | $0.10 | $0.40 | 1M | 16K | Yes | Very Fast | Legacy nano, being deprecated |
| **gpt-4o-mini** | $0.15 | $0.60 | 128K | 16K | Yes | Fast | Legacy, being deprecated |
| **o1-mini** | $3.00 | $12.00 | 128K | 65K | Yes | Medium | Lightweight reasoning (hidden tokens still apply) |
| **o3-mini** | $1.10 | $4.40 | 200K | 100K | Yes | Medium | Lightweight reasoning (hidden tokens still apply) |
| **o4-mini** | $1.10 | $4.40 | 200K | 100K | Yes | Medium | Latest mini reasoning model |
| **codex-mini-latest** | $0.25 | $2.00 | 1M | 16K | Yes | Very Fast | Code-focused mini |

### Key Warnings — Mini/Nano Tier

- **o-series mini models**: Same hidden reasoning token issue as premium o-series. Avoid for high-volume extraction/summarization.
- **gpt-4.1-mini/nano and gpt-4o-mini**: Older generation, scheduled for deprecation. Use gpt-5-mini/nano instead.
- **gpt-5-nano at $0.05/$0.40**: 5x cheaper than gpt-5-mini for input, same speed. Ideal for summarization and extraction tasks where quality difference is minimal.

---

## Pipeline Task-to-Model Matrix

| Pipeline Task | Model | Tier | Temperature | Rationale |
|---------------|-------|------|-------------|-----------|
| File summarization | gpt-5-nano | Nano | 0.2 | Summarization is nano's sweet spot; 5x cheaper than mini |
| Chunk summarization (map) | gpt-5-nano | Nano | 0.2 | Short chunk summaries, high volume |
| Summary reduction (reduce) | gpt-5-nano | Nano | 0.2 | Combining summaries, straightforward |
| Topic extraction | gpt-5-nano | Nano | 0.2 | Simple structured extraction from short text |
| Gap analysis | gpt-5-mini | Mini | 0.2 | Analytical comparison needs mini quality for nuance |
| Module generation (critical severity) | gpt-5.1 | Premium | 0.3 | Only for critical-severity topics; best quality |
| Module generation (moderate/minor) | gpt-5-mini | Mini | 0.3 | Frees premium budget; mini handles well-defined generation |
| Module validation | gpt-5-nano | Nano | 0.2 | Lightweight section/quality checks (done in code, not LLM) |
| PPT per-topic slide structuring | gpt-5-mini | Mini | 0.3 | JSON structuring from single topic's data |
| PPT executive summary | gpt-5-nano | Nano | 0.2 | Aggregation/summarization of pre-computed data |
| Video scripts | gpt-5.1 | Premium | 0.55 | Creative writing quality scales with model capability |

### Why These Choices

- **gpt-5.1 over gpt-5.2 for premium**: gpt-5.1 is 37% cheaper per output token ($10 vs $16) with similar quality for educational content. The extra reasoning depth of 5.2 is unnecessary for our structured generation tasks.
- **gpt-5-nano over gpt-5-mini for extraction**: Summarization and extraction tasks show minimal quality difference between nano and mini, but nano is 5x cheaper on input. At high volume (20+ files, multiple chunks per file), this saves significant budget.
- **gpt-5-mini for gap analysis**: Gap analysis requires comparing curriculum content against industry trends and identifying nuanced differences. Mini's analytical capability is needed here; nano tends to miss subtleties.
- **Temperature 0.55 for scripts**: Higher temperature produces more natural, varied spoken-word content. Lower temperatures (0.2-0.3) produce more formulaic scripts that sound robotic when spoken by an avatar.
- **Severity-based routing**: Only critical-severity topics (typically 3-5 out of 20) use the premium model. This concentrates premium budget where it matters most.

---

## Token Budget Analysis (Per 20-Topic Run)

### Before Optimization

| Task | Model | Calls | Input/Call | Output/Call | Total Input | Total Output |
|------|-------|-------|-----------|-------------|-------------|--------------|
| File summarization | gpt-5-mini | 8 | 8K | 500 | 64K | 4K |
| Topic extraction | gpt-5-mini | 1 | 5K | 2K | 5K | 2K |
| Gap analysis | gpt-5-mini | 20 | 4K | 1.5K | 80K | 30K |
| Module generation | gpt-5 | 20 | 12K | 4K | 240K | 80K |
| PPT structuring | gpt-5-mini | 1 | 44K | 8K | 44K | 8K |
| Video scripts | gpt-5-mini | 5 | 44K | 1K | 220K | 5K |
| **Totals** | | | | | **653K** | **129K** |

**Premium tokens**: 240K input + 80K output = **320K** (exceeds 250K daily limit)
**Mini tokens**: 413K input + 49K output = **462K**

### After Optimization

| Task | Model | Calls | Input/Call | Output/Call | Total Input | Total Output |
|------|-------|-------|-----------|-------------|-------------|--------------|
| File summarization | gpt-5-nano | 8 | 8K | 500 | 64K | 4K |
| Topic extraction | gpt-5-nano | 1 | 5K | 2K | 5K | 2K |
| Gap analysis | gpt-5-mini | 20 | 4K | 1.5K | 80K | 30K |
| Module gen (4 critical) | gpt-5.1 | 4 | 12K | 4K | 48K | 16K |
| Module gen (16 mod/minor) | gpt-5-mini | 16 | 12K | 4K | 192K | 64K |
| PPT per-topic slides | gpt-5-mini | 20 | 3K | 1K | 60K | 20K |
| PPT executive summary | gpt-5-nano | 1 | 2K | 1K | 2K | 1K |
| Video scripts | gpt-5.1 | 5 | 6K | 1K | 30K | 5K |
| **Totals** | | | | | **481K** | **142K** |

**Premium tokens**: 78K input + 21K output = **99K** (well within 250K daily limit)
**Mini tokens**: 332K input + 114K output = **446K**
**Nano tokens**: 71K input + 7K output = **78K**

### Savings Summary

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Premium tokens/run | 320K | 99K | **69% reduction** |
| Script input tokens | 220K | 30K | **86% reduction** (filtered context) |
| Daily premium runs possible | <1 | 2-3 | **2.5x throughput** |
| Estimated cost/run | ~$4.50 | ~$2.10 | **53% cost reduction** |

### Key Optimizations Driving Savings

1. **Filtered context for scripts** (-190K premium input): Each script now receives only its own topic's module (~1.5K) instead of all modules (~44K).
2. **Severity-based routing** (-192K premium input, -64K premium output): 80% of modules use mini instead of premium.
3. **Split PPT structuring** (quality improvement): Per-topic calls produce better-focused slide data than one monolithic call.
4. **Nano for extraction** (budget category shift): Summarization and extraction moved from mini to nano tier.

---

## Cost Comparison (Per Run, 20 Topics)

| Component | Before (Model / Cost) | After (Model / Cost) |
|-----------|----------------------|---------------------|
| Summarization | gpt-5-mini / $0.02 | gpt-5-nano / $0.005 |
| Topic extraction | gpt-5-mini / $0.005 | gpt-5-nano / $0.001 |
| Gap analysis | gpt-5-mini / $0.08 | gpt-5-mini / $0.08 |
| Module generation | gpt-5 / $1.04 | gpt-5.1 (4) + gpt-5-mini (16) / $0.34 |
| PPT structuring | gpt-5-mini / $0.03 | gpt-5-mini (20) + gpt-5-nano (1) / $0.06 |
| Video scripts | gpt-5-mini / $0.07 | gpt-5.1 / $0.09 |
| **Total** | | **~$4.50 → ~$2.10** |

Note: Exact costs vary with actual token counts, prompt caching effectiveness, and severity distribution across topics.
