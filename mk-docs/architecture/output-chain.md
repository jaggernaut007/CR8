# Output Chain

CR8 generates outputs in a dependency chain where each output builds on the previous one.

## The Dependency Chain

```mermaid
graph LR
    MM[modules_md] --> PDF[PDF\nGround Truth]
    PDF --> PPT[PPT\nGap Analysis]
    PPT --> SCR[Video Scripts\nSlide-Synced]
    SCR --> VID[AI Avatar Videos\nHeyGen]
```

## How Each Output Builds on the Previous

1. **Modules (markdown)** -- Generated per-topic from curriculum + research + gap analysis. Each module contains seven sections: Curriculum Coverage, Identified Gaps, Learning Objectives, Core Content, Industry Context, Key Takeaways, and Further Reading. Severity-based model routing selects GPT-5.1 for critical topics and GPT-5-mini for moderate/minor topics.

2. **PDF** -- Compiled from modules using fpdf2. This is the ground truth document. Includes a cover page, table of contents, and one chapter per topic with rich text rendering (bold, italic, code blocks). The PDF builder sanitizes Unicode characters for Helvetica/latin-1 compatibility.

3. **PPT** -- Structured around the PDF content. The LLM receives PDF module content plus gap analysis data and produces structured JSON for six slide types: title, executive summary, severity overview, per-topic gap detail, recommendations, and closing. Per-topic slides are generated in parallel (GPT-5-mini), and the executive summary uses GPT-5-nano.

4. **Scripts** -- Each script is synced to its PPT slide. The `SCRIPT_FROM_SLIDES` prompt receives the PPT slide structure, the PDF module content, and research/gap data for that specific topic. Output uses `[SLIDE N: title]` markers mapping 1:1 to PPT slides. Each script receives only its own topic's data (filtered context), saving ~86% on input tokens compared to passing all modules. Hook variety is enforced across scripts using thread-safe tracking.

5. **Videos** -- Kokoro TTS (default) or HeyGen API renders scripts as narrated slide videos. Video generation uses a two-phase pipeline: sequential TTS synthesis with a shared engine (memory-heavy), then parallel ffmpeg composition (`VIDEO_MAX_WORKERS` threads, default 12). When `GPU_SERVICE_URL` is configured, TTS and encoding are offloaded to a dedicated NVIDIA L4 Cloud Run service in europe-west1 via GCS data transfer (~2-3 min for 5 videos on GPU vs ~28 min locally). Configurable avatar emotion (`Friendly` default), speech speed (1.05x default). Limited to `VIDEO_TOPIC_LIMIT` topics (default 5).

## Format Selection

When running the pipeline, format dependencies are automatic:

- Selecting `video` auto-enables `script`
- Selecting `script` auto-enables `ppt`
- `pdf` is always generated

```bash
# PDF only (default)
python -m backend.run_pipeline files.pdf

# PDF + PPT
python -m backend.run_pipeline files.pdf --format pdf,ppt

# PDF + PPT + Scripts
python -m backend.run_pipeline files.pdf --format pdf,script

# Full chain: PDF + PPT + Scripts + Videos
python -m backend.run_pipeline files.pdf --format pdf,video
```

The web UI enforces the same dependencies with checkbox logic: checking "Script" auto-checks "PPT", checking "Video" auto-checks both "PPT" and "Script", and unchecking "PPT" auto-unchecks "Script" and "Video".

## Fallback Behavior

If PPT is not selected but scripts are requested, the pipeline falls back to per-module script generation using the `MODULE_TO_SCRIPT` prompt, which converts a learning module directly to a 2-minute spoken-word script without slide synchronization.

## Parallel Execution

Within the generate agent, PDF and PPT structuring run in parallel when both formats are requested. Script generation follows after PPT is complete (since scripts depend on slide structure). Video rendering uses one of two paths:

**Local path** (default, `GPU_SERVICE_URL` empty): Two-phase pipeline — Phase 1 sequential TTS synthesis with a shared engine (avoids reloading the ~250 MB model per video), Phase 2 parallel ffmpeg composition via `ThreadPoolExecutor` with `VIDEO_MAX_WORKERS` (default 12).

**GPU service path** (`GPU_SERVICE_URL` set): Slide PNGs are uploaded to GCS, a job is submitted to the remote GPU service, and the CPU pipeline polls for completion before downloading the finished MP4s. The local container is freed from memory-heavy TTS work.

```
                    ┌─────────┐
                    │ Modules │  (parallel per topic)
                    └────┬────┘
                         │
                ┌────────┴────────┐
                │                 │
           ┌────▼────┐     ┌─────▼─────┐
           │  PDF    │     │ PPT LLM   │  (parallel)
           │ build   │     │ structuring│
           └────┬────┘     └─────┬─────┘
                │                │
                │           ┌────▼────┐
                │           │  PPT    │
                │           │  build  │
                │           └────┬────┘
                │                │
                │           ┌────▼────┐
                │           │ Scripts │  (parallel per topic)
                │           └────┬────┘
                │                │
                │           ┌────▼────────────────────────────┐
                │           │ Videos                           │
                │           │  local: TTS seq → ffmpeg par     │
                │           │  GPU:   GCS upload → submit job  │
                │           │         → poll → download MP4s   │
                │           └────┬────────────────────────────┘
                │                │
                └────────┬───────┘
                         │
                    ┌────▼────┐
                    │  Done   │
                    └─────────┘
```
