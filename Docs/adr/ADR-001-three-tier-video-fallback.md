# ADR-001: Three-Tier Video Service Fallback Architecture
<!-- Architecture Decision Record
     Place in: docs/adr/ADR-001-three-tier-video-fallback.md
     Reference from AGENTS.md so the agent knows these exist. -->

**Date:** 2026-03-06
**Status:** Superseded (2026-03-14 — simplified to 2-tier: GPU Primary → CPU Video. GPU Fallback in europe-west1 removed to cut Artifact Registry storage costs.)
**Deciders:** Shreyas Jagannath (engineering lead)

---

## Context

CR8's video pipeline (Kokoro TTS + ffmpeg composition) is the most resource-intensive stage, requiring either GPU acceleration or high-CPU capacity. The main Cloud Run instance (1 vCPU / 2 GiB) is an I/O orchestrator — it calls OpenAI, Tavily, ChromaDB, and coordinates outputs. Running video processing on the main instance caused two problems:

1. **Resource contention**: Kokoro TTS model (~3.4 GB) + parallel ffmpeg workers exceeded the main instance's memory, causing OOM crashes or forcing expensive scaling.
2. **Dependency bloat**: ffmpeg, espeak-ng, libreoffice-impress, and CUDA libraries inflated the Docker image from ~1 GB to ~5 GB, slowing cold starts.

GPU Cloud Run instances (NVIDIA L4) provide fast TTS (~15s vs ~20 min on CPU) but have limited regional availability and can fail to allocate. A single GPU service in one region was a single point of failure.

## Decision

> We will use a 3-tier fallback chain of dedicated video services, removing all video processing from the main pipeline instance.

**Fallback order:**

| Tier | Service | Region | Hardware | Speed |
|------|---------|--------|----------|-------|
| 1 | GPU Primary | europe-west4 (Netherlands) | NVIDIA L4, 4 CPU, 16 GiB | ~3-4 min |
| 2 | GPU Fallback | europe-west1 (Belgium) | NVIDIA L4, 4 CPU, 16 GiB | ~3-4 min |
| 3 | CPU Video | europe-west2 (London) | 8 vCPU, 32 GiB | ~25-30 min |

**Fallback triggers** (infrastructure failures only):

| Trigger | Action |
|---------|--------|
| `ConnectionError` (service unreachable) | Try next tier |
| `Timeout` (no response within submit timeout) | Try next tier |
| `HTTPError` (5xx from service) | Try next tier |
| Job returns `status: "error"` | **Do NOT fallback** — job ran but failed |
| `PipelineCancelledError` | **Propagate immediately** — user cancelled |

**Key design rules:**
- Once a tier accepts a job (HTTP 202), all polling stays on that tier — no cross-tier polling.
- Each tier gets a fresh identity token scoped to its URL (Cloud Run IAM requirement).
- All tiers implement the same API contract (`/health`, `/api/v1/video-jobs`).
- All tiers scale to zero ($0 when idle).

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **3-tier fallback chain (chosen)** | Fast path when GPUs available; always-available CPU safety net; $0 idle cost; clean separation of concerns | 3 separate deployments to manage; CPU tier is slow (~25 min); more complex client code |
| **Single GPU service (no fallback)** | Simple deployment; fast processing | Single point of failure; GPU allocation failures cause video generation to fail entirely |
| **Video processing on main instance** | No additional services; simple architecture | OOM risk; 5 GB Docker image; slow cold starts; resource contention with pipeline I/O |
| **External video API (e.g., HeyGen)** | No infrastructure to manage; scalable | Per-video cost; vendor lock-in; latency; privacy concerns with curriculum data |

## Consequences

**Positive:**
- Main instance is a lightweight I/O orchestrator (1 vCPU / 2 GiB, ~1 GB image, ~3s cold start)
- Video generation always succeeds if at least one tier is healthy
- GPU failures are transparent to users — automatic fallback with no manual intervention
- Each service scales independently and costs $0 when idle

**Negative / Trade-offs:**
- 3 Docker images to build and deploy (Dockerfile, Dockerfile.gpu, Dockerfile.cpu-video)
- CPU tier is ~8x slower than GPU — acceptable as a last-resort safety net
- `cpu_video_service/worker.py` imports private functions (`_compose_video`, `_slugify`, `_get_topic_images`) from `backend.services.video_builder` — tight coupling to internal API
- Cold start timeouts must be generous (10s health, 60s submit) to handle Cloud Run scale-to-zero

**Neutral:**
- `GPUVideoClient` renamed to `VideoServiceClient` (backward-compatible alias preserved)
- `should_use_gpu_service` replaced by `should_use_video_service` in config
- Local development still uses `build_videos()` directly when no service URLs are configured

## Implementation Notes

- Files created: `cpu_video_service/` package (app.py, worker.py, config.py, gcs_client.py), `Dockerfile.cpu-video`
- Files modified: `backend/services/gpu_client.py` (3-tier client), `backend/config.py` (new settings), `backend/pipeline/agent_generate.py` (dispatch logic), `Dockerfile` (stripped video deps)
- Client class: `VideoServiceClient` in `backend/services/gpu_client.py` — iterates `_tiers` list, catches `(ConnectionError, Timeout, HTTPError)` to trigger fallback
- API contract: `POST /api/v1/video-jobs` (submit), `GET /api/v1/video-jobs/{id}` (poll), `POST /api/v1/video-jobs/{id}/cancel`, `GET /health`
- Config: `GPU_SERVICE_URL`, `GPU_FALLBACK_URL`, `CPU_VIDEO_SERVICE_URL` env vars
- Anti-pattern: Do NOT retry on job-level `status: "error"` — the input is bad, retrying elsewhere won't fix it
- Future: Extract shared video utilities (`_compose_video`, `_slugify`) into a common package to reduce private API coupling

## References

- Plan: `.claude/plans/cheeky-wiggling-cookie.md` (v0.4.2 implementation plan)
- GPU service: `gpu_service/` package (existing, deployed europe-west4)
- CPU video service: `cpu_video_service/` package (new, v0.4.2)
- Video builder: `backend/services/video_builder.py` (shared composition logic)
- Cloud Run GPU docs: https://cloud.google.com/run/docs/configuring/services/gpu
