# Video Builder

**File**: `backend/services/video_builder.py`

Generates narrated slide videos from PPT/PDF slides and video scripts. Supports two providers: `kokoro` (open-source, local, zero cost) and `heygen` (cloud API with AI avatar). The active provider is selected via the `VIDEO_PROVIDER` environment variable.

## Usage

```python
from backend.services.video_builder import build_videos

video_paths = build_videos(
    scripts=["[SLIDE 1]\nWelcome to...", "[SLIDE 2]\nIn this section..."],
    output_dir="outputs/videos/",
    slide_images=["outputs/slides/slide_01.png", "outputs/slides/slide_02.png"],
)
```

## Provider Dispatch

`build_videos()` inspects `settings.video_provider` and dispatches to the appropriate builder:

| `VIDEO_PROVIDER` | Builder | Description |
|-----------------|---------|-------------|
| `kokoro` | `_build_kokoro_videos()` | Open-source Kokoro TTS + MoviePy composition |
| `heygen` | HeyGen API client | Cloud AI avatar video (requires API keys) |
| `synthesia` | Scaffold only | Raises `NotImplementedError` |

Provider validation (missing API keys for `heygen` and `synthesia`, unknown provider names) is performed by `_validate_video_provider()` in `backend/run_pipeline.py` before the pipeline is invoked. Both the CLI (`main()`) and the web entry point (`run_job()`) use the same validation function.

## GPU Service Dispatch (Remote Video Generation)

When `GPU_SERVICE_URL` is configured, the generate agent routes video work to a remote NVIDIA L4 Cloud Run service instead of running locally. This is handled by `_build_videos_dispatch()` in `backend/pipeline/agent_generate.py`, not by `build_videos()` directly.

```
_build_videos_dispatch()
  ├── GPU_SERVICE_URL set?
  │     YES → GCSVideoClient.upload_job_inputs()   # slide PNGs + manifest → GCS
  │          → GPUVideoClient.submit_job()          # POST /api/v1/video-jobs
  │          → GPUVideoClient.poll_until_complete() # poll status, emit [Video] GPU: lines
  │          → GCSVideoClient.download_videos()     # MP4s ← GCS
  └── NO  → build_videos()                          # local Kokoro pipeline (unchanged)
```

See [GCS Client](../services/gcs-client.md) and [GPU Client](../services/gpu-client.md) for the transfer layer details. See [GCP Cloud Run](../deployment/gcp-cloud-run.md) for the two-service deployment setup.

## Kokoro Provider (`VIDEO_PROVIDER=kokoro`)

The Kokoro path is a fully local, open-source pipeline with zero per-video API cost implemented as a two-phase process:

```
slide PNGs + script segments
  Phase 1 (sequential):
    → Kokoro TTS (tts_engine.py) → WAV audio per segment
  Phase 2 (parallel, VIDEO_MAX_WORKERS threads):
    → MoviePy ImageClip per slide, duration = audio duration
    → Concatenate all clips
    → Write MP4 (H.264 + AAC, 24fps)
```

### `_build_kokoro_videos()`

Builds MP4 files for all topics in two phases. Phase 1 synthesises all audio sequentially using a shared `TTSEngine` instance (the Kokoro model loads once and is reused across topics — peak RAM ~3.4 GB). Phase 2 runs MoviePy composition and ffmpeg encoding in parallel across topics using `ThreadPoolExecutor`.

```python
def _build_kokoro_videos(
    topics: list[dict],
    scripts: list[str],
    output_dir: str,
    slide_images: list[str],
    topic_slide_map: dict[str, list[int]] | None = None,
    voice: str = "af_heart",
    lang: str = "a",
    fps: int = 24,
) -> list[str | None]
```

**Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| `topics` | `list[dict]` | Topic dicts, each with a `"name"` key |
| `scripts` | `list[str]` | Script text per topic, with `[SLIDE N]` markers |
| `output_dir` | `str` | Root directory for video outputs and scripts |
| `slide_images` | `list[str]` | Ordered list of slide PNG file paths |
| `topic_slide_map` | `dict[str, list[int]] \| None` | Maps topic names to 0-based slide indices; if absent, all slides are used for every topic |
| `voice` | `str` | Kokoro voice identifier |
| `lang` | `str` | Kokoro language code |
| `fps` | `int` | Output frame rate |

**Returns**: `list[str | None]` — filesystem paths to `.mp4` files in the same order as `topics`. Failed topics produce `None` at their position; errors are logged with `exc_info=True` and printed as `[Video] ERROR:` lines.

!!! warning "Resource cleanup"
    `_compose_video()` wraps all MoviePy `ImageClip` and `CompositeVideoClip` instances in a `try/finally` block to ensure `clip.close()` is called even when composition fails. This prevents file-handle leaks and releases the ~3.4 GB RAM peak when a video fails mid-encode.

**Output spec**:
- Format: MP4 (H.264 video, AAC audio)
- Resolution: Matches slide image dimensions (typically 1920×1080)
- Frame rate: Configured via `VIDEO_FPS` (default 24)
- Duration: Sum of per-segment audio durations

### Dependencies (lazy imports)

`kokoro`, `moviepy`, and `soundfile` are imported inside the Kokoro functions at call time. They are not installed in the dev/CI environment — they are only loaded when `VIDEO_PROVIDER=kokoro`. The Dockerfile includes all required system packages (`ffmpeg`, `espeak-ng`, `poppler-utils`, `libreoffice-impress`).

## HeyGen Provider (`VIDEO_PROVIDER=heygen`)

Submits scripts to HeyGen API v2 for AI avatar video generation. Supports configurable avatar emotion and speech speed. Polls the API for completion status after submitting each job.

!!! warning "HeyGen keys required"
    HeyGen video generation requires `HEYGEN_API_KEY`, `HEYGEN_AVATAR_ID`, and `HEYGEN_VOICE_ID` to be set. The pipeline validates these via `_validate_video_provider()` before the run starts when `--format video` is requested.

## Configuration

| Setting | Config Variable | Default | Description |
|---------|----------------|---------|-------------|
| Provider | `VIDEO_PROVIDER` | `heygen` | `kokoro`, `heygen`, or `synthesia` |
| Device | `VIDEO_DEVICE` | `auto` | Hardware acceleration: `auto`, `cpu`, `mps`, `cuda` |
| FPS | `VIDEO_FPS` | `24` | Output frame rate for Kokoro MP4 |
| Kokoro voice | `KOKORO_VOICE` | `af_heart` | Kokoro TTS voice identifier |
| Kokoro language | `KOKORO_LANG` | `a` | Kokoro language code (`a`=American English) |
| Emotion | `VIDEO_AVATAR_EMOTION` | `Friendly` | HeyGen avatar facial expression |
| Speed | `VIDEO_AVATAR_SPEED` | `1.05` | HeyGen speech rate multiplier |
| Concurrency | `VIDEO_MAX_WORKERS` | `12` | Parallel video composition workers (Phase 2) |
| Topic limit | `VIDEO_TOPIC_LIMIT` | `5` | Max topics to generate videos for |
| GPU service | `GPU_SERVICE_URL` | *(empty)* | URL of remote GPU service; empty = local |
| GCS bucket | `GCS_BUCKET` | `cr8-jobs` | Shared bucket for CPU↔GPU data transfer |

## Required Environment Variables

| Variable | Required for | Description |
|----------|-------------|-------------|
| `VIDEO_PROVIDER` | All | Select provider (`kokoro` recommended for local use) |
| `KOKORO_VOICE` | Kokoro | TTS voice identifier |
| `KOKORO_LANG` | Kokoro | TTS language code |
| `VIDEO_FPS` | Kokoro | MP4 frame rate |
| `HEYGEN_API_KEY` | HeyGen | HeyGen API key |
| `HEYGEN_AVATAR_ID` | HeyGen | HeyGen avatar ID |
| `HEYGEN_VOICE_ID` | HeyGen | HeyGen voice ID |
| `SYNTHESIA_API_KEY` | Synthesia | Synthesia API key (scaffold only) |
| `SYNTHESIA_AVATAR_ID` | Synthesia | Synthesia avatar ID |
| `GPU_SERVICE_URL` | GPU offload | Cloud Run GPU service URL (optional) |
| `GCS_BUCKET` | GPU offload | GCS bucket for slide/video transfer (optional) |

## GPU Acceleration

The video pipeline supports hardware acceleration for both TTS synthesis and video encoding. Detection is handled by `backend/services/gpu_utils.py`.

### TTS (PyTorch Device)

Kokoro TTS loads its model onto the best available device, controlled by `VIDEO_DEVICE`:

| `VIDEO_DEVICE` | Behavior |
|----------------|----------|
| `auto` (default) | Auto-detect: CUDA > MPS > CPU |
| `cuda` | Force NVIDIA GPU |
| `mps` | Force Apple Metal (Apple Silicon Macs) |
| `cpu` | Force CPU (disable GPU) |

### Video Encoding (ffmpeg Hardware Encoder)

Video composition uses hardware H.264 encoding when available, detected automatically:

| Encoder | Hardware | Platform |
|---------|----------|----------|
| `h264_videotoolbox` | Apple GPU/Media Engine | macOS |
| `h264_nvenc` | NVIDIA GPU | Linux/Windows |
| `h264_qsv` | Intel Quick Sync | Intel CPUs with iGPU |
| `h264_amf` | AMD GPU | AMD GPUs |
| `libx264` | Software (CPU) | All platforms (fallback) |

Hardware encoders are typically 5-10x faster than software encoding. The encoder is auto-detected by probing `ffmpeg -encoders`.

### Thread Control

Each ffmpeg composition worker gets a fair share of CPU cores via the `-threads` flag: `threads_per_worker = cpu_count // max_workers`. This prevents CPU cache thrashing when running multiple ffmpeg processes in parallel.

## Resource Requirements (Kokoro)

Kokoro TTS is memory-intensive and benefits from GPU acceleration:

| Resource | Minimum | Recommended | Notes |
|----------|---------|-------------|-------|
| RAM | 4 GiB | 4-8 GiB | Model: ~250 MB disk, ~3.4 GB peak during synthesis |
| CPU | 2 vCPU | 4 vCPU | TTS runs sequentially; ffmpeg encodes in parallel |
| Disk | 500 MB | 1 GB | Model download + temporary WAV + final MP4 files |

!!! info "GPU service removes RAM constraint from the CPU container"
    When `GPU_SERVICE_URL` is set, TTS and video encoding run on the GPU service (16 GiB, NVIDIA L4). The CPU service only uploads slide images and downloads finished MP4s, keeping its RAM at 4 GiB regardless of video load.

### Timing Benchmarks (5 topics, `VIDEO_TOPIC_LIMIT=5`)

Measured 2026-03-04: M&A PDF (33 slides, 5 topics, 792KB) on Mac M-series (MPS GPU + h264_videotoolbox).

| Phase | Duration | Notes |
|-------|----------|-------|
| TTS synthesis (sequential, MPS) | **7m 7s** | Kokoro 82M on Apple Metal GPU |
| ffmpeg composition (5 parallel, VideoToolbox) | **~21 min** | 2000x1125 @ 24fps, `preset=fast` |
| **Total Video stage** | **~28 min** | 5 videos, 423MB, 21.9 min total duration |

Output per video: 73-95 MB, 4.2-4.6 min each. Timing varies with script length, slide count, and hardware.

On GPU Cloud Run (NVIDIA L4): ~2-3 min total for 5 videos (~10x faster than local CPU).

### Local Development

| Scenario | RAM Needed | CPU | Duration (measured) |
|----------|-----------|-----|---------------------|
| PDF/PPT/Script only | 2 GB free | 2 cores | ~5.5 min |
| Full pipeline + Video (MPS GPU) | **4 GB free** | **4 cores** | **~34 min** |
| Full pipeline + Video (CPU-only) | **4 GB free** | **4 cores** | **~55 min** |

On 8 GB machines, close memory-heavy apps before video jobs. On 16 GB+ machines, no concern.

## Notes

- Video generation is optional and disabled by default in the web UI
- Selecting video output auto-enables Script + PPT generation
- Kokoro TTS runs in two phases: sequential TTS synthesis (shared model, memory-heavy) then parallel ffmpeg composition (`VIDEO_MAX_WORKERS` threads)
- Only the first `VIDEO_TOPIC_LIMIT` topics get videos (default 5) to manage compute time
- `preset='fast'` is used for ffmpeg encoding (same quality, ~2x faster, ~10% larger files)
- GPU acceleration is auto-detected: MPS on Apple Silicon, CUDA on NVIDIA, CPU fallback. Set `VIDEO_DEVICE=cpu` to force CPU mode.
- Hardware H.264 encoders (VideoToolbox, NVENC, QSV, AMF) are auto-detected and preferred over software `libx264`
- Each parallel ffmpeg worker gets `cpu_count // max_workers` threads to prevent CPU contention
- When `GPU_SERVICE_URL` is set, `_build_videos_dispatch()` in `agent_generate.py` bypasses `build_videos()` entirely and routes through the GCS+GPU service path
