# Research: CR8 Deployment Strategies — CPU vs GPU

**Date:** 2026-03-04
**Status:** Current
**Question:** What's the most cost-efficient way to deploy CR8, and should we split CPU/GPU workloads?

---

## Workload Profile

| Phase | What Happens | CPU-bound? | GPU-accelerable? | Duration (measured) |
|-------|-------------|-----------|------------------|---------------------|
| Ingest | PDF parse, chunking, ChromaDB embed | Light | No | **51s** |
| Research | Tavily web search, OpenAI calls | I/O-bound | No | **2m 29s** |
| Generate | OpenAI calls for modules/scripts + PDF/PPT build | I/O-bound | No | **2m 19s** |
| Slide Export | PPTX → 33 PNG images via LibreOffice | Light | No | **14s** |
| **TTS** | **Kokoro 82M model inference (sequential)** | **Heavy** | **Yes (MPS/CUDA)** | **7m 7s (MPS)** |
| **Video compose** | **ffmpeg encode 5 videos (parallel)** | **Heavy** | **Yes (hw encoder)** | **~21m (VideoToolbox)** |

**Measured 2026-03-04:** M&A Presentation PDF (33 slides, 5 topics, 792KB) on Mac M-series with MPS GPU + h264_videotoolbox. Total: **~34 min**. Output: 5 videos, 423MB, 21.9 min total duration.

**Key insight:** Without video, the pipeline completes in ~5.5 min (I/O-bound, waiting on APIs). With video, ffmpeg composition alone takes ~21 min (62% of total) due to raw frame piping at 2000x1125.

---

## Kokoro TTS Benchmarks (from published benchmarks)

Real-Time Factor = audio duration / processing time. Higher = faster.

| Hardware | RTF (PyTorch) | 12 min audio → |
|----------|--------------|----------------|
| CPU 32-core (c6a.8xlarge) | 5x | ~2.4 min |
| CPU 4-core (Cloud Run) | ~1.5x (estimated) | **~8 min** |
| **NVIDIA T4** | **36x** | **~20 sec** |
| **NVIDIA L4** | **81x** | **~9 sec** |
| NVIDIA A10G | 96x | ~7.5 sec |

Source: [Kokoro v1 Benchmark](https://gist.github.com/efemaer/23d9a3b949b751dde315192b4dcf0653)

**Conclusion:** GPU turns 8-15 min of TTS into <30 seconds. This is the single biggest optimization available.

---

## Option 1: CPU-Only Cloud Run (Current Setup)

```
Cloud Run (4 vCPU, 4 GiB) — single monolith
```

### Configuration

| Setting | Without Video | With Video |
|---------|-------------|-----------|
| CPU | 2 vCPU | 4 vCPU |
| Memory | 2 GiB | 4 GiB (Kokoro peaks 3.4 GB) |
| Timeout | 3600s | 3600s |
| min-instances | 0 | 0 |
| `--no-cpu-throttling` | Required | Required |

### Timing

| Pipeline Mode | Cold Start | Processing | Total |
|--------------|-----------|-----------|-------|
| Text only (PDF/PPT/Script) | 30-60s | ~5.5 min | ~6-7 min |
| With video (5 topics, MPS GPU) | 30-60s | **~34 min** | **~35 min** |
| With video (5 topics, CPU-only) | 30-60s | **~50-60 min** | **~55-65 min** |

### Cost Per Job (Tier 1 region)

Pricing: $0.000024/vCPU-sec, $0.0000025/GiB-sec

| Mode | Compute | Memory | **Total** |
|------|---------|--------|-----------|
| Text (2 vCPU, 2 GiB, 300s) | $0.014 | $0.0015 | **~$0.02** |
| Video (4 vCPU, 4 GiB, 1200s) | $0.115 | $0.012 | **~$0.13** |

### Monthly Estimates

| Usage | Text Only | With Video |
|-------|----------|-----------|
| 5 jobs/month | ~$0.10 | ~$0.65 |
| 20 jobs/month | ~$0.40 | ~$2.60 |
| Always-on (min=1) | ~$70/mo | ~$137/mo |

**Verdict:** Extremely cheap for light use. Video is slow but functional.

---

## Option 2: Cloud Run with L4 GPU (Recommended for Video)

```
Cloud Run CPU service (main pipeline)
  └─→ Cloud Run GPU service (TTS + video only)
```

### Cloud Run GPU Requirements

- GPU: NVIDIA L4 (24 GB VRAM)
- Minimum: 4 CPU, 16 GiB memory (enforced by GCP)
- Cold start: ~5s infrastructure + ~5-10s model load = **~10-15s**
- Scale to zero: Yes (pay nothing when idle)
- Pricing: **$0.000187/GPU-sec (~$0.67/hr)** + CPU/memory costs

Source: [Cloud Run GPU docs](https://docs.cloud.google.com/run/docs/configuring/services/gpu)

### Timing with GPU

| Phase | CPU-only | MPS (Mac) | L4 GPU (est.) |
|-------|----------|-----------|---------------|
| TTS (22 min audio) | ~15-20 min | **7m 7s** | **~15 sec** |
| ffmpeg encode (5 topics, 33 slides) | ~30-40 min | **~21 min** (VideoToolbox) | **~2-3 min** (NVENC) |
| **Total video phase** | **~50 min** | **~28 min** | **~3-4 min** |
| **Full pipeline** | **~55 min** | **~34 min** | **~9-10 min** |

### Cost Per Video Job (L4 GPU, ~180s active)

| Resource | Rate | Duration | Cost |
|----------|------|----------|------|
| GPU (L4) | $0.000187/s | 180s | $0.034 |
| CPU (4 vCPU) | $0.000024/vCPU-s | 180s | $0.017 |
| Memory (16 GiB) | $0.0000025/GiB-s | 180s | $0.007 |
| **Total** | | | **~$0.06** |

**GPU is CHEAPER than CPU per job** because it finishes 8-10x faster.

### Hybrid Architecture Monthly Estimates

| Usage | CPU Service | GPU Service | **Total** |
|-------|-----------|-----------|-----------|
| 5 video jobs/month | ~$0.10 | ~$0.30 | **~$0.40** |
| 20 video jobs/month | ~$0.40 | ~$1.20 | **~$1.60** |
| 100 video jobs/month | ~$2.00 | ~$6.00 | **~$8.00** |

---

## Option 3: Third-Party Serverless GPU

For maximum cost efficiency on GPU, these platforms offer per-second billing:

### Modal.com

| GPU | Price/hr | 3-min job cost | Cold start |
|-----|---------|---------------|-----------|
| T4 | ~$0.59 | ~$0.03 | 2-5s |
| L4 | ~$0.59-0.80 | ~$0.03-0.04 | 2-5s |

- Per-second billing, scale to zero
- **Caveat:** Production multipliers (non-preemptible, regional) can push to 3.75x base price
- Python SDK with `@modal.function(gpu="L4")` decorator — clean integration
- Source: [Modal pricing](https://modal.com/pricing)

### RunPod Serverless

| GPU | Price/hr | 3-min job cost | Cold start |
|-----|---------|---------------|-----------|
| T4 | ~$0.40 | ~$0.02 | 5-10s |
| RTX 4090 | ~$0.35 | ~$0.018 | 5-10s |

- Pay-per-second on flex workers, scale to zero
- Cheapest raw GPU pricing
- Custom Docker endpoint required
- Source: [RunPod pricing](https://www.runpod.io/pricing)

### Comparison Table

| Platform | L4 cost/hr | 3-min video job | Scale to zero? | Cold start | Integration effort |
|----------|-----------|----------------|---------------|-----------|-------------------|
| **Cloud Run GPU** | $0.67 | $0.06 | Yes | 10-15s | Low (same GCP) |
| **Modal** | $0.59-0.80 | $0.03-0.04 | Yes | 2-5s | Medium (SDK) |
| **RunPod** | $0.40 | $0.02 | Yes | 5-10s | High (custom endpoint) |

---

## Recommended Architecture

### For MVP / Light Use (< 20 video jobs/month)

**CPU-only Cloud Run.** Cost is negligible (~$3/month). ~50-60 min video processing on CPU is slow but acceptable for an MVP.

```yaml
# deploy.sh
gcloud run deploy cr8-pipeline \
  --memory=4Gi --cpu=4 \
  --timeout=3600 \
  --min-instances=0 --max-instances=1 \
  --no-cpu-throttling
```

### For Production / User-Facing (needs <10 min response)

**Hybrid: Cloud Run CPU + Cloud Run GPU**

```
┌─────────────────────┐      HTTP/gRPC      ┌──────────────────────┐
│  cr8-pipeline (CPU) │ ──────────────────→  │  cr8-gpu (L4 GPU)    │
│  2 vCPU, 2 GiB      │                      │  4 CPU, 16 GiB, L4   │
│  Ingest/Research/Gen │                      │  Kokoro TTS + ffmpeg  │
│  min-instances=0     │                      │  min-instances=0      │
└─────────────────────┘                      └──────────────────────┘
```

- Main service handles PDF/PPT/Script (~5.5 min, cheap)
- GPU service called only for video generation (~3-4 min, ~$0.06/job)
- Both scale to zero independently
- **Total per video job: ~$0.08** | **Total time: ~9-10 min**

### For Maximum Cost Optimization

**Cloud Run CPU + Modal/RunPod GPU** — saves ~50% on GPU cost but adds integration complexity and cross-cloud latency.

---

## Decision Matrix

| Factor | CPU Only | Cloud Run GPU | Modal GPU | RunPod GPU |
|--------|---------|--------------|----------|-----------|
| Video processing time | ~50 min (CPU) / ~28 min (MPS) | **~3-4 min** | **~3-4 min** | **~3-4 min** |
| Cost per video job | $0.13 | **$0.06** | $0.03-0.04 | $0.02 |
| Integration effort | None | Low | Medium | High |
| Cold start | 30-60s | 10-15s | 2-5s | 5-10s |
| Operational complexity | Minimal | Low | Medium | Medium |
| Vendor lock-in | GCP | GCP | Modal | RunPod |
| Scale to zero | Yes | Yes | Yes | Yes |

---

## Implementation Priority

1. **Now:** Deploy CPU-only (already documented in mk-docs/deployment/)
2. **When video speed matters:** Add Cloud Run GPU service (same ecosystem, easiest)
3. **When cost-optimizing at scale:** Evaluate Modal as GPU backend (best price-performance)

---

## Files Affected by GPU Split

- `backend/services/video_builder.py` — Add HTTP client path to GPU service
- `backend/services/tts_engine.py` — Move to GPU service container
- `backend/services/gpu_utils.py` — Already handles device detection
- `Dockerfile` — Split into `Dockerfile.cpu` and `Dockerfile.gpu`
- `deploy.sh` — Deploy two services
- New: `backend/services/gpu_client.py` — HTTP client for GPU service
