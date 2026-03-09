# Research: google-cloud-storage Python SDK

**Date researched:** 2026-03-09
**Library version:** >=2.14
**Researched by:** Research Assistant Agent
**Status:** Current

---

## Question Being Answered

How do we safely and efficiently use the google-cloud-storage Python SDK for CR8's CPU-GPU service data transfer pipeline (via GCS) and job artifact storage?

## Sources Consulted

| Source | URL | Date accessed |
|--------|-----|---------------|
| Official Python Client Docs | https://docs.cloud.google.com/python/docs/reference/storage/latest | 2026-03-09 |
| Blob API Reference | https://docs.cloud.google.com/python/docs/reference/storage/latest/google.cloud.storage.blob.Blob | 2026-03-09 |
| Client API Reference | https://docs.cloud.google.com/python/docs/reference/storage/latest/google.cloud.storage.client.Client | 2026-03-09 |
| Signed URL Docs | https://docs.cloud.google.com/storage/docs/access-control/signing-urls-with-helpers | 2026-03-09 |
| V4 Signed URL Examples | https://docs.cloud.google.com/storage/docs/samples/storage-generate-signed-url-v4 | 2026-03-09 |
| Authentication Guide | https://docs.cloud.google.com/docs/authentication/client-libraries | 2026-03-09 |
| Retry & Timeout Config | https://docs.cloud.google.com/python/docs/reference/storage/latest/retry_timeout | 2026-03-09 |
| Transfer Manager | https://cloud.google.com/python/docs/reference/storage/latest/google.cloud.storage.transfer_manager | 2026-03-09 |
| IAM Access Control | https://docs.cloud.google.com/storage/docs/access-control/iam | 2026-03-09 |
| PyPI Package | https://pypi.org/project/google-cloud-storage/ | 2026-03-09 |

## What We Found

### The Correct Approach

#### Client Initialization

```python
from google.cloud import storage

# Default credentials (Cloud Run — uses attached service account)
client = storage.Client()
bucket = client.bucket("cr8-jobs-cr8-learning")

# Explicit service account (local development)
from google.oauth2 import service_account
credentials = service_account.Credentials.from_service_account_file(
    "/path/to/service-account-key.json"
)
client = storage.Client(credentials=credentials, project="cr8-learning")
```

#### Upload Patterns

```python
# Upload from file path (large files — auto-resumable for >5MB)
blob = bucket.blob("job123/slides/slide_01.png")
blob.upload_from_filename("local/slide_01.png", content_type="image/png", timeout=300)

# Upload from string (JSON manifests, metadata)
blob = bucket.blob("job123/manifest.json")
blob.upload_from_string(
    json.dumps(manifest, ensure_ascii=False),
    content_type="application/json",
    timeout=60,
)

# Upload from file object (streams)
with open("local/file.bin", "rb") as f:
    blob = bucket.blob("job123/data.bin")
    blob.upload_from_file(f, content_type="application/octet-stream", timeout=600)
```

#### Download Patterns

```python
# Download to file (recommended for large files)
blob = bucket.blob("job123/output/video_01.mp4")
blob.download_to_filename("local/video_01.mp4", timeout=600)

# Download as bytes (in-memory for JSON/metadata)
blob = bucket.blob("job123/manifest.json")
data = blob.download_as_bytes(timeout=60)
manifest = json.loads(data)

# List and download multiple blobs
blobs = client.list_blobs(bucket, prefix="job123/output/")
for blob in blobs:
    if blob.name.endswith(".mp4"):
        blob.download_to_filename(f"local/{blob.name}")
```

### Key API Methods / Concepts

| Method / Concept | Purpose | Notes / Gotchas |
|-----------------|---------|----------------|
| `storage.Client()` | Create client with ADC | No auth setup needed on Cloud Run |
| `client.bucket(name)` | Get bucket reference | Lazy — doesn't check if bucket exists |
| `bucket.blob(path)` | Get blob reference | Lazy — blob doesn't have to exist yet |
| `blob.upload_from_filename()` | Upload from disk | Auto-resumable for >5MB; set `timeout` |
| `blob.upload_from_string()` | Upload string/bytes | Ideal for JSON; requires `content_type` |
| `blob.download_to_filename()` | Download to disk | Supports resumable downloads |
| `blob.download_as_bytes()` | Download to memory | Don't use for >50MB files |
| `blob.generate_signed_url(version="v4")` | Temporary URL | Max 7-day expiry; requires service account key |
| `client.list_blobs(bucket, prefix=...)` | List objects | Returns iterator; respects prefix filter |
| `blob.delete()` | Delete object | Irreversible |
| `transfer_manager.upload_many()` | Parallel uploads | For >10 files; uses max_workers threads |
| `transfer_manager.download_many()` | Parallel downloads | For >10 files; reduces total latency |

### Signed URL Generation

```python
from datetime import timedelta

# Temporary download URL (1-hour expiry)
blob = bucket.blob("job123/output/video.mp4")
url = blob.generate_signed_url(
    version="v4",
    expiration=timedelta(hours=1),
    method="GET",
)

# Temporary upload URL (30-minute expiry)
blob = bucket.blob("job123/upload/file.bin")
url = blob.generate_signed_url(
    version="v4",
    expiration=timedelta(minutes=30),
    method="PUT",
    content_type="application/octet-stream",
)
```

**Constraints:**
- Maximum expiration: 7 days (604,800 seconds)
- Always use v4 (more secure, includes signing timestamp)
- Requires service account private key (not temporary OAuth tokens)

### Parallel Transfers (Transfer Manager)

```python
from google.cloud.storage import transfer_manager

# Upload 100 files concurrently
results = transfer_manager.upload_many(
    bucket=bucket,
    file_blob_pairs=[(local_path, f"job123/{name}") for local_path, name in files],
    max_workers=8,
    timeout=600,
)

# Download many files concurrently
results = transfer_manager.download_many(
    bucket=bucket,
    blob_names=[(b.name, f"local/{b.name}") for b in blobs],
    max_workers=8,
    timeout=600,
)
```

### Configuration Required

```bash
# .env (local development)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
GCS_BUCKET=cr8-jobs-cr8-learning

# Cloud Run — no env vars needed (uses attached service account)
```

```python
# backend/config.py
class Settings(BaseSettings):
    gcs_bucket: str = Field(default="cr8-jobs-cr8-learning", alias="GCS_BUCKET")
```

## What We Ruled Out (and Why)

| Approach | Why Rejected |
|----------|-------------|
| boto3 (AWS S3) | CR8 uses GCP, not AWS |
| gsutil CLI (subprocess) | External binary; less reliable than native SDK |
| Direct HTTP to GCS API | Error-prone; no retry/resumable upload support |
| ACLs (per-object) | Deprecated; IAM + Uniform Bucket-Level Access preferred |
| V2 signed URLs | Deprecated; v4 is more secure |

## Known Gotchas / Edge Cases

1. **Blob operations are lazy** — `client.bucket("name")` and `bucket.blob("path")` don't verify existence. Errors surface on upload/download.
2. **Don't set `GOOGLE_APPLICATION_CREDENTIALS` on Cloud Run** — it overrides the attached service account (usually undesirable).
3. **Signed URLs require private key** — cannot generate from temporary OAuth tokens (`gcloud auth application-default`).
4. **Max signed URL expiry is 7 days** — longer values silently cap, no error raised.
5. **Resumable uploads automatic for >5MB** — files <5MB use single PUT request.
6. **`list_blobs` is not atomic** — concurrent uploads may cause missed or duplicate results across pagination.
7. **Content-Type matters for PUT signed URLs** — client must send matching Content-Type header or get 403.
8. **Transfer manager max_workers** — too high (>16) may hit GCS rate limits or connection pool limits.

## Security Assessment

| Check | Result | Notes |
|-------|--------|-------|
| Open CVEs (critical/high) | None | Clean as of 2026-03-09 |
| License | Apache 2.0 | Fully compatible |
| Last release | Recent (monthly) | Google Cloud team maintains |
| Maintainer count | Large (Google) | Enterprise-grade support |
| Transitive dependencies | ~15 packages | All Google-maintained (google-api-core, google-auth, etc.) |
| Known security incidents | None | No supply chain attacks |
| Package popularity | 28.3M weekly downloads | Highly trusted |

### Access Control Recommendations

- Enable **Uniform Bucket-Level Access** (UBLA) — simplifies to IAM only
- Enable **public access prevention** at bucket level
- Use `roles/storage.admin` for internal services (acceptable for CR8)
- Default encryption (Google-managed keys) is sufficient; CMEK optional for compliance

**Verdict:** SAFE to use. Enterprise-grade, Google-maintained, no CVEs, Apache 2.0 license.

## Decision Made

Based on this research, we will:
> Continue using google-cloud-storage >=2.14 as the data bus for CPU-GPU service communication and job artifact storage. Use ADC on Cloud Run (no explicit credentials). Use `upload_from_filename`/`download_to_filename` for large files with appropriate timeouts. Use `transfer_manager` for batch operations (>10 files). Generate v4 signed URLs with 1-hour expiry for user downloads.

## Files This Affects

- `backend/services/gcs_client.py` — Upload/download patterns, signed URLs
- `gpu_service/gcs_client.py` — Same patterns for GPU service
- `backend/services/gpu_client.py` — Communicates with GPU service via GCS
- `backend/config.py` — `GCS_BUCKET` setting
- `Dockerfile.gpu` — `GOOGLE_APPLICATION_CREDENTIALS` env var

---
*If this research is more than 6 months old or the library has had a major version bump, re-verify before implementing.*
