# Services

The services layer provides reusable abstractions over external APIs and file generation. Each service is a standalone module in `backend/services/`.

- **[LLM Wrapper](llm.md)** -- Multi-tier OpenAI model access
- **[ChromaDB Store](chromadb.md)** -- Vector database for curriculum and research
- **[File Parser](file-parser.md)** -- PDF and PowerPoint text extraction
- **[Web Search](web-search.md)** -- Tavily web search integration
- **[PDF Builder](pdf-builder.md)** -- Learning guide PDF generation
- **[PPT Builder](ppt-builder.md)** -- Gap analysis PowerPoint generation
- **[Video Builder](video-builder.md)** -- Kokoro TTS + ffmpeg local video pipeline; GPU service offload
- **[TTS Engine](tts-engine.md)** -- Kokoro TTS wrapper with GPU-aware device selection
- **[Script Parser](script-parser.md)** -- `[SLIDE N]` marker parsing for video scripts
- **[GPU Utils](gpu-utils.md)** -- Hardware detection for PyTorch devices and ffmpeg encoders
- **[GCS Client](gcs-client.md)** -- Google Cloud Storage client for CPU↔GPU video data transfer
- **[GPU Client](gpu-client.md)** -- HTTP client for the Cloud Run GPU video service
