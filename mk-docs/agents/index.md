# Pipeline Agents

CR8's pipeline consists of three specialized agents, each responsible for a distinct phase of the learning guide generation process. All agents run sequentially via LangGraph, sharing state through a `PipelineState` TypedDict.

```mermaid
sequenceDiagram
    participant CLI as CLI / Web UI
    participant LG as LangGraph
    participant A1 as Agent 1: Ingest
    participant A2 as Agent 2: Research
    participant A3 as Agent 3: Generate
    participant CDB as ChromaDB
    participant OAI as OpenAI API
    participant TAV as Tavily API

    CLI->>LG: run_pipeline(files)
    LG->>A1: ingest_node(state)
    A1->>OAI: Summarize files (nano)
    A1->>OAI: Extract topics (nano)
    A1->>CDB: Embed curriculum chunks
    A1-->>LG: topics, raw_text, curriculum_scope

    LG->>A2: research_node(state)
    loop For each topic (parallel)
        A2->>TAV: Web search (jobs + trends)
        A2->>CDB: Query curriculum
        A2->>OAI: Gap analysis (mini)
        A2->>CDB: Embed research
    end
    A2-->>LG: gap_summary

    LG->>A3: generate_node(state)
    loop For each topic (parallel)
        A3->>CDB: Query cached results
        A3->>OAI: Generate module (severity-routed)
    end
    A3->>A3: Compile PDF + PPT + Scripts
    A3-->>LG: pdf_path, ppt_path, video_dir
```

- **[Agent 1: Ingest](ingest.md)** -- Parse files, extract topics, build vector knowledge base
- **[Agent 2: Research](research.md)** -- Web search, gap analysis, store enrichments
- **[Agent 3: Generate](generate.md)** -- Generate modules, compile PDF/PPT/scripts/videos
- **[Prompt Templates](prompts.md)** -- All prompt templates documented
