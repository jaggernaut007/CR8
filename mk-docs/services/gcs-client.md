# GCS Client

Google Cloud Storage client for CPU↔GPU video job data transfer.

## Module

::: backend.services.gcs_client

## Overview

The `GCSVideoClient` manages data transfer between the CPU pipeline service and the GPU video service via a shared GCS bucket. Used when `GPU_SERVICE_URL` is configured.

### Data Flow

```
CPU service                    GCS bucket                     GPU service
───────────                    ──────────                     ───────────
upload_job_inputs() ────────> {job_id}/input/manifest.json
                              {job_id}/input/slide_001.png
                              {job_id}/input/slide_002.png
                                                              ──> downloads
                              {job_id}/output/topic_1.mp4     <── uploads
download_videos()  <────────  {job_id}/output/topic_2.mp4
cleanup_job()      ────────>  (deletes all blobs)
```

### Key Methods

| Method | Description |
|--------|-------------|
| `upload_job_inputs(job_id, slide_images, manifest)` | Uploads slide PNGs + manifest JSON |
| `download_videos(job_id, local_dir)` | Downloads completed MP4s |
| `cleanup_job(job_id)` | Deletes all blobs under `{job_id}/` |

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `GCS_BUCKET` | `cr8-jobs` | Shared GCS bucket name |
