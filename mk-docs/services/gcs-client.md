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

| Method | Signature | Description |
|--------|-----------|-------------|
| `upload_job_inputs` | `(job_id, slide_images, manifest, pptx_path=None)` | Uploads slide PNGs (or PPTX for remote export) + manifest JSON |
| `download_videos` | `(job_id, local_dir)` | Downloads completed MP4s |
| `cleanup_job` | `(job_id)` | Deletes all blobs under `{job_id}/` |

### PPTX Upload for Remote Slide Export

The `upload_job_inputs` method accepts an optional `pptx_path` parameter. When the CPU pipeline container cannot export slide images locally (LibreOffice is not installed), it uploads the generated PPTX file instead. The GPU or CPU-video worker receives the PPTX via GCS and performs the conversion to PNGs.

```
upload_job_inputs(job_id, slide_images=[], manifest=..., pptx_path="outputs/gap_analysis.pptx")
  ├── uploads manifest.json
  ├── slide_images is empty → skips PNG upload loop
  └── pptx_path set → uploads PPTX as {job_id}/input/gap_analysis.pptx
```

The manifest includes `pptx_name` (the basename of the uploaded PPTX) so the remote worker knows which file to convert.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `GCS_BUCKET` | `cr8-jobs` | Shared GCS bucket name |
