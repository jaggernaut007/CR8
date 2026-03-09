# ADR-005: Kokoro TTS Open-Source Video Pipeline

**Date:** 2026-03-01
**Status:** Accepted
**Deciders:** Shreyas Jagannath

---

## Context

CR8 generates narrated slide videos as one of its four output formats (PDF, PPT, Script, Video).
Each pipeline run produces one video per topic: a slide deck converted to images, overlaid with
spoken narration synthesized from a generated script.

The video pipeline must meet these constraints:

- **Cost at scale**: CR8 is an edtech tool — per-minute API fees compound across hundreds of runs.
- **Data privacy**: Curriculum PDFs and generated content should not leave CR8 infrastructure.
- **Latency tolerance**: Video is the slowest format. Users already expect minutes, not seconds.
- **No avatar requirement**: CR8 videos are narrated slide walkthroughs, not talking-head presentations.
- **Hardware flexibility**: Must run on developer Macs (MPS), Cloud Run with NVIDIA L4 (CUDA), and CPU-only containers.

Commercial avatar APIs (HeyGen, Synthesia) were evaluated during v0.3 prototyping but rejected
due to per-video cost, data exfiltration, and features (avatar lip-sync) that CR8 does not need.

## Decision

> We will use Kokoro TTS (open-source, 82M parameters) with a two-phase local pipeline
> (sequential TTS, parallel ffmpeg) for video generation because it eliminates per-video cost,
> keeps curriculum data on-infrastructure, and avoids vendor lock-in.

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **Kokoro TTS + ffmpeg (chosen)** | Zero marginal cost; 82M param model loads in seconds; data never leaves server; no vendor lock-in; GPU-accelerated on CUDA and MPS | ~3.4 GB peak RAM; no avatar/lip-sync; requires `espeak-ng` system dep; ~34 min for 33 slides on Mac MPS |
| HeyGen API | Professional avatar with lip-sync; polished output; no local GPU needed | $0.10-0.50/min per video; curriculum data sent to third party; polling latency; rate limits; vendor lock-in |
| Synthesia API | Enterprise-grade avatars; SOC2 compliant | ~$30/video (enterprise pricing); data leaves infrastructure; no self-hosted option; API availability risk |
| Google Cloud TTS + ffmpeg | High voice quality; within GCP ecosystem (already on Cloud Run); predictable pricing ($4-16/1M chars) | Per-character cost; data sent to Google; still needs local ffmpeg composition; no avatar |
| OpenAI TTS + ffmpeg | Good voice quality; already using OpenAI for LLM; simple API | $15/1M chars; data sent to OpenAI; adds to existing OpenAI spend; still needs local ffmpeg composition |

## Consequences

**Positive:**
- Zero marginal cost per video — cost is only compute time on Cloud Run
- Curriculum data never leaves CR8 infrastructure (PDF content, scripts, audio all local)
- No API key management, rate limits, or vendor SLA dependency for video generation
- Hardware acceleration works on both developer machines (MPS) and production (CUDA)
- Two-phase design maximizes throughput: TTS is memory-bound (sequential), ffmpeg is CPU-bound (parallel)

**Negative / Trade-offs:**
- No avatar or lip-sync — videos are narrated slide decks only
- 3.4 GB peak RAM requires 4+ GiB Cloud Run instances (or GPU service offload)
- Kokoro voice quality is good but not state-of-the-art compared to commercial TTS
- `espeak-ng` system dependency must be installed in Docker images
- MoviePy v2 has a pix_fmt bug requiring a runtime monkey-patch (`yuva420p` to `yuv420p`)

**Neutral:**
- Video generation time (~34 min for 33 slides) is comparable to commercial API round-trips with polling
- The `provider` parameter in `build_videos()` preserves the option to add commercial providers later
- HeyGen and Synthesia client stubs remain in `video_builder.py` as scaffolding for future use

## Implementation Notes

- **Files affected:**
  - `backend/services/tts_engine.py` — `TTSEngine` class wrapping Kokoro `KPipeline`
  - `backend/services/video_builder.py` — `build_videos()` entry point, two-phase `_build_kokoro_videos()`
  - `backend/services/gpu_utils.py` — `get_torch_device()` and `get_ffmpeg_encoder()` detection
  - `backend/services/script_parser.py` — Parses `[SLIDE N]` markers into segments for TTS
  - `backend/config.py` — `kokoro_voice`, `kokoro_lang`, `video_device`, `video_max_workers`
  - `pyproject.toml` — `kokoro>=0.9`, `moviepy>=2.0`, `soundfile>=0.12`
  - `Dockerfile` / `Dockerfile.gpu` — `espeak-ng` system package

- **Patterns to follow:**
  - Lazy model loading: `TTSEngine._get_pipeline()` defers 250 MB model load until first use
  - Two-phase execution: Phase 1 sequential TTS (shared engine, memory-bound) then Phase 2 parallel ffmpeg (thread pool, CPU-bound)
  - Hardware fallback: if hardware encoder fails, `_compose_video` retries with `libx264`
  - Thread distribution: `cpu_count // max_workers` threads per ffmpeg worker to prevent over-subscription

- **Things to avoid:**
  - Do not run TTS in parallel — single `KPipeline` instance, 3.4 GB peak RAM, not thread-safe
  - Do not use MoviePy's default pix_fmt without the `_patch_moviepy_pix_fmt()` workaround
  - Do not hardcode encoder names — always use `get_ffmpeg_encoder()` for portability
  - Do not send curriculum content to external TTS APIs without an explicit ADR superseding this one

## References

- `docs/research/kokoro-tts.md` — Kokoro API research note
- [Kokoro GitHub](https://github.com/hexgrad/kokoro) — 82M parameter open-source TTS
- `backend/services/gpu_utils.py` — hardware detection implementation
- `gpu_service/` — Cloud Run GPU service for offloading video generation
- E2E benchmark data in `PROGRESS.md` (M&A PDF, 33 slides, ~34 min total)
