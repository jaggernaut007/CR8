# Research: MoviePy v2

**Date researched:** 2026-03-03
**Library version:** moviepy>=2.0
**Researched by:** Claude Agent (research-assistant)
**Status:** Current

---

## Question Being Answered

> How do we compose slide images + audio into MP4 videos using MoviePy v2 in CR8?

## Sources Consulted

| Source | URL | Date accessed |
|--------|-----|---------------|
| Official docs | https://zulko.github.io/moviepy/ | 2026-03-03 |
| PyPI | https://pypi.org/project/moviepy/ | 2026-03-03 |

## What We Found

### The Correct Approach
```python
# v2 uses flat namespace (NOT moviepy.editor like v1)
from moviepy import AudioFileClip, ImageClip, concatenate_videoclips

audio = AudioFileClip("narration.wav")
clip = ImageClip("slide.png").with_duration(audio.duration).with_audio(audio)
final = concatenate_videoclips([clip], method="compose")
final.write_videofile("output.mp4", fps=24, audio_codec="aac", logger=None)
```

### Key API Methods / Concepts
| Method / Concept | Purpose | Notes / Gotchas |
|-----------------|---------|----------------|
| `ImageClip(path)` | Load static image as clip | **No default duration** — must call `.with_duration()` or write_videofile fails |
| `AudioFileClip(path)` | Load audio from WAV/MP3 | Duration auto-detected from file metadata |
| `.with_duration(seconds)` | Set clip length | Returns NEW clip (v2 clips are immutable). Must assign result. |
| `.with_audio(audio_clip)` | Attach audio track | Audio truncated if longer than video; silent padding if shorter |
| `concatenate_videoclips(clips, method="compose")` | Chain clips sequentially | `"compose"` handles different resolutions; `"chain"` faster for same-size clips |
| `.write_videofile(path, fps, logger)` | Render to MP4 | `logger=None` suppresses ffmpeg spam. Default video codec: mpeg4. Default audio codec: `libmp3lame` (MP3) — **use `audio_codec="aac"` for MP4 containers** for better player compatibility. |

### Configuration Required
```bash
# System dependency (required by MoviePy)
apt-get install ffmpeg

# Python
pip install moviepy>=2.0
```

## What We Ruled Out (and Why)

| Approach | Why Rejected |
|----------|-------------|
| `from moviepy.editor import ...` (v1 style) | Deprecated in v2 — namespace flattened |
| `.set_duration()` method | v1 API; v2 uses `.with_duration()` |
| `CompositeVideoClip` for sequential clips | Verbose; `concatenate_videoclips()` is simpler for our use case |

## Known Gotchas / Edge Cases

- **v2 clips are immutable** — `.with_duration()` returns a NEW clip. `clip.with_duration(5)` without assignment discards the result.
- **ImageClip without duration** — Causes `AttributeError: 'NoneType'` during write. Always chain `.with_duration()`.
- **Audio/video duration mismatch** — Audio longer than video is silently truncated. Match durations via `.with_duration(audio.duration)`.
- **ffmpeg codec errors** — Default video codec is `mpeg4`. If it fails, try `codec="libx264"` (more widely supported).
- **Audio in MP4** — Default audio codec is `libmp3lame` (MP3). MP3-in-MP4 may not play in all players. **Always pass `audio_codec="aac"`** for MP4 output.
- **`logger=None` is critical** — Without it, ffmpeg floods stdout with progress bars, slowing batch processing.

## Decision Made

> Import from flat `moviepy` namespace. Build clips immutably via chaining. Use `concatenate_videoclips(method="compose")` and `write_videofile(fps=24, logger=None)`.

## Files This Affects

- `backend/services/video_builder.py` — `_build_kokoro_video()` uses MoviePy for composition
- `Dockerfile` — `ffmpeg` system dependency

---
*Re-verify if MoviePy releases v3.0 with breaking changes.*
