# TTS Engine

Kokoro TTS wrapper for local speech synthesis with GPU-aware device selection.

## Module

::: backend.services.tts_engine

## Overview

The TTS engine wraps the [Kokoro](https://github.com/thewh1teagle/kokoro) text-to-speech library. It lazy-loads the `KPipeline` on first use (~250 MB model) and supports MPS (Apple Silicon), CUDA (NVIDIA), or CPU inference.

### Key Features

- **Lazy initialisation** — model loads on first `synthesize()` call, not at import time
- **GPU-aware** — uses `get_torch_device(settings.video_device)` for automatic device selection
- **Path validation** — prevents directory traversal in output paths
- **LangSmith tracing** — `@traceable` decorator for observability

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `KOKORO_VOICE` | `af_heart` | Voice model identifier |
| `KOKORO_LANG` | `a` | Language code |
| `VIDEO_DEVICE` | `auto` | Device selection: `auto`, `cpu`, `mps`, `cuda` |
| `HF_TOKEN` | *(empty)* | HuggingFace token for authenticated model downloads |

## Usage

```python
from backend.services.tts_engine import TTSEngine

engine = TTSEngine(voice="af_heart", lang="a")
engine.synthesize("Hello world", "/tmp/output.wav")

# Batch synthesis for video segments
segments = [{"slide_num": 1, "text": "Introduction..."}, ...]
paths = engine.synthesize_segments(segments, "/tmp/audio/")
```
