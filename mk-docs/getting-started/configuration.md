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

# Video provider — "kokoro" (local, zero cost) or "heygen"
VIDEO_PROVIDER=kokoro
VIDEO_MAX_WORKERS=12
VIDEO_DEVICE=auto          # auto | cpu | mps | cuda
VIDEO_AVATAR_EMOTION=Friendly
VIDEO_AVATAR_SPEED=1.05
VIDEO_TOPIC_LIMIT=5
VIDEO_FPS=24

# Kokoro TTS — used when VIDEO_PROVIDER=kokoro
KOKORO_VOICE=af_heart
KOKORO_LANG=a

# HeyGen — only needed when VIDEO_PROVIDER=heygen
HEYGEN_API_KEY=your-heygen-api-key
HEYGEN_AVATAR_ID=
HEYGEN_VOICE_ID=

# Synthesia — alternative video provider (scaffold only)
SYNTHESIA_API_KEY=
SYNTHESIA_AVATAR_ID=

# Video services — 3-tier fallback chain (leave empty to run locally)
GPU_SERVICE_URL=           # Tier 1: GPU primary  (europe-west4, NVIDIA L4)
GPU_FALLBACK_URL=          # Tier 2: GPU fallback (europe-west1, NVIDIA L4)
CPU_VIDEO_SERVICE_URL=     # Tier 3: CPU-only     (europe-west2, 8 vCPU / 32 GiB)
GCS_BUCKET=cr8-jobs        # shared GCS bucket for data transfer

# Output formats — comma-separated: pdf, ppt, script, video
OUTPUT_FORMATS=pdf
MAX_WORKERS=8

# LangSmith — tracing is opt-in (set LANGCHAIN_TRACING_V2=true to enable)
LANGCHAIN_API_KEY=your-langsmith-api-key
LANGCHAIN_TRACING_V2=false
LANGCHAIN_PROJECT=cr8-prototype

# Auth — password for the web UI login (default: CR8-AI)
AUTH_PASSWORD=CR8-AI

# DeepSeek (eval judge) — only needed for running evals
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com

# HuggingFace — speeds up Kokoro model downloads (get token at huggingface.co/settings/tokens)
HF_TOKEN=
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
| `VIDEO_PROVIDER` | No | `heygen` | Video provider: `kokoro`, `heygen`, or `synthesia` |
| `VIDEO_MAX_WORKERS` | No | `12` | Thread pool size for parallel video composition |
| `VIDEO_DEVICE` | No | `auto` | Hardware acceleration: `auto` (detect best GPU), `cpu`, `mps` (Apple), `cuda` (NVIDIA) |
| `VIDEO_FPS` | No | `24` | Output frame rate for Kokoro MP4 files |
| `VIDEO_AVATAR_EMOTION` | No | `Friendly` | HeyGen avatar facial expression |
| `VIDEO_AVATAR_SPEED` | No | `1.05` | HeyGen avatar speech rate multiplier |
| `VIDEO_TOPIC_LIMIT` | No | `5` | Max topics to generate scripts/videos for |

### Video Service (3-Tier Fallback)

Set these variables to offload TTS and video encoding to remote Cloud Run services instead of running locally. The pipeline tries each tier in order on infrastructure failures. When all three URLs are empty, video runs locally using the Kokoro pipeline.

**Tier chain:** GPU Primary (europe-west4) → GPU Fallback (europe-west1) → CPU Video (europe-west2)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GPU_SERVICE_URL` | No | *(empty)* | GPU primary Cloud Run service URL (europe-west4, NVIDIA L4) |
| `GPU_FALLBACK_URL` | No | *(empty)* | GPU fallback Cloud Run service URL (europe-west1, NVIDIA L4) |
| `CPU_VIDEO_SERVICE_URL` | No | *(empty)* | CPU-only video service URL (europe-west2, 8 vCPU / 32 GiB). Tier 3 fallback. |
| `GCS_BUCKET` | No | `cr8-jobs` | GCS bucket used to transfer slide images and completed MP4s. Must be accessible from all services. |

When any video service URL is set:

1. The generate agent uploads slide PNGs and a job manifest to `gs://{GCS_BUCKET}/{job_id}/input/`.
2. It submits the job to the first reachable tier via `POST /api/v1/video-jobs`.
3. It polls for completion, emitting `[Video] GPU:` progress lines.
4. It downloads finished MP4s from `gs://{GCS_BUCKET}/{job_id}/output/`.

Fallback to the next tier is triggered only by infrastructure failures (connection refused, timeout, 5xx response). Job-level errors reported by the service do not trigger fallback.

Identity token authentication is handled automatically on Cloud Run (service-to-service). When running locally, auth tokens are skipped.

!!! tip "GPU service is ~10x faster for video"
    A 5-topic video job takes ~2-3 min on an NVIDIA L4 vs ~20-30 min on the CPU video service. The CPU tier is a reliability fallback, not a performance alternative. Cost: ~$0.06 per job (GPU 3 min) vs ~$0.13 (CPU 20 min on Cloud Run).

### Kokoro TTS

Used when `VIDEO_PROVIDER=kokoro`. Kokoro is an open-source TTS engine with near-commercial quality audio. It supports GPU acceleration (Apple Metal MPS, NVIDIA CUDA) for faster synthesis and falls back to CPU when no GPU is available. Set `VIDEO_DEVICE=auto` (default) to auto-detect, or force a specific device. Requires `espeak-ng` as a system dependency (included in the Dockerfile).

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `KOKORO_VOICE` | No | `af_heart` | Kokoro voice identifier |
| `KOKORO_LANG` | No | `a` | Kokoro language code (`a` = American English) |

!!! warning "System dependencies for Kokoro"
    Kokoro requires `espeak-ng`, `ffmpeg`, and `libreoffice-impress` (for PPTX→PNG slide export) to be installed. These are included in the project `Dockerfile`. For local development: `brew install espeak ffmpeg libreoffice` (macOS) or `apt-get install espeak-ng ffmpeg libreoffice-impress` (Debian/Ubuntu). Kokoro also peaks at approximately 3.4 GB RAM — Cloud Run must be configured with at least 4 GiB memory when running video locally. When any video service URL is set, the main service does not run Kokoro and can stay at 4 GiB.

### HeyGen / Synthesia

| Variable | Required for | Description |
|----------|-------------|-------------|
| `HEYGEN_API_KEY` | HeyGen | HeyGen API key |
| `HEYGEN_AVATAR_ID` | HeyGen | HeyGen avatar ID |
| `HEYGEN_VOICE_ID` | HeyGen | HeyGen voice ID |
| `SYNTHESIA_API_KEY` | Synthesia | Synthesia API key (scaffold only, raises `NotImplementedError`) |
| `SYNTHESIA_AVATAR_ID` | Synthesia | Synthesia avatar ID |

HeyGen keys are only needed when `VIDEO_PROVIDER=heygen`. All three variables must be set — the pipeline validates this at startup if video output is requested. The same validation applies to Synthesia (`SYNTHESIA_API_KEY` and `SYNTHESIA_AVATAR_ID`). Both paths use the shared `_validate_video_provider()` function in `backend/run_pipeline.py`.

### Authentication

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AUTH_PASSWORD` | No | `CR8-AI` | Password for the web UI login form |

The web UI uses bcrypt session authentication. The password is read from `AUTH_PASSWORD` at startup and hashed with bcrypt. For local development the default `CR8-AI` is sufficient. For production deployments, set a strong unique password in your secrets manager.

!!! warning "Change the default password in production"
    The default password `CR8-AI` is publicly documented. Always set `AUTH_PASSWORD` to a strong secret value before deploying to any environment reachable from the internet.

### Output

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OUTPUT_FORMATS` | No | `pdf` | Comma-separated output formats: `pdf`, `ppt`, `script`, `video` |
| `MAX_WORKERS` | No | `8` | Thread pool size for parallel agent execution |

`MAX_WORKERS` controls how many topics are processed concurrently across all pipeline agents. Increase for faster runs if your machine and API rate limits allow it.

### LangSmith

LangSmith tracing is **opt-in**. Tracing is disabled by default and must be explicitly enabled.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LANGCHAIN_API_KEY` | No | -- | LangSmith API key (required when tracing is enabled) |
| `LANGCHAIN_TRACING_V2` | No | `false` | Set to `true` to enable LangSmith tracing |
| `LANGCHAIN_PROJECT` | No | `cr8-prototype` | LangSmith project name |

When enabled, every LLM call is traced with a descriptive `run_name` (e.g., `summarize_lecture.pdf`, `gap_analysis_Word2Vec`, `generate_Transformers`). Pipeline runs include `job_id`, `output_formats`, and `file_count` as top-level metadata. Services decorated with `@traceable` (`tts_engine`, `script_parser`, `export_slides_as_images`) appear as child spans.

To view traces, visit [smith.langchain.com](https://smith.langchain.com/) and look for the `cr8-prototype` project.

### DeepSeek

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DEEPSEEK_API_KEY` | No | -- | DeepSeek API key (for eval judge) |
| `DEEPSEEK_BASE_URL` | No | `https://api.deepseek.com` | DeepSeek API base URL |

Only needed if you plan to run the L2 LLM judge in the [evaluation framework](../evals/index.md). Not required for normal pipeline operation.
