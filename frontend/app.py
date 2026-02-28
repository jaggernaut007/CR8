"""FastAPI frontend for the CR8 Learning Pipeline.

Provides a single-page web UI for uploading curriculum PDFs, launching
the 3-agent pipeline in a background thread, polling for real-time
progress, and downloading generated artifacts (PDF, PPT, scripts, videos).
"""

import asyncio
import os
import re
import secrets
import sys
import threading
import time
import uuid
import zipfile
from contextlib import asynccontextmanager

import bcrypt
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Add project root to path so backend imports work
PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, PROJECT_ROOT)

from backend.run_pipeline import run_job  # noqa: E402

UPLOAD_DIR = os.path.join(PROJECT_ROOT, "uploads")
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")

# ---------------------------------------------------------------------------
# Auth — password hashing
# ---------------------------------------------------------------------------

# bcrypt hash computed once at startup. Plaintext is used only here at import
# time and not retained after this line executes.
_PASSWORD_HASH: bytes = bcrypt.hashpw(b"CR8-AI", bcrypt.gensalt())

# ---------------------------------------------------------------------------
# Auth — session store (token -> expiry Unix timestamp)
# ---------------------------------------------------------------------------

_sessions: dict[str, float] = {}
_sessions_lock = threading.Lock()
SESSION_TTL = 8 * 3600  # 8 hours

# ---------------------------------------------------------------------------
# Auth — rate limiter (IP -> list of failed-attempt timestamps)
# ---------------------------------------------------------------------------

_failed_attempts: dict[str, list[float]] = {}
_failed_attempts_lock = threading.Lock()
MAX_ATTEMPTS = 5
LOCKOUT_WINDOW = 900.0  # 15 minutes

# ---------------------------------------------------------------------------
# Auth — constants
# ---------------------------------------------------------------------------

_PUBLIC_PATHS = frozenset({"/login", "/api/auth/login", "/health"})
JOB_ID_RE = re.compile(r"^[a-f0-9]{8}$")
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB
# Set COOKIE_SECURE=false in .env for local HTTP development; defaults to True for production HTTPS.
COOKIE_SECURE = os.environ.get("COOKIE_SECURE", "true").lower() != "false"


# ---------------------------------------------------------------------------
# Auth — session helpers
# ---------------------------------------------------------------------------

def _create_session() -> str:
    """Create a 256-bit cryptographically random session token and store it."""
    token = secrets.token_hex(32)
    expiry = time.time() + SESSION_TTL
    with _sessions_lock:
        _sessions[token] = expiry
        # Evict expired sessions to prevent unbounded memory growth
        now = time.time()
        for t in [k for k, exp in _sessions.items() if exp < now]:
            del _sessions[t]
    return token


def _is_valid_session(token: str | None) -> bool:
    """Return True only if the token exists server-side and has not expired."""
    if not token:
        return False
    with _sessions_lock:
        expiry = _sessions.get(token)
        if expiry is None:
            return False
        if time.time() > expiry:
            del _sessions[token]
            return False
        return True


def _invalidate_session(token: str) -> None:
    with _sessions_lock:
        _sessions.pop(token, None)


# ---------------------------------------------------------------------------
# Auth — rate limiter helpers
# ---------------------------------------------------------------------------

def _check_rate_limit(ip: str) -> bool:
    """Return True if this IP is still allowed to attempt login."""
    now = time.time()
    with _failed_attempts_lock:
        attempts = [t for t in _failed_attempts.get(ip, []) if now - t < LOCKOUT_WINDOW]
        _failed_attempts[ip] = attempts
        return len(attempts) < MAX_ATTEMPTS


def _record_failed_attempt(ip: str) -> None:
    now = time.time()
    with _failed_attempts_lock:
        attempts = [t for t in _failed_attempts.get(ip, []) if now - t < LOCKOUT_WINDOW]
        attempts.append(now)
        _failed_attempts[ip] = attempts


# ---------------------------------------------------------------------------
# Auth — middleware (registered LAST = outermost = runs before all routing)
# ---------------------------------------------------------------------------

class _AuthMiddleware(BaseHTTPMiddleware):
    """Block every request that lacks a valid session, except public paths."""

    async def dispatch(self, request: Request, call_next):
        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)

        if _is_valid_session(request.cookies.get("cr8_session")):
            return await call_next(request)

        # Not authenticated
        if request.url.path.startswith("/api/"):
            return JSONResponse({"error": "Authentication required"}, status_code=401)
        return RedirectResponse(url="/login", status_code=302)


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    yield


app = FastAPI(title="CR8 Learning Pipeline", lifespan=lifespan)

# Middleware order: last added = outermost (runs first on every request).
# _AuthMiddleware must be outermost so it intercepts before any routing occurs.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(_AuthMiddleware)

# In-memory job registry: job_id -> ProgressCapture
jobs: dict[str, "ProgressCapture"] = {}


# ---------------------------------------------------------------------------
# Progress capture
# ---------------------------------------------------------------------------

class ProgressCapture:
    """Captures stdout from the pipeline thread and parses progress."""

    STAGE_WEIGHTS = {
        "Ingest": 15,
        "Research": 50,
        "Generate": 25,
        "Script": 8,
        "Video": 2,
    }

    def __init__(self):
        self.logs: list[str] = []
        self.current_stage = "starting"
        self.percent = 0
        self.start_time = time.time()
        self.status = "running"  # running | complete | error
        self.error: str | None = None
        self.result: dict | None = None
        self._lock = threading.Lock()
        self._original_stdout = sys.stdout

    # Called by print() when stdout is redirected
    def write(self, text: str):
        self._original_stdout.write(text)  # tee to console
        with self._lock:
            for line in text.strip().split("\n"):
                line = line.strip()
                if line:
                    self.logs.append(line)
                    self._parse_line(line)

    def flush(self):
        self._original_stdout.flush()

    def _parse_line(self, line: str):
        # Match "[Research] Topic 3/8: ..." or "[Generate] Module 3/8: ..."
        topic_match = re.match(r"\[(\w+)\]\s+(?:Topic|Module)\s+(\d+)/(\d+)", line)
        if topic_match:
            stage = topic_match.group(1)
            current = int(topic_match.group(2))
            total = int(topic_match.group(3))
            sub_progress = current / total
            cumulative = 0
            for s, w in self.STAGE_WEIGHTS.items():
                if s == stage:
                    cumulative += int(w * sub_progress)
                    break
                cumulative += w
            self.percent = min(cumulative, 99)
            self.current_stage = stage
            return

        # Match generic "[Ingest] ..." lines for stage transitions
        stage_match = re.match(r"\[(\w+)\]", line)
        if stage_match:
            stage = stage_match.group(1)
            if stage in self.STAGE_WEIGHTS and stage != self.current_stage:
                self.current_stage = stage
                cumulative = 0
                for s, w in self.STAGE_WEIGHTS.items():
                    if s == stage:
                        break
                    cumulative += w
                self.percent = min(cumulative, 99)

    def get_state(self) -> dict:
        with self._lock:
            state = {
                "status": self.status,
                "stage": self.current_stage,
                "percent": self.percent,
                "logs": self.logs[-30:],
                "elapsed": round(time.time() - self.start_time, 1),
            }
            if self.status == "complete" and self.result:
                state["files"] = _collect_output_files(self.result)
            if self.status == "error":
                state["error"] = self.error
            return state


# ---------------------------------------------------------------------------
# Background pipeline runner
# ---------------------------------------------------------------------------

def _run_pipeline_sync(file_paths: list[str], formats: list[str], capture: ProgressCapture):
    """Runs the pipeline with stdout redirected to capture."""
    old_stdout = sys.stdout
    sys.stdout = capture  # type: ignore[assignment]
    try:
        result = run_job(file_paths, formats)
        with capture._lock:
            capture.result = result
            capture.percent = 100
            capture.status = "complete"
    except Exception as e:
        import traceback
        with capture._lock:
            capture.status = "error"
            capture.error = str(e)
        traceback.print_exc(file=old_stdout)
    finally:
        sys.stdout = old_stdout


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _collect_output_files(result: dict) -> list[dict]:
    files = []
    pdf_path = result.get("pdf_path", "")
    if pdf_path and os.path.exists(pdf_path):
        files.append({
            "name": os.path.basename(pdf_path),
            "type": "pdf",
            "size": os.path.getsize(pdf_path),
        })
    ppt_path = result.get("ppt_path", "")
    if ppt_path and os.path.exists(ppt_path):
        files.append({
            "name": os.path.basename(ppt_path),
            "type": "ppt",
            "size": os.path.getsize(ppt_path),
        })
    video_dir = result.get("video_dir", "")
    if video_dir:
        scripts_dir = os.path.join(video_dir, "scripts")
        if os.path.isdir(scripts_dir) and os.listdir(scripts_dir):
            files.append({"name": "video_scripts.zip", "type": "scripts", "size": 0})
        mp4s = [f for f in os.listdir(video_dir) if f.endswith(".mp4")] if os.path.isdir(video_dir) else []
        if mp4s:
            files.append({"name": "videos.zip", "type": "videos", "size": 0})
    return files


def _zip_directory(dir_path: str, zip_path: str, extension: str | None = None):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(dir_path):
            for f in files:
                if extension and not f.endswith(extension):
                    continue
                filepath = os.path.join(root, f)
                arcname = os.path.relpath(filepath, dir_path)
                zf.write(filepath, arcname)


# ---------------------------------------------------------------------------
# Health check (public — no auth required)
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    """Health check endpoint for Cloud Run readiness probes."""
    active_jobs = sum(1 for j in jobs.values() if j.status == "running")
    return {"status": "ok", "active_jobs": active_jobs}


# ---------------------------------------------------------------------------
# Auth routes (public)
# ---------------------------------------------------------------------------

@app.get("/login", response_class=HTMLResponse)
async def login_page():
    """Serve the login page."""
    html_path = os.path.join(TEMPLATE_DIR, "login.html")
    with open(html_path) as f:
        return HTMLResponse(content=f.read())


@app.post("/api/auth/login")
async def login(request: Request, body: dict):
    """Validate password and issue a session cookie."""
    ip = request.client.host if request.client else "unknown"

    if not _check_rate_limit(ip):
        return JSONResponse(
            {"error": "Too many failed attempts. Try again in 15 minutes."},
            status_code=429,
        )

    password = body.get("password", "")
    if not password or not bcrypt.checkpw(password.encode(), _PASSWORD_HASH):
        _record_failed_attempt(ip)
        return JSONResponse({"error": "Incorrect password. Please try again."}, status_code=401)

    token = _create_session()
    response = JSONResponse({"status": "ok"})
    response.set_cookie(
        key="cr8_session",
        value=token,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        max_age=SESSION_TTL,
    )
    return response


@app.post("/api/auth/logout")
async def logout(request: Request):
    """Invalidate the current session and clear the cookie."""
    token = request.cookies.get("cr8_session")
    if token:
        _invalidate_session(token)
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("cr8_session")
    return response


# ---------------------------------------------------------------------------
# Protected routes
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the single-page HTML frontend."""
    html_path = os.path.join(TEMPLATE_DIR, "index.html")
    with open(html_path) as f:
        return HTMLResponse(content=f.read())


@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    """Upload a curriculum PDF and receive a job ID.

    Validates file extension, magic bytes, and size before saving.
    """
    # Extension check
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        return JSONResponse({"error": "Please upload a PDF file"}, status_code=400)

    content = await file.read()

    # File size limit
    if len(content) > MAX_UPLOAD_BYTES:
        return JSONResponse({"error": "File too large (max 20 MB)"}, status_code=413)

    # Magic bytes — verify it is actually a PDF, not just named .pdf
    if not content.startswith(b"%PDF-"):
        return JSONResponse({"error": "File is not a valid PDF"}, status_code=400)

    # Sanitize filename to prevent path traversal
    safe_filename = os.path.basename(file.filename)
    safe_filename = re.sub(r"[^\w\-.]", "_", safe_filename) or "upload.pdf"

    job_id = uuid.uuid4().hex[:8]
    job_dir = os.path.join(UPLOAD_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    filepath = os.path.join(job_dir, safe_filename)
    with open(filepath, "wb") as f:
        f.write(content)

    return {"job_id": job_id, "filename": safe_filename}


@app.post("/api/start")
async def start(body: dict):
    """Start the pipeline for a previously uploaded job."""
    job_id = body.get("job_id")
    formats = body.get("formats", ["pdf"])

    if not job_id or not JOB_ID_RE.match(str(job_id)):
        return JSONResponse({"error": "Invalid job_id"}, status_code=400)

    # Reject if a job is already running
    for jid, cap in jobs.items():
        if cap.status == "running":
            return JSONResponse(
                {"error": f"A job is already running (job {jid}). Please wait."},
                status_code=409,
            )

    job_dir = os.path.join(UPLOAD_DIR, job_id)
    if not os.path.exists(job_dir):
        return JSONResponse({"error": "Job not found. Upload a file first."}, status_code=404)

    pdf_files = [os.path.join(job_dir, f) for f in os.listdir(job_dir) if f.lower().endswith(".pdf")]
    if not pdf_files:
        return JSONResponse({"error": "No PDF found for this job"}, status_code=404)

    capture = ProgressCapture()
    jobs[job_id] = capture

    asyncio.get_running_loop().run_in_executor(
        None, _run_pipeline_sync, pdf_files, formats, capture
    )

    return {"status": "running"}


@app.get("/api/progress/{job_id}")
async def progress(job_id: str):
    """Poll the current progress of a running pipeline job."""
    if not JOB_ID_RE.match(job_id):
        return JSONResponse({"error": "Invalid job_id"}, status_code=400)

    capture = jobs.get(job_id)
    if not capture:
        return JSONResponse({"error": "Job not found"}, status_code=404)
    return capture.get_state()


@app.get("/api/download/{job_id}/{file_type}")
async def download(job_id: str, file_type: str):
    """Download a generated artifact from a completed job."""
    if not JOB_ID_RE.match(job_id):
        return JSONResponse({"error": "Invalid job_id"}, status_code=400)

    capture = jobs.get(job_id)
    if not capture or not capture.result:
        return JSONResponse({"error": "Job not found or not complete"}, status_code=404)

    result = capture.result

    if file_type == "pdf":
        pdf_path = result.get("pdf_path", "")
        if pdf_path and os.path.exists(pdf_path):
            return FileResponse(pdf_path, filename=os.path.basename(pdf_path))

    elif file_type == "ppt":
        ppt_path = result.get("ppt_path", "")
        if ppt_path and os.path.exists(ppt_path):
            return FileResponse(ppt_path, filename=os.path.basename(ppt_path))

    elif file_type == "scripts":
        video_dir = result.get("video_dir", "")
        scripts_dir = os.path.join(video_dir, "scripts")
        if os.path.isdir(scripts_dir):
            zip_path = scripts_dir.rstrip("/") + ".zip"
            _zip_directory(scripts_dir, zip_path)
            return FileResponse(zip_path, filename="video_scripts.zip")

    elif file_type == "videos":
        video_dir = result.get("video_dir", "")
        if os.path.isdir(video_dir):
            zip_path = video_dir.rstrip("/") + "_videos.zip"
            _zip_directory(video_dir, zip_path, extension=".mp4")
            return FileResponse(zip_path, filename="videos.zip")

    return JSONResponse({"error": "File not found"}, status_code=404)


if __name__ == "__main__":
    import uvicorn
    os.chdir(PROJECT_ROOT)
    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run("frontend.app:app", host="0.0.0.0", port=port, reload=True)
