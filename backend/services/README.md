# backend/services/

External API wrappers and output builders. One file per integration.

**Rule**: All external API calls live here only. Agents and routes never call external APIs directly.

## Service Catalog

| File | Integration | Purpose |
|------|-------------|---------|
| `llm.py` | OpenAI | Chat completions with model routing (nano/mini/model/premium) |
| `chromadb_store.py` | ChromaDB | Vector store: store and query curriculum context embeddings |
| `web_search.py` | Tavily API | Web search for industry context and recent research |
| `file_parser.py` | PyMuPDF + python-pptx | Extract text and structure from PDF and PPTX uploads |
| `pdf_builder.py` | fpdf2 | Generate learning guide PDF output |
| `ppt_builder.py` | python-pptx | Generate presentation PPT output |
| `video_builder.py` | HeyGen REST API | Generate AI avatar video output |

## Adding a New Service

1. Create `backend/services/[name].py`
2. Create `backend/prompts/[name].py` if prompts are needed
3. Add corresponding test in `backend/tests/test_[name].py`
4. Create research note at `docs/research/[library].md` before implementing
5. All external calls in the new service must be mockable — add pytest fixtures

## Environment Variables

All API keys and config come from `backend/config.py` (Pydantic Settings):
- `OPENAI_API_KEY` — required
- `TAVILY_API_KEY` — required for research agent
- `HEYGEN_API_KEY` + `HEYGEN_AVATAR_ID` + `HEYGEN_VOICE_ID` — required for video output
- `CHROMA_PERSIST_DIR` — ChromaDB storage path (default: `./chroma_db`)
