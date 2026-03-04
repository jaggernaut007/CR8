# Data Flow & State

## PipelineState

State is a `TypedDict` defined in `backend/pipeline/state.py` that accumulates data as it passes through each agent:

| Field | Set By | Type | Description |
|-------|--------|------|-------------|
| `job_id` | CLI runner | `str` | Random 12-char hex ID |
| `file_paths` | CLI runner | `list[str]` | Input file paths |
| `output_formats` | CLI runner | `str` | Comma-separated formats to generate (e.g. `"pdf,ppt,script"`) |
| `topics` | Agent 1 | `list[dict]` | Topics with name, description, key_techniques, domain_context |
| `raw_text` | Agent 1 | `str` | Concatenated extracted text |
| `curriculum_scope` | Agent 1 | `str` | One-sentence domain boundary description |
| `gap_summary` | Agent 2 | `list[dict]` | Gap analysis per topic (severity, gaps, enrichments) |
| `pdf_path` | Agent 3 | `str` | Path to output PDF |
| `ppt_path` | Agent 3 | `str` | Path to output PPT |
| `video_dir` | Agent 3 | `str` | Path to video output directory |
| `slide_images` | Agent 3 | `NotRequired[list[str]]` | Paths to exported slide PNGs (set when `VIDEO_PROVIDER=kokoro`) |
| `current_stage` | All agents | `str` | `starting` -> `ingested` -> `researched` -> `complete` |

## State Flow

The pipeline starts with an initial state containing only `job_id` and `file_paths`. Each agent reads from existing fields and writes to new ones, accumulating data as it flows through the graph.

### Initial State (set by runner)

```python
initial_state = {
    "job_id": uuid.uuid4().hex[:12],
    "file_paths": file_paths,
    "output_formats": "pdf",
    "topics": [],
    "raw_text": "",
    "curriculum_scope": "",
    "gap_summary": [],
    "pdf_path": "",
    "ppt_path": "",
    "video_dir": "",
    "current_stage": "starting",
}
```

### After Agent 1: Ingest

The ingest agent reads `file_paths`, parses the curriculum files, extracts topics via LLM, and embeds raw text into ChromaDB. It writes:

- `topics` -- A list of 10-25 topic dicts, each with `name`, `description`, `key_techniques` (list of 3-8 specific methods/algorithms), and `domain_context` (broader subject framing).
- `raw_text` -- The full concatenated text extracted from all input files.
- `curriculum_scope` -- A one-sentence description constraining all downstream agents to the curriculum's domain (e.g., "Natural language processing with deep learning, covering neural network methods for text understanding and generation").
- `current_stage` -- Set to `"ingested"`.

ChromaDB's `curriculum` collection is populated with 1,500-character chunks (150 overlap) of the raw text.

### After Agent 2: Research

The research agent reads `topics`, `curriculum_scope`, and queries the `curriculum` ChromaDB collection. For each topic (processed in parallel), it runs two Tavily web searches, retrieves relevant curriculum chunks, and performs gap analysis via LLM. It writes:

- `gap_summary` -- A list of dicts, one per topic, each containing:
  - `topic` -- Topic name
  - `severity` -- `"critical"`, `"moderate"`, or `"minor"`
  - `curriculum_coverage` -- What the curriculum teaches
  - `industry_demands` -- What industry expects
  - `gaps` -- List of identified gaps
  - `enrichments` -- List of enrichment content from web search
- `current_stage` -- Set to `"researched"`.

ChromaDB's `research` collection is populated with web search results and enrichments (deduplicated by MD5 hash).

### After Agent 3: Generate

The generate agent reads `topics`, `gap_summary`, `curriculum_scope`, and queries both ChromaDB collections. For each topic (processed in parallel), it generates a learning module using severity-based model routing. It then compiles outputs and writes:

- `pdf_path` -- Path to the generated learning guide PDF.
- `ppt_path` -- Path to the generated gap analysis PowerPoint (if PPT format selected).
- `video_dir` -- Path to the directory containing video scripts and/or rendered videos (if script/video format selected).
- `current_stage` -- Set to `"complete"`.

## ChromaDB Collections

Two vector collections persist across the pipeline:

| Collection | Populated By | Queried By | Contents |
|-----------|-------------|------------|----------|
| `curriculum` | Agent 1 (Ingest) | Agent 2, Agent 3 | 1,500-char chunks of raw curriculum text |
| `research` | Agent 2 (Research) | Agent 3 | Web search results and enrichment content |

Both use ChromaDB's built-in `all-MiniLM-L6-v2` embeddings (local, free, no API calls). The `research` collection deduplicates entries by MD5 hash to avoid storing the same search result multiple times.

Agent 3 caches all ChromaDB query results upfront for all topics, then reuses the cached results across module generation and script generation. This eliminates redundant vector searches.

## State Diagram

```
                  ┌──────────────────────┐
                  │     Initial State    │
                  │  job_id, file_paths  │
                  │  current_stage:      │
                  │    "starting"        │
                  └──────────┬───────────┘
                             │
                    ┌────────▼────────┐
                    │  Agent 1: Ingest │
                    └────────┬────────┘
                             │
                  ┌──────────▼───────────┐
                  │  + topics            │
                  │  + raw_text          │
                  │  + curriculum_scope  │
                  │  current_stage:      │
                  │    "ingested"        │
                  └──────────┬───────────┘
                             │
                   ┌─────────▼─────────┐
                   │ Agent 2: Research  │
                   └─────────┬─────────┘
                             │
                  ┌──────────▼───────────┐
                  │  + gap_summary       │
                  │  current_stage:      │
                  │    "researched"      │
                  └──────────┬───────────┘
                             │
                   ┌─────────▼─────────┐
                   │ Agent 3: Generate  │
                   └─────────┬─────────┘
                             │
                  ┌──────────▼───────────┐
                  │  + pdf_path          │
                  │  + ppt_path          │
                  │  + video_dir         │
                  │  current_stage:      │
                  │    "complete"        │
                  └──────────────────────┘
```
