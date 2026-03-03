# Agent 3: Generate

**File**: `backend/pipeline/agent_generate.py`

Generates full learning modules and compiles the final PDF, PPT, scripts, and videos. All modules are generated in parallel.

## Process

Per topic, concurrently:

1. **Cache ChromaDB results** -- All topics' curriculum and research chunks are queried once and cached for reuse across module generation and script generation
2. **Get gap analysis** -- Looks up the gap summary for this topic, including severity (critical/moderate/minor)
3. **Generate module** -- Severity-based model routing: critical topics use GPT-5.1 (premium), moderate/minor use GPT-5-mini. Each module is validated for required sections and minimum length, with up to 2 retries on failure
4. **Compile PDF + PPT** -- PDF and PPT structuring run in parallel. PPT uses per-topic LLM calls (mini) + executive summary (nano) instead of one monolithic call
5. **Generate scripts** -- Each script receives only its own topic's module and gap data (filtered context), saving ~86% on input tokens. Hook variety is enforced across scripts

## Module Generation

### Severity-Based Model Routing

| Severity | Model | Rationale |
|----------|-------|-----------|
| `critical` | GPT-5.1 (premium) | Highest quality for most important gaps |
| `moderate` | GPT-5-mini | Good quality at lower cost |
| `minor` | GPT-5-mini | Good quality at lower cost |

### Validation and Retries

Generated modules are checked for:
- **Required sections**: `## Module Overview`, `## Learning Objectives`, `## Core Content`, `## Key Takeaways`
- **Minimum length**: 2,000 characters

Failed modules are retried up to 2 times before the pipeline raises an error.

## PDF Compilation

### Output Structure

1. **Cover page** -- Title, generation date, topic count
2. **Table of contents** -- Linked chapter listing
3. **Chapters** (one per topic), each containing:
   - Chapter title and description
   - Curriculum Coverage (what the original slides teach)
   - Identified Gaps (what's missing vs. industry demands)
   - Learning Objectives (tagged as Curriculum or Gap)
   - Core Content
   - Industry Context
   - Key Takeaways (grouped: Curriculum, Gap, Integration)
   - Further Reading

## PPT Compilation

PPT structuring runs in parallel with PDF generation:
- **Per-topic slides**: GPT-5-mini generates structured JSON for each topic independently
- **Executive summary**: GPT-5-nano aggregates gap analysis statistics
- **Build step**: `ppt_builder.build_gap_ppt()` renders all slides from the structured JSON

## Script Generation

- Each script receives **filtered context** -- only its own topic's module and gap data, not all topics
- This saves ~86% on input tokens compared to passing all module content
- **Hook variety** is enforced via a thread-safe tracker that prevents consecutive scripts from using the same hook type (question, statistic, analogy, myth-buster, etc.)
- Scripts are generated using GPT-5.1 at temperature 0.55 for creative writing

## Console Output

```
[Generate] Starting...
[Generate] Module 1/15: Word2Vec Embeddings
[Generate]   Done -- 3847 chars
...
[Generate] PDF written to outputs/20260218_235751_learning_guide.pdf
```

## State Updates

| Field | Value |
|-------|-------|
| `pdf_path` | Path to output PDF |
| `ppt_path` | Path to output PPT (if PPT format selected) |
| `video_dir` | Path to video output directory (if video format selected) |
| `current_stage` | `"complete"` |

## Key Configuration

| Setting | Value | Notes |
|---------|-------|-------|
| Premium model | GPT-5.1 | For critical topics and scripts |
| Standard model | GPT-5-mini | For moderate/minor topics |
| Generation temperature | 0.3 | Module generation |
| Script temperature | 0.55 | Creative writing |
| Max retries | 2 | On module validation failure |
| Min module length | 2,000 chars | Validation threshold |
| Concurrency | `ThreadPoolExecutor` | Controlled by `MAX_WORKERS` (default 8) |
