# Research: Kokoro TTS

**Date researched:** 2026-03-03
**Library version:** kokoro>=0.9
**Researched by:** Claude Agent (research-assistant)
**Status:** Current

---

## Question Being Answered

> How do we use Kokoro TTS for local text-to-speech in CR8's video pipeline?

## Sources Consulted

| Source | URL | Date accessed |
|--------|-----|---------------|
| GitHub README | https://github.com/hexgrad/kokoro | 2026-03-03 |
| PyPI | https://pypi.org/project/kokoro/ | 2026-03-03 |

## What We Found

### The Correct Approach
```python
from kokoro import KPipeline
import numpy as np
import soundfile as sf

pipeline = KPipeline(lang_code="a")  # "a" = American English
samples = []
for chunk in pipeline("Hello world", voice="af_heart"):
    samples.append(chunk.audio)  # numpy float32 array
audio = np.concatenate(samples)
sf.write("output.wav", audio, 24000)  # 24 kHz sample rate
```

### Key API Methods / Concepts
| Method / Concept | Purpose | Notes / Gotchas |
|-----------------|---------|----------------|
| `KPipeline(lang_code="a")` | Initialize TTS pipeline | Loads ~250 MB model. Use lazy init to avoid loading when TTS not needed. |
| `pipeline(text, voice="af_heart")` | Generate audio chunks (generator) | Yields objects with `.audio` attribute (numpy float32). Must concatenate all chunks. |
| `chunk.audio` | Raw audio samples | Shape: (num_samples,), dtype: float32, sample rate: 24 kHz |

### Configuration Required
```bash
# System dependency (required — Kokoro uses it internally for text-to-phoneme)
apt-get install espeak-ng

# Python
pip install kokoro soundfile numpy
```

### Voices and Languages
- Default voice: `af_heart` (female, American English)
- Language codes: `"a"` (American English), `"b"` (British English)
- Voice naming: `[lang][gender]_[name]` — e.g., `af_heart`, `bf_emma`

## What We Ruled Out (and Why)

| Approach | Why Rejected |
|----------|-------------|
| Parallel TTS generation | CPU-bound, peaks at ~3.4 GB RAM — TTS runs sequentially with shared engine; only ffmpeg encoding is parallelised |
| Writing individual chunks to file | Must concatenate all chunks first; partial writes produce truncated audio |

## Known Gotchas / Edge Cases

- **espeak-ng is mandatory** — Kokoro calls it internally. Without it, synthesis fails with cryptic errors.
- **Memory: ~3.4 GB peak** — Cloud Run needs 4 GiB minimum.
- **Voice names are case-sensitive** — `"af_heart"` works, `"AF_HEART"` does not.
- **Empty text** — May produce empty chunks or error. Validate input text before calling.
- **lang_code is immutable** — Changing language requires a new KPipeline instance.

## Decision Made

> Use Kokoro with lazy KPipeline initialization, concatenate all audio chunks before writing WAV at 24 kHz. Two-phase pipeline: sequential TTS with shared engine (memory-heavy) → parallel ffmpeg composition (CPU-bound, thread-safe). `preset='fast'` for ~2x encoding speed.

## Files This Affects

- `backend/services/tts_engine.py` — Core TTS wrapper
- `backend/services/video_builder.py` — Calls tts_engine for Kokoro provider
- `backend/config.py` — `kokoro_voice`, `kokoro_lang` settings
- `Dockerfile` — `espeak-ng` system dependency

---
*Re-verify if kokoro has a major version bump past 1.0.*
