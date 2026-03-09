# ADR-006: GPU Offload Architecture (CPU Orchestrator + GPU Worker via GCS)
<!-- Architecture Decision Record
     Place in: docs/adr/ADR-006-gpu-offload-architecture.md
     Reference from AGENTS.md so the agent knows these exist.
     Foundational decision that ADR-001 (3-tier fallback) builds upon. -->

**Date:** 2026-03-04
**Status:** Accepted
**Deciders:** Shreyas Jagannath (engineering lead)

---

## Context

CR8's video pipeline (Kokoro TTS at ~3.4 GB peak VRAM + parallel ffmpeg composition) is the only compute-heavy stage. The remaining pipeline -- PDF parsing, OpenAI/Tavily API calls, ChromaDB queries, PDF/PPT generation -- is I/O-bound and completes in ~5.5 minutes on a 2 vCPU instance. Adding video processing to the same instance caused two critical problems:

1. **OOM risk**: Kokoro TTS peaks at 3.4 GB RAM. The main Cloud Run instance (2 GiB) cannot host it. Scaling to 4+ GiB increases cost for every request, including non-video jobs.
2. **Image bloat**: ffmpeg, espeak-ng, libreoffice-impress, torch, and CUDA libraries inflated the Docker image from ~1 GB to ~5 GB, slowing cold starts from ~3s to 30-60s for all users.

Cloud Run instances are stateless and share no filesystem, so any multi-service architecture requires an external data bus for slide images (input) and MP4 videos (output). A GPU (NVIDIA L4) reduces the video phase from ~50 minutes (CPU) to ~3-4 minutes, and is paradoxically cheaper per job ($0.06 vs $0.13) because it finishes 8-10x faster.

## Decision

> We will use a separate Cloud Run GPU service for video processing, with GCS as the data bus between the CPU orchestrator and GPU worker, because Cloud Run instances share no filesystem and the GPU workload has fundamentally different resource requirements than the I/O-bound pipeline.

**Dispatch pattern:**

```
CPU orchestrator                    GCS bucket                    GPU worker
-----------------                   ----------                    ----------
1. Upload slides + manifest ------> gs://cr8-jobs/{job_id}/input/
2. POST /api/v1/video-jobs ----------------------------------------> 3. Download inputs
                                                                     4. TTS (sequential, GPU)
                                                                     5. ffmpeg (parallel, CPU)
                                                                     6. Upload MP4s ----------> gs://cr8-jobs/{job_id}/output/
7. GET  /api/v1/video-jobs/{id} <-- progress (phase, %, ETA)
8. Download videos <--------------- gs://cr8-jobs/{job_id}/output/
9. Cleanup GCS prefix
```

**Service-to-service auth**: Identity tokens via `google.oauth2.id_token.fetch_id_token()`, scoped to the target service URL. Returns `None` in local dev (no auth needed).

## Options Considered

| Option | Pros | Cons |
|--------|------|------|
| **Separate GPU service + GCS data bus (chosen)** | Clean separation; GPU scales to zero ($0 idle); main image stays lean (~1 GB, ~3s cold start); cheaper per job than CPU-only; real-time progress polling | Two services to deploy; GCS round-trip adds ~10-30s; identity token auth complexity; GPU cold start ~10-15s |
| **Video processing on main instance** | Single deployment; no network latency | OOM at 2 GiB (Kokoro needs 3.4 GB); 5 GB Docker image; 30-60s cold starts; CPU-only TTS is ~15-20 min; resource contention with pipeline I/O |
| **Cloud Run Jobs (batch)** | Designed for batch work; scale to zero | No HTTP polling -- cannot stream real-time progress to frontend; would need Pub/Sub or Firestore for status updates; more complex integration |
| **GKE with GPU node pool** | Full Kubernetes control; GPU sharing across pods | ~$200-300/month minimum even idle; massive operational complexity; overkill for <100 jobs/month |
| **External GPU provider (RunPod, Lambda Labs)** | Cheapest raw GPU ($0.02/job); fast cold starts | Cross-cloud egress costs and latency; no GCP IAM -- custom auth needed; harder to debug across cloud boundaries |

## Consequences

**Positive:**
- Main pipeline image is a lightweight I/O orchestrator (1 vCPU, 2 GiB, ~1 GB image, ~3s cold start)
- Pipeline never imports `torch`, `ffmpeg`, or Kokoro -- no heavyweight dependencies
- GPU costs ~$0.06 per 3-minute video job; $0 when idle (scale-to-zero)
- GCS acts as a durable checkpoint -- inputs survive GPU service restarts, enabling retry
- Real-time progress via HTTP polling (phases: `downloading` -> `tts` -> `composing` -> `uploading` -> `complete`)

**Negative / Trade-offs:**
- GCS upload/download adds ~10-30s per job (slide PNGs up, MP4s down)
- Two Docker images (`Dockerfile` + `Dockerfile.gpu`), two deploy commands, two log streams
- GPU in-memory job store is lost on restart (acceptable: GCS has final status, and jobs are short-lived)
- GPU cold start takes ~10-15s (CUDA init on first `torch.cuda.is_available()` + Kokoro model load)
- `google-auth` library required on CPU side for identity tokens

**Neutral:**
- Local development bypasses the split entirely -- `build_videos()` runs in-process when no `GPU_SERVICE_URL` is configured
- GCS bucket (`cr8-jobs`) is shared infrastructure, not per-environment -- job IDs provide namespace isolation
- This decision was later extended by ADR-001 (3-tier fallback chain) adding redundancy across regions

## Implementation Notes

- Files created: `gpu_service/` package (`app.py`, `worker.py`, `config.py`, `gcs_client.py`), `Dockerfile.gpu`
- Files created (CPU side): `backend/services/gpu_client.py` (`VideoServiceClient`), `backend/services/gcs_client.py` (`GCSVideoClient`)
- Files modified: `backend/pipeline/agent_generate.py` (`_build_videos_dispatch` routes to remote or local), `backend/config.py` (`gpu_service_url`, `gcs_bucket` settings)
- API contract on GPU service: `POST /api/v1/video-jobs` (202 Accepted), `GET /api/v1/video-jobs/{id}` (poll), `POST /api/v1/video-jobs/{id}/cancel`, `GET /health` (lightweight), `GET /health/detailed` (GPU + encoder probe)
- Config gate: `settings.should_use_video_service` -- `True` when any remote URL is set; `False` falls back to local `build_videos()`
- Auth pattern: `_get_identity_token(audience)` returns `None` outside GCP -- callers must handle both authenticated and unauthenticated paths
- Anti-patterns ruled out: Do NOT import `torch` or `tts_engine` in the CPU service; do NOT pass video data inline via HTTP (use GCS for large payloads); do NOT use shared filesystem assumptions between services
- Deployment lessons: `/health` must be lightweight (no torch import) for startup probe; `--no-cpu-throttling` required for GPU billing; pre-cache Kokoro model in `Dockerfile.gpu` because Cloud Run blocks HuggingFace Hub at runtime

## References

- Research note: `docs/research/deployment-strategies.md` (cost analysis, benchmarks)
- ADR-001: `docs/adr/ADR-001-three-tier-video-fallback.md` (extends this with 3-tier redundancy)
- GPU service: `gpu_service/` package (deployed europe-west4)
- CPU-side clients: `backend/services/gpu_client.py`, `backend/services/gcs_client.py`
- Dispatch logic: `backend/pipeline/agent_generate.py` (`_build_videos_dispatch`)
- Cloud Run GPU docs: https://cloud.google.com/run/docs/configuring/services/gpu
