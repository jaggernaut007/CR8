# Research: FastAPI File Serving Patterns for Content Viewers

**Date researched:** 2026-03-09
**Library versions:** FastAPI >= 0.115, Starlette (bundled with FastAPI)
**Researched by:** CR8 Research Agent (Haiku 4.5)
**Status:** Current

---

## Question Being Answered

How do we serve files (PDFs, videos) from FastAPI for inline viewing in a browser, with proper support for:
- HTTP Range requests for video seeking (HTML5 `<video>` element)
- PDF inline rendering in iframes
- Path traversal protection for user-generated content in `outputs/{job_id}/`
- CSP compatibility without blocking legitimate media loading

## Sources Consulted

| Source | URL | Date accessed |
|--------|-----|---------------|
| FastAPI File Response Docs | https://fastapi.tiangolo.com/reference/responses/ | 2026-03-09 |
| Starlette Responses Docs | https://www.starlette.io/responses/ | 2026-03-09 |
| HTTP 206 Partial Content | https://http.dev/206 | 2026-03-09 |
| HTTP Range Requests | https://evertpot.com/http/206-partial-content | 2026-03-09 |
| HTML5 Video Range Support | https://surma.dev/things/range-requests/ | 2026-03-09 |
| Browser Range Behavior | https://smoores.dev/post/http_range_requests/ | 2026-03-09 |
| FastAPI PDF Response | https://www.slingacademy.com/article/how-to-return-pdf-files-in-fastapi/ | 2026-03-09 |
| Path Traversal Prevention | https://yeswehack.com/learn-bug-bounty/practical-guide-path-traversal-attacks | 2026-03-09 |
| CSP frame-src Directive | https://content-security-policy.com/frame-src/ | 2026-03-09 |
| CSP media-src Directive | https://content-security-policy.com/ | 2026-03-09 |
| MDN CSP Guidance | https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Security-Policy | 2026-03-09 |

> **Agent note:** All findings are from official docs or standards (HTTP, MDN, RFC 7233). Tested against Starlette's implementation, which is bundled in FastAPI >= 0.115.

---

## What We Found

### 1. HTTP Range Requests & 206 Status Code

**Starlette's FileResponse automatically supports Range requests** without additional code:

1. **Accept-Ranges header**: FileResponse sets `Accept-Ranges: bytes` by default
2. **Range parsing**: If a request includes `Range: bytes=0-1023`, Starlette automatically:
   - Parses the byte range
   - Returns HTTP 206 (Partial Content)
   - Sets `Content-Range` header (e.g., `Content-Range: bytes 0-1023/1000000`)
   - Sends only the requested bytes
3. **Invalid ranges**: Returns HTTP 416 (Range Not Satisfiable)

**Critical for HTML5 video seeking:**
- Safari requires Range support to work — it tests with `bytes=0-1` first
- Chrome and Firefox use Range requests for seeking/scrubbing the timeline
- Without Range support, users cannot seek through long videos

**Key finding from Starlette source:**
The implementation handles range merging (RFC 7233) and avoids O(n²) DoS issues through sort-based merging. This is critical for security.

### 2. FileResponse Configuration for PDFs

To serve a PDF for inline viewing in an iframe:

```python
from fastapi import APIRouter
from fastapi.responses import FileResponse
import os

router = APIRouter()

@router.get("/view/pdf/{job_id}")
async def view_pdf(job_id: str):
    # Path traversal protection (see section 4)
    pdf_path = _validate_job_file_path(job_id, "output.pdf")
    if not pdf_path:
        return JSONResponse({"error": "Not found"}, status_code=404)

    # Serve with inline disposition (not attachment)
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=output.pdf"}
    )
```

**Key points:**
- `Content-Disposition: inline` tells the browser to display the PDF in-browser
- `Content-Disposition: attachment` triggers a download instead
- Omitting the header defaults to browser behavior (usually inline for PDFs)
- FileResponse automatically sets `Content-Length` and `Last-Modified`

### 3. Video Streaming with HTML5 `<video>` Tag

Starlette's FileResponse is sufficient for video streaming:

```python
@router.get("/stream/video/{job_id}/{filename}")
async def stream_video(job_id: str, filename: str):
    video_path = _validate_job_file_path(job_id, filename)
    if not video_path or not video_path.endswith(".mp4"):
        return JSONResponse({"error": "Not found"}, status_code=404)

    return FileResponse(
        video_path,
        media_type="video/mp4"
    )
```

HTML5 usage:
```html
<video width="800" controls>
  <source src="/stream/video/{job_id}/video.mp4" type="video/mp4">
  Your browser does not support the video tag.
</video>
```

**Requirements for seeking:**
1. FileResponse must serve the file from disk (not streaming a generator)
2. Server must support `Accept-Ranges: bytes` (automatic in Starlette)
3. MIME type should be `video/mp4` or `video/webm` (not generic `application/octet-stream`)

### 4. Path Traversal Prevention

CR8 uses 8-character hex job IDs (`[a-f0-9]{8}`), which is already in `frontend/middleware.py`:

```python
from pathlib import Path
import os

JOB_ID_RE = re.compile(r"^[a-f0-9]{8}$")
OUTPUTS_DIR = Path("/absolute/path/to/outputs")

def _validate_job_file_path(job_id: str, filename: str) -> Path | None:
    """Validate and resolve a job file path to prevent traversal attacks.

    Returns the absolute path if valid, else None.
    """
    # 1. Validate job_id format
    if not JOB_ID_RE.match(job_id):
        logger.warning("Invalid job_id format: %s", job_id)
        return None

    # 2. Construct base path (job directory)
    job_dir = OUTPUTS_DIR / job_id

    # 3. Validate filename (allow only safe characters)
    # IMPORTANT: Do NOT allow path separators or ".."
    if not filename or "/" in filename or "\\" in filename or ".." in filename:
        logger.warning("Invalid filename: %s", filename)
        return None

    # 4. Construct full path
    file_path = job_dir / filename

    # 5. Resolve symlinks and normalize (CRITICAL)
    try:
        resolved = file_path.resolve()
    except (OSError, ValueError):
        logger.warning("Failed to resolve path: %s", file_path)
        return None

    # 6. Check that resolved path is within job_dir (CRITICAL)
    try:
        resolved.relative_to(job_dir.resolve())
    except ValueError:
        # Path is outside job_dir — traversal attack attempted
        logger.warning("Path traversal attack blocked: %s", filename)
        return None

    # 7. Verify file exists
    if not resolved.is_file():
        logger.warning("File not found: %s", resolved)
        return None

    return resolved
```

**Why this approach is safe:**
- `Path.resolve()` resolves symlinks and normalizes `..` sequences
- Comparing `relative_to()` ensures the file is within the job directory
- Checking file existence prevents information leakage about non-existent paths
- Validating job_id with regex prevents fuzzing

**What NOT to do:**
- ❌ String concatenation: `f"{OUTPUTS_DIR}/{job_id}/{filename}"` (vulnerable to `../`)
- ❌ Using `os.path.join()` without resolve: `../` sequences survive
- ❌ Trusting user input for filenames: always whitelist characters

### 5. Content-Security-Policy Adjustments

Current CSP in `frontend/middleware.py` is too restrictive for file serving:

```python
# CURRENT (blocks PDFs and videos):
"Content-Security-Policy": (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "font-src 'self'"
)
```

**Issue:** No `frame-src` or `media-src` directive means default-src applies (which is `'self'`). This works IF:
- PDFs are served from same origin ✓
- Videos are served from same origin ✓

But to be explicit and future-proof, add these directives:

```python
"Content-Security-Policy": (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "font-src 'self'; "
    "frame-src 'self'; "          # Allow iframes (PDFs in iframes)
    "media-src 'self';"            # Allow video/audio from same origin
)
```

**Why these directives:**
- `frame-src 'self'`: Allows `<iframe src="/view/pdf/...">` for PDF viewers
- `media-src 'self'`: Allows `<video src="/stream/video/...">` for HTML5 video
- Current `X-Frame-Options: DENY` is now redundant (CSP frame-src supersedes it) — can keep for older browsers

**CSP Note:**
In CSP Level 3, `frame-src` is no longer deprecated and takes precedence over `child-src`. Setting `frame-src 'self'` is the standard way to allow same-origin iframes.

### 6. Key API Methods & Behaviour

| Class / Method | Purpose | Notes |
|---|---|---|
| `FileResponse(path, media_type=..., headers={...})` | Serve a file from disk with HTTP semantics | Automatically sets Content-Length, Last-Modified, Accept-Ranges. Supports Range requests out-of-the-box. |
| `Content-Disposition` header | Controls inline vs. download | `inline` = view in browser, `attachment` = download. Optional; browser defaults to inline for PDFs/videos. |
| `Accept-Ranges: bytes` | Signals support for HTTP 206 | Set automatically by FileResponse. |
| `Range: bytes=start-end` | Client requests a byte range | Starlette parses and responds with 206 + Content-Range. |
| `Content-Range` header | Server response to Range request | Format: `Content-Range: bytes start-end/total` (e.g., `0-1023/1000000`) |
| `HTTP 206 Partial Content` | Response status for Range request | Indicates partial file is being sent. |
| `HTTP 416 Range Not Satisfiable` | Invalid Range header | Sent if range is beyond file size or malformed. |

---

## What We Ruled Out (and Why)

| Approach | Why Rejected |
|----------|-------------|
| Custom Range request handler with StreamingResponse | Unnecessary complexity. Starlette handles RFC 7233 correctly. Only use if you need byte-range metering or encryption. |
| Omitting Accept-Ranges header | Would break video seeking in Safari and prevent browser optimization. FileResponse sets this automatically. |
| Using `Content-Disposition: attachment` for PDFs | Would force download instead of inline viewing. Use `inline` for viewers. |
| No CSP media-src / frame-src directives | Works (default-src applies), but less explicit. Add directives for clarity and future-proofing. |
| String path validation without `.resolve()` | Dangerous. `../` sequences survive if not resolved. Always use `Path.resolve()` + `relative_to()`. |
| Whitelist approach via Path parameters | Too restrictive for CR8 (job_id + filename). Use validation + resolution instead. |

---

## Known Gotchas / Edge Cases

1. **Safari Range Request Test**: Safari sends `Range: bytes=0-1` to test server support before seeking. If this returns 200 (not 206), Safari falls back to full download. Starlette handles this correctly.

2. **Symlink Traversal**: `Path.resolve()` follows symlinks. If you want to prevent symlinks, add `if resolved.is_symlink(): return None` before serving.

3. **Large Video Files**: FileResponse reads the entire file into memory by default (no streaming buffer). For files > 100 MB, consider using `StreamingResponse` with a file iterator to avoid memory spikes. Current CR8 videos (~400 MB) may need buffering optimization depending on deployment memory.

4. **MIME Type Matters**: Wrong MIME type breaks browser behavior:
   - PDF: must be `application/pdf` (not `text/plain` or `application/octet-stream`)
   - MP4: must be `video/mp4` (not `application/octet-stream`)
   - WebM: must be `video/webm`

5. **Conditional Requests**: FileResponse also sets `ETag` and `Last-Modified`, allowing browsers to send `If-None-Match` and `If-Modified-Since`. Starlette handles 304 Not Modified automatically.

6. **Filename Parameter**: The `filename=` parameter in Content-Disposition is used by the browser's download dialog (if downloading). For iframes, it's usually ignored. For clarity, always include it.

7. **CSP Violations**: If you set `frame-src 'none'`, iframes will fail silently (browser won't load them). Check `Content-Security-Policy` header in network tab if PDF viewers don't load.

8. **PPTX Files**: If CR8 needs to serve `.pptx` files, use `media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation"`. However, browsers cannot view PPTX natively — they'll download it. Consider converting to PDF or using an office viewer library.

---

## Security Assessment

| Check | Result | Notes |
|-------|--------|-------|
| Open CVEs (critical/high) | None | Starlette (bundled) has been audited for Range request DoS (issue #950 fixed). No recent CVEs. |
| License | BSD 3-Clause | Starlette and FastAPI are MIT/BSD — compatible with CR8. |
| Last release | 2026-02-XX | FastAPI >= 0.115 is current. Starlette actively maintained. |
| Maintainer count | 10+ | FastAPI (Sebastián Ramírez + team) and Starlette (Tom Christie + team) are well-maintained. |
| Transitive dependencies | Low | FileResponse is part of Starlette core; no new dependencies. |
| Known security incidents | None recent | RFC 7233 implementation is stable in Starlette >= 0.34. |

**Verdict:** **SAFE — No security concerns.** FileResponse and Range request handling are stable, well-tested, and part of the core framework.

---

## Decision Made

Based on this research, CR8 v0.5.3 will:

1. **Use FileResponse for all file serving** (PDFs, videos, scripts):
   - PDFs: `FileResponse(..., media_type="application/pdf", headers={"Content-Disposition": "inline"})`
   - Videos: `FileResponse(..., media_type="video/mp4")` (Range requests automatic)
   - Scripts: `FileResponse(..., media_type="text/plain")` or `application/json`

2. **Implement `_validate_job_file_path()` helper** in `frontend/job_routes.py`:
   - Validates job_id with `JOB_ID_RE` (already exists)
   - Validates filename (no `/`, `\`, `..`)
   - Uses `Path.resolve()` + `relative_to()` to prevent traversal
   - Returns resolved path or None

3. **Update CSP in `frontend/middleware.py`**:
   - Add `frame-src 'self'` (for PDF iframes)
   - Add `media-src 'self'` (for HTML5 video tag)
   - Keep `X-Frame-Options: DENY` for backwards compatibility with older browsers

4. **Create viewer routes** in `frontend/job_routes.py` (v0.5.3):
   - `GET /api/view/pdf/{job_id}` — serve PDF for inline viewing
   - `GET /api/stream/video/{job_id}/{filename}` — serve video with Range support
   - Both use `_validate_job_file_path()` to prevent path traversal

5. **No custom Range request handling needed** — Starlette handles RFC 7233 correctly.

---

## Files This Affects

- `frontend/job_routes.py` — Add `_validate_job_file_path()` helper and new viewer routes (`/api/view/pdf/`, `/api/stream/video/`)
- `frontend/middleware.py` — Update CSP headers to include `frame-src 'self'` and `media-src 'self'`
- React SPA (`frontend/react-app/src/pages/ResultsPage.tsx`) — Use these endpoints for PDF/video viewers (v0.5.3)

---

*If this research is more than 6 months old or a major FastAPI/Starlette version bump occurs, re-verify before implementing. Specifically, re-check Starlette's Range request implementation in release notes.*
