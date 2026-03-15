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

Failed modules are retried up to `_MAX_MODULE_RETRIES` times (currently 2). After all retries are exhausted the best-effort response — the last LLM output regardless of validation result — is used so the pipeline continues rather than raising an error.

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

## Internal Structure

### Context Classes

The refactored agent uses two context classes to pass shared state between helpers without exceeding the 5-argument function limit (PLR0913).

**`_GenerateCtx`** — shared context for the entire generate phase. Populated by `_init_generate_ctx` and mutated by helpers.

| Field | Set by | Description |
|-------|--------|-------------|
| `topics` | `_init_generate_ctx` | Topic list from pipeline state |
| `curriculum_scope` | `_init_generate_ctx` | Top-level curriculum description |
| `gap_summary` | `_init_generate_ctx` | Full gap analysis list from Research Agent |
| `gap_lookup` | `_init_generate_ctx` | `{topic_name: gap_dict}` index for fast lookups |
| `chroma_cache` | `_init_generate_ctx` | Pre-queried ChromaDB results keyed by topic name |
| `llm_premium` | `_init_generate_ctx` | LLM instance for critical-severity topics |
| `llm_mini` | `_init_generate_ctx` | LLM instance for moderate/minor topics |
| `formats` | `_init_generate_ctx` | Requested output format list |
| `timestamp` | `_init_generate_ctx` | Run timestamp string (`YYYYMMDD_HHMMSS`) |
| `modules_md` | `_generate_all_modules` | Generated markdown per topic |
| `topic_modules_map` | `_generate_all_modules` | `{topic_name: module_md}` for script generation |
| `slide_data` | `_build_pdf_and_ppt` | Structured PPT JSON (or `None` if PPT skipped) |
| `ppt_path` | `_build_pdf_and_ppt` | Path to generated PPTX file |
| `topic_slide_map` | `_build_pdf_and_ppt` | `{topic_name: [slide_indices]}` |

**`_ScriptCtx`** — script generation context, wraps `_GenerateCtx` with per-run script state.

| Field | Description |
|-------|-------------|
| `gen` | The parent `_GenerateCtx` instance |
| `llm_script` | LLM instance for script generation (premium, temperature 0.55) |
| `used_hooks` | Shared list of hook types used so far (thread-safe append via `hooks_lock`) |
| `hooks_lock` | `threading.Lock` protecting `used_hooks` |

### Extracted Helpers from `generate_node`

`generate_node` was reduced from ~115 statements to ~10 by extracting 12 focused helpers:

| Helper | Purpose |
|--------|---------|
| `_init_generate_ctx` | Build `_GenerateCtx` from pipeline state; queries ChromaDB, gets LLMs |
| `_generate_all_modules` | Parallel module generation via `ThreadPoolExecutor`; writes to `ctx.modules_md` |
| `_build_pdf_and_ppt` | Route to PDF-only, PPT-only, or parallel PDF+PPT based on requested formats |
| `_build_pdf_ppt_parallel` | Run `build_pdf` and `_structure_slides_parallel` concurrently |
| `_build_pdf_only` | Build PDF output only |
| `_build_ppt_only` | Structure and build PPT output only |
| `_handle_scripts_videos` | Entry point for script/video generation; selects PPT-aligned or fallback path |
| `_handle_ppt_aligned_path` | Generate PPT-aligned scripts then optionally render videos |
| `_handle_fallback_path` | Generate per-module scripts then optionally render videos |
| `_render_videos` | Export slide images and call `_build_videos_dispatch` |
| `_save_raw_outputs` | Write `_raw_outputs.json` sidecar for the eval framework |
| `_merge_slide_data` | Embed PPT JSON into the raw outputs dict |

Additionally, two helpers were extracted from previously large functions:

| Helper | Extracted from | Purpose |
|--------|---------------|---------|
| `_invoke_with_retry` | `_generate_module` | LLM invocation loop with validation and best-effort fallback |
| `_collect_slide_sources` | `_get_slide_images` | Collect candidate slide source files in priority order |

### Logging

All `print()` calls have been replaced with `logger.info()` / `logger.warning()` using lazy `%s` formatting. The module creates its logger at the top level:

```python
logger = logging.getLogger(__name__)
```

---

## Video Dispatch

The `_VideoJobInputs` dataclass groups the six arguments needed for video dispatch (avoids exceeding the 5-argument function limit):

| Field | Type | Description |
|-------|------|-------------|
| `video_topics` | `list[dict]` | Topics to render (up to `VIDEO_TOPIC_LIMIT`) |
| `scripts` | `list[str]` | One script per topic |
| `video_dir` | `str` | Output directory for MP4s |
| `slide_images` | `list[str]` | Pre-exported slide PNG paths (may be empty) |
| `topic_slide_map` | `dict \| None` | Maps topic names to 0-based slide indices |
| `ppt_path` | `str \| None` | Path to generated PPTX (used for remote export when local LibreOffice is absent) |

### Slide Export and LibreOffice Fallback

`_get_slide_images()` exports the PPTX to PNGs for local video composition. On Cloud Run, the CPU pipeline container does not include LibreOffice. When `export_slides_as_images()` raises `FileNotFoundError`, the function returns an empty list and logs a warning. The remote GPU or CPU-video worker (both include `libreoffice-impress`) performs the conversion after downloading the PPTX from GCS.

```
_get_slide_images(state, video_dir, ppt_path=ppt_path)
  ├── LibreOffice present → export_slides_as_images() → list of PNGs
  └── FileNotFoundError  → logger.warning(...)        → []  (deferred to remote worker)
```

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
