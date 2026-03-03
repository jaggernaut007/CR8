# Configuration

All configuration is managed through environment variables, loaded by `backend/config.py` using [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/). Variables are read from a `.env` file in the project root.

## Setting Up `.env`

Copy the example file and fill in your API keys:

```bash
cp .env.example .env
```

Then edit `.env` with your keys:

```
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
```

At minimum, you need `OPENAI_API_KEY` and `TAVILY_API_KEY` to run the pipeline. All other variables have sensible defaults.

## Full `.env.example`

```bash
# OpenAI — model tiers (premium tier: 250K tokens/day combined)
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-5.1
OPENAI_MODEL_PREMIUM=gpt-5.1
OPENAI_MODEL_MINI=gpt-5-mini
OPENAI_MODEL_NANO=gpt-5-nano

# Temperature presets (per-task)
TEMP_ANALYSIS=0.2
TEMP_STRUCTURED=0.3
TEMP_CREATIVE=0.55

# Tavily (web search)
TAVILY_API_KEY=your-tavily-api-key

# ChromaDB
CHROMA_PERSIST_DIR=./chroma_db

# Video provider — "heygen" or "synthesia"
VIDEO_PROVIDER=heygen
VIDEO_MAX_WORKERS=4
VIDEO_AVATAR_EMOTION=Friendly
VIDEO_AVATAR_SPEED=1.05
VIDEO_TOPIC_LIMIT=5

# HeyGen — optional, only needed for --format video/both
HEYGEN_API_KEY=your-heygen-api-key
HEYGEN_AVATAR_ID=
HEYGEN_VOICE_ID=

# Synthesia — alternative video provider (scaffold only)
SYNTHESIA_API_KEY=
SYNTHESIA_AVATAR_ID=

# Output formats — comma-separated: pdf, script, video
OUTPUT_FORMATS=pdf
MAX_WORKERS=8

# LangSmith
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=cr8-prototype

# DeepSeek (eval judge) — only needed for running evals
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

## Configuration Reference

### OpenAI

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | -- | OpenAI API key |
| `OPENAI_MODEL` | No | `gpt-5.1` | Backward-compat alias (maps to premium) |
| `OPENAI_MODEL_PREMIUM` | No | `gpt-5.1` | Premium model for critical modules and scripts |
| `OPENAI_MODEL_MINI` | No | `gpt-5-mini` | Mini model for analysis and structured output |
| `OPENAI_MODEL_NANO` | No | `gpt-5-nano` | Nano model for summarization and extraction |

The pipeline uses a tiered model strategy: nano for cheap extraction tasks, mini for analysis and structured output, and premium for high-quality generation of critical content.

### Temperature

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TEMP_ANALYSIS` | No | `0.2` | Temperature for analysis and summarization tasks |
| `TEMP_STRUCTURED` | No | `0.3` | Temperature for structured output and generation |
| `TEMP_CREATIVE` | No | `0.55` | Temperature for creative writing (scripts) |

Lower temperatures produce more deterministic output. The creative temperature is higher to allow more varied and engaging script writing.

### Tavily

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TAVILY_API_KEY` | Yes | -- | Tavily web search API key |

Used by the Research agent to find current industry trends and job requirements for gap analysis.

### ChromaDB

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CHROMA_PERSIST_DIR` | No | `./chroma_db` | ChromaDB storage directory |

The vector database persists at this path between runs. Run `make clean` to wipe it if you encounter version mismatch errors.

### Video

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `VIDEO_PROVIDER` | No | `heygen` | Video provider: `heygen` or `synthesia` |
| `VIDEO_MAX_WORKERS` | No | `4` | Thread pool size for parallel video generation |
| `VIDEO_AVATAR_EMOTION` | No | `Friendly` | Avatar facial expression |
| `VIDEO_AVATAR_SPEED` | No | `1.05` | Avatar speech rate multiplier |
| `VIDEO_TOPIC_LIMIT` | No | `5` | Max topics to generate scripts/videos for |
| `HEYGEN_API_KEY` | No | -- | HeyGen API key (required for video generation) |
| `HEYGEN_AVATAR_ID` | No | -- | HeyGen avatar ID |
| `HEYGEN_VOICE_ID` | No | -- | HeyGen voice ID |
| `SYNTHESIA_API_KEY` | No | -- | Synthesia API key (alternative video provider, scaffold only) |
| `SYNTHESIA_AVATAR_ID` | No | -- | Synthesia avatar ID |

Video generation is optional. HeyGen keys are only needed when using `--format video` or `--format both`.

### Output

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OUTPUT_FORMATS` | No | `pdf` | Comma-separated output formats: `pdf`, `script`, `video` |
| `MAX_WORKERS` | No | `8` | Thread pool size for parallel agent execution |

`MAX_WORKERS` controls how many topics are processed concurrently across all pipeline agents. Increase for faster runs if your machine and API rate limits allow it.

### LangSmith

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LANGCHAIN_TRACING_V2` | No | `true` | Enable LangSmith tracing |
| `LANGCHAIN_PROJECT` | No | `cr8-prototype` | LangSmith project name |

To view traces, visit [smith.langchain.com](https://smith.langchain.com/) and look for the `cr8-prototype` project. Every LLM call is tagged with a descriptive `run_name` (e.g., `summarize_lecture.pdf`, `gap_analysis_Word2Vec`, `generate_Transformers`).

### DeepSeek

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DEEPSEEK_API_KEY` | No | -- | DeepSeek API key (for eval judge) |
| `DEEPSEEK_BASE_URL` | No | `https://api.deepseek.com` | DeepSeek API base URL |

Only needed if you plan to run the L2 LLM judge in the [evaluation framework](../evals/index.md). Not required for normal pipeline operation.
