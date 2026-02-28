# Services

The services layer provides reusable abstractions over external APIs and file generation. Each service is a standalone module in `backend/services/`.

- **[LLM Wrapper](llm.md)** -- Multi-tier OpenAI model access
- **[ChromaDB Store](chromadb.md)** -- Vector database for curriculum and research
- **[File Parser](file-parser.md)** -- PDF and PowerPoint text extraction
- **[Web Search](web-search.md)** -- Tavily web search integration
- **[PDF Builder](pdf-builder.md)** -- Learning guide PDF generation
- **[PPT Builder](ppt-builder.md)** -- Gap analysis PowerPoint generation
- **[Video Builder](video-builder.md)** -- HeyGen AI avatar video generation
