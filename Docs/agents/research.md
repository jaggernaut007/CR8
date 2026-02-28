# Agent 2: Research

**File**: `backend/pipeline/agent_research.py`

For each topic, researches current industry requirements and identifies curriculum gaps.

All topics are processed in parallel using `ThreadPoolExecutor`.

## Process

Per topic, concurrently:

1. **Web search** -- Two Tavily searches run in parallel:
   - `"{key_techniques} skills applications in {domain_context} 2025 2026"` (5 results)
   - `"{topic} latest developments alternatives in {domain_context} 2025 2026"` (5 results)
2. **Curriculum retrieval** -- Top 3 matching chunks from ChromaDB `curriculum` collection
3. **Gap analysis** -- GPT-5-mini compares curriculum content against industry findings (JSON mode), scoped to the `curriculum_scope` domain, producing gaps and enrichments
4. **Store enrichments** -- All search results and enrichments are embedded into ChromaDB `research` collection (deduplicated by MD5 hash)

## Console Output

```
[Research] Starting...
[Research] Topic 1/15: Word2Vec Embeddings
[Research]   Found 4 gaps
[Research] Topic 2/15: GloVe and Global Methods
[Research]   Found 3 gaps
...
[Research] Completed -- 15 topics analyzed
```

## State Updates

| Field | Value |
|-------|-------|
| `gap_summary` | List of gap analysis dicts (one per topic) |
| `current_stage` | `"researched"` |

## Key Configuration

| Setting | Value | Notes |
|---------|-------|-------|
| Search results per query | 5 | Two queries per topic (jobs + trends) |
| Curriculum retrieval | Top 3 chunks | From ChromaDB `curriculum` collection |
| Model | GPT-5-mini | Temperature 0.3, JSON mode |
| Deduplication | MD5 hash | Prevents duplicate embeddings in `research` collection |
| Concurrency | `ThreadPoolExecutor` | Controlled by `MAX_WORKERS` (default 8) |
| Severity levels | critical / moderate / minor | Drives model routing in Agent 3 |
