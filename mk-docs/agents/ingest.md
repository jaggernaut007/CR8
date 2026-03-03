# Agent 1: Ingest

**File**: `backend/pipeline/agent_ingest.py`

Parses curriculum files, identifies topics, and builds the vector knowledge base.

## Process

1. **Parse files** -- Extract text page-by-page using PyMuPDF (`.pdf`) or python-pptx (`.pptx`)
2. **Summarize** -- Each file is summarized by GPT-5-nano in parallel. Files >15K characters use map-reduce: split into 12K-char chunks, each summarized independently, then combined into one summary. Short files use direct summarization.
3. **Extract topics** -- Combined summaries are analyzed by GPT-5-nano (JSON mode) to produce 10-25 topics, each with a name, description, key techniques, and domain context. Also extracts a one-sentence `curriculum_scope` that constrains all downstream agents.
4. **Chunk and embed** -- Raw text is split into 1,500-character chunks (150 overlap) using `RecursiveCharacterTextSplitter`, then embedded into ChromaDB's `curriculum` collection.

## Console Output

```
[Ingest] Starting...
[Ingest] Parsed 01_Word_Vectors_I.pdf -- 73 pages
[Ingest] Summarized 01_Word_Vectors_I.pdf
[Ingest] Extracted 15 topics
[Ingest] Embedded 48 chunks into ChromaDB
```

## State Updates

| Field | Value |
|-------|-------|
| `topics` | List of 10-25 topic dicts |
| `raw_text` | Concatenated extracted text |
| `curriculum_scope` | One-sentence domain boundary |
| `current_stage` | `"ingested"` |

## Key Configuration

| Setting | Value | Notes |
|---------|-------|-------|
| Map-reduce threshold | 15,000 chars | Files above this are chunked |
| Chunk size | 12,000 chars | Per-chunk for map-reduce |
| Embedding chunk size | 1,500 chars | For ChromaDB |
| Embedding overlap | 150 chars | RecursiveCharacterTextSplitter |
| Model | GPT-5-nano | Temperature 0.2 |
