# Research Index

Implementation research notes for the CR8 pipeline.
Read the relevant note before implementing any feature that uses an external library or API.

## How to Use

1. Check this index for existing notes
2. If a current note exists, read it before implementing
3. If no note exists (or it's outdated), create one:
   - Copy `docs/research/RESEARCH-TEMPLATE.md` → `docs/research/[library].md`
   - Research the official docs for the exact version in `pyproject.toml`
   - Add a row to this index when done

## Research Notes

| Topic | File | Version | Date | Status |
|-------|------|---------|------|--------|
| Code Intelligence & Project Management Tools | [code-intelligence-tools.md](code-intelligence-tools.md) | CodeGrok MCP, code-graph-mcp, GitHub Projects V2, Notion MCP | 2026-03-06 | Current |
| GitLab Knowledge Graph for AI Context | [gitlab-knowledge-graph.md](gitlab-knowledge-graph.md) | GitLab 18.4+ (beta), LadybugDB | 2026-03-06 | Current |
| Kokoro TTS | [kokoro-tts.md](kokoro-tts.md) | >=0.9 | 2026-03-03 | Current |
| MoviePy v2 | [moviepy-v2.md](moviepy-v2.md) | >=2.0 | 2026-03-03 | Current |
| PyMuPDF Slide Export | [pymupdf-slide-export.md](pymupdf-slide-export.md) | >=1.24 | 2026-03-03 | Current |
| Deployment Strategies | [deployment-strategies.md](deployment-strategies.md) | — | 2026-03-04 | Current |
| MCP Dev Tools | [mcp-dev-tools.md](mcp-dev-tools.md) | — | 2026-03-04 | Current |
| MCP Pipeline Integration | [mcp-pipeline-integration.md](mcp-pipeline-integration.md) | MCP Spec 2025-11-25 | 2026-03-04 | Current |
| Agent Lightning (APO/RL) | [agent-lightning.md](agent-lightning.md) | >=0.3.0 | 2026-03-06 | Current |
| pytest Test Optimization | [pytest-tdd-optimization.md](pytest-tdd-optimization.md) | pytest-xdist>=3.5, pytest-randomly>=0.15, pytest-timeout>=2.2 | 2026-03-06 | Current |
| React 19 + Vite 6 + FastAPI Integration | [react-vite-fastapi.md](react-vite-fastapi.md) | React 19.2.4, Vite 6.2.6, React Router 7.13.1, TanStack Query 5.90.21 | 2026-03-09 | Current |
| Tailwind CSS v4 Custom Styles & Glassmorphism | [tailwind-css-v4.md](tailwind-css-v4.md) | tailwindcss >= 4.0.1 | 2026-03-09 | Current |
| shadcn/ui Components & TanStack Query | [shadcn-ui-tanstack-query.md](shadcn-ui-tanstack-query.md) | shadcn/ui (CLI-based), @tanstack/react-query >= 5.90.21 | 2026-03-09 | Current |
| FastAPI File Serving (Range Requests, PDFs, Videos) | [fastapi-file-serving.md](fastapi-file-serving.md) | FastAPI >= 0.115, Starlette (bundled) | 2026-03-09 | Current |
| ChromaDB Vector Storage | [chromadb.md](chromadb.md) | >=0.5 | 2026-03-09 | Current |
| LangGraph Pipeline Orchestration | [langgraph.md](langgraph.md) | >=0.2 | 2026-03-09 | Current |
| OpenAI SDK (via langchain-openai) | [openai-sdk.md](openai-sdk.md) | langchain-openai >=0.3 | 2026-03-09 | Current |
| Tavily Python SDK | [tavily.md](tavily.md) | >=0.5 | 2026-03-09 | Current |
| HeyGen REST API | [heygen-api.md](heygen-api.md) | REST API v2 (rejected in ADR-005) | 2026-03-09 | Current |
| fpdf2 PDF Generation | [fpdf2.md](fpdf2.md) | >=2.8 | 2026-03-09 | Current |
| python-pptx PowerPoint Generation | [python-pptx.md](python-pptx.md) | >=1.0 | 2026-03-09 | Current |
| google-cloud-storage SDK | [google-cloud-storage.md](google-cloud-storage.md) | >=2.14 | 2026-03-09 | Current |

## Priority Research Needed

All priority research has been completed. No gaps remain.

## Notes That Are Outdated

Check this section when a library has a major version bump:
- *(none flagged yet)*
