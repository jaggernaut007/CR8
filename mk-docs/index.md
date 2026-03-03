# CR8 — Adaptive Learning Pipeline

A 3-agent AI pipeline that transforms university curriculum materials into market-enriched learning guides. Feed in lecture PDFs, get out structured outputs with industry context, gap analysis, and curated resources.

``` mermaid
graph LR
    A[Curriculum PDFs] --> B[Agent 1: Ingest]
    B --> C[Agent 2: Research]
    C --> D[Agent 3: Generate]
    D --> E[Learning Guide PDF]
    D --> F[Gap Analysis PPT]
    D --> G[Video Scripts]
    G --> H[AI Avatar Videos]
    B -.->|embed| DB1[(ChromaDB\ncurriculum)]
    C -.->|embed| DB2[(ChromaDB\nresearch)]
    C -.->|query| DB1
    D -.->|query| DB1
    D -.->|query| DB2
    C -.->|search| T[Tavily API]
```

Built with LangGraph, OpenAI, ChromaDB, Tavily, fpdf2, and FastAPI.

---

## Quick Links

<div class="grid cards" markdown>

-   **[Getting Started](getting-started/index.md)**

    Install and run the pipeline in minutes

-   **[Architecture](architecture/index.md)**

    Pipeline design, data flow, and model routing

-   **[Pipeline Agents](agents/index.md)**

    Deep dive into Ingest, Research, and Generate agents

-   **[Services](services/index.md)**

    LLM wrapper, ChromaDB, PDF/PPT/Video builders

-   **[Evaluation Framework](evals/index.md)**

    Two-layer eval system with structural checks and LLM judge

-   **[Deployment](deployment/index.md)**

    Docker and GCP Cloud Run deployment

-   **[API Reference](api/index.md)**

    Auto-generated API documentation

-   **[Security](security.md)**

    Authentication, upload hardening, and AI pipeline security

-   **[Contributing](contributing/index.md)**

    Development setup, testing, and documentation guide

</div>

---

## Key Features

- **3-agent pipeline** — Ingest → Research → Generate, orchestrated by LangGraph
- **Multi-model routing** — GPT-5-nano (extraction), GPT-5-mini (analysis), GPT-5.1 (generation), with severity-based routing for critical topics
- **Chained outputs** — PDF → PPT → Scripts → Videos, each building on the previous
- **Vector-backed context** — ChromaDB stores curriculum and research for semantic retrieval
- **Web UI** — Upload PDFs, select formats, track progress in real time
- **Evaluation framework** — L1 structural checks (free) + L2 DeepSeek-V3 judge (~$0.02/run) with A/B prompt comparison

## Quick Start

```bash
# Install
python -m venv .venv && source .venv/bin/activate
make install

# Configure
cp .env.example .env  # Add your API keys

# Run
python -m backend.run_pipeline path/to/lecture.pdf
```

Output is saved to `outputs/<timestamp>/`.

See the [full installation guide](getting-started/installation.md) for details.
