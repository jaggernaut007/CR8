"""FastAPI frontend for the CR8 Learning Pipeline.

Provides a single-page web UI for uploading curriculum PDFs, launching
the 3-agent pipeline in a background thread, polling for real-time
progress, and downloading generated artifacts (PDF, PPT, scripts, videos).

Route handlers are organized into separate modules:
- ``frontend.auth_routes`` — JWT + legacy session auth
- ``frontend.job_routes`` — upload, start, progress, cancel, download
- ``frontend.quiz_routes`` — quiz stubs (Phase 4)
"""

import glob
import logging
import typing
import os
import re
import shutil
import sys
import threading
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

# Add project root to path so backend imports work
PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, PROJECT_ROOT)

from backend.config import settings  # noqa: E402
from backend.pipeline.state import PipelineCancelledError  # noqa: E402
from backend.run_pipeline import run_job  # noqa: E402
from frontend.auth_routes import router as auth_router  # noqa: E402
from frontend.job_routes import router as job_router  # noqa: E402
from frontend.middleware import AuthMiddleware, SecurityHeadersMiddleware  # noqa: E402
from frontend.quiz_routes import router as quiz_router  # noqa: E402
from frontend.view_routes import router as view_router  # noqa: E402

logger = logging.getLogger(__name__)

UPLOAD_DIR = os.path.join(PROJECT_ROOT, "uploads")
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")


# ---------------------------------------------------------------------------
# Progress capture
# ---------------------------------------------------------------------------


class ProgressCapture:
    """Captures stdout from the pipeline thread and parses progress.

    Works by replacing ``sys.stdout`` during pipeline execution.  The
    pipeline agents print structured messages like ``[Research] Topic 3/8: ...``
    which ``_parse_line()`` parses into stage + sub-progress.  This is why
    pipeline agents use ``print()`` rather than ``logging`` — the progress
    messages must flow through stdout to be captured here.

    Cancellation: ``write()`` checks ``_cancel_at_boundary`` on every print
    and raises ``PipelineCancelledError`` at stage transitions to ensure
    graceful cleanup (no mid-LLM-call interruption).
    """

    # Approximate relative effort per stage (must sum to 100).
    STAGE_WEIGHTS: typing.ClassVar[dict[str, int]] = {
        "Ingest": 10,
        "Research": 35,
        "Generate": 20,
        "Script": 10,
        "Video": 25,
    }

    # Expected wall-clock seconds per stage (video-enabled, 5-topic run).
    STAGE_TIME_BUDGETS: typing.ClassVar[dict[str, int]] = {
        "Ingest": 51,
        "Research": 150,
        "Generate": 140,
        "Script": 14,
        "Video": 1690,
    }

    def __init__(self):
        self.logs: list[str] = []
        self.current_stage = "starting"
        self.percent = 0
        self.start_time = time.time()
        self.stage_start_time = time.time()
        self.status = "running"  # running | complete | error | cancelled
        self.error: str | None = None
        self.warnings: list[str] = []
        self.result: dict | None = None
        self.formats: list[str] = []
        self._lock = threading.Lock()
        self._original_stdout = sys.stdout
        self.cancel_requested = False
        self._cancel_at_boundary = False
        self.video_job_id: str | None = None
        self.gpu_progress: dict | None = None

    def is_cancelled(self) -> bool:
        """Check if cancellation has been requested."""
        with self._lock:
            return self.cancel_requested

    def request_cancel(self) -> None:
        """Request cancellation of this pipeline run."""
        with self._lock:
            self.cancel_requested = True

    def write(self, text: str):
        """Intercept stdout writes from the pipeline thread."""
        self._original_stdout.write(text)  # tee to console
        should_cancel = False
        with self._lock:
            for line in text.strip().split("\n"):
                line = line.strip()
                if line:
                    self.logs.append(line)
                    self._parse_line(line)
            should_cancel = self._cancel_at_boundary
        if should_cancel:
            raise PipelineCancelledError("Pipeline cancelled by user")

    def flush(self):
        """Flush the underlying stdout."""
        self._original_stdout.flush()

    def _cumulative_weight(self, target_stage: str, fraction: float = 0.0) -> int:
        """Calculate cumulative progress weight up to (and partially through) a stage."""
        cumulative = 0
        for s, w in self.STAGE_WEIGHTS.items():
            if s == target_stage:
                cumulative += int(w * fraction)
                break
            cumulative += w
        return min(cumulative, 99)

    def _parse_topic_progress(self, line: str) -> bool:
        """Parse "[Stage] Topic X/Y" or "[Stage] Module X/Y" lines."""
        topic_match = re.match(r"\[(\w+)\]\s+(?:Topic|Module)\s+(\d+)/(\d+)", line)
        if not topic_match:
            return False
        stage = topic_match.group(1)
        current = int(topic_match.group(2))
        total = int(topic_match.group(3))
        self.percent = self._cumulative_weight(stage, current / total)
        self.current_stage = stage
        return True

    def _parse_gpu_line(self, line: str) -> bool:
        """Parse GPU-related progress lines ([Video] GPU_*)."""
        gpu_id_match = re.match(r"\[Video\] GPU_JOB_ID: (.+)", line)
        if gpu_id_match:
            self.video_job_id = gpu_id_match.group(1).strip()
            return True

        compose_match = re.match(r"\[Video\] GPU_COMPOSE: (\d+)/(\d+)", line)
        if compose_match:
            if self.gpu_progress is None:
                self.gpu_progress = {}
            self.gpu_progress["completed_videos"] = int(compose_match.group(1))
            self.gpu_progress["total_videos"] = int(compose_match.group(2))
            return True

        tts_match = re.match(r"\[Video\] GPU_TTS: (\d+)/(\d+)", line)
        if tts_match:
            if self.gpu_progress is None:
                self.gpu_progress = {}
            self.gpu_progress["current_topic"] = int(tts_match.group(1))
            self.gpu_progress["total_topics"] = int(tts_match.group(2))
            return True

        time_match = re.match(r"\[Video\] GPU_TIME: elapsed=(\d+) eta=(\d+|\?)", line)
        if time_match:
            if self.gpu_progress is None:
                self.gpu_progress = {}
            self.gpu_progress["elapsed_s"] = int(time_match.group(1))
            eta_val = time_match.group(2)
            self.gpu_progress["eta_s"] = int(eta_val) if eta_val != "?" else None
            return True

        return False

    def _parse_line(self, line: str):
        """Parse a single log line for progress information."""
        if self._parse_topic_progress(line):
            return

        if line.startswith(("[Video] ERROR:", "[Video] WARNING:")):
            self.warnings.append(line)

        if self._parse_gpu_line(line):
            return

        stage_match = re.match(r"\[(\w+)\]", line)
        if stage_match:
            stage = stage_match.group(1)
            if stage in self.STAGE_WEIGHTS and stage != self.current_stage:
                if self.cancel_requested:
                    self._cancel_at_boundary = True
                self.current_stage = stage
                self.stage_start_time = time.time()
                self.percent = self._cumulative_weight(stage)

    def get_state(self) -> dict:
        """Return the current progress state as a JSON-serializable dict."""
        from frontend.job_routes import _collect_output_files

        with self._lock:
            effective_status = self.status
            if self.cancel_requested and self.status == "running":
                effective_status = "cancelling"
            state = {
                "status": effective_status,
                "stage": self.current_stage,
                "percent": self.percent,
                "logs": self.logs[-30:],
                "elapsed": round(time.time() - self.start_time, 1),
                "stage_elapsed": round(time.time() - self.stage_start_time, 1),
                "stage_time_budgets": self.STAGE_TIME_BUDGETS,
                "has_video": "video" in self.formats,
            }
            if self.status in ("complete", "cancelled") and self.result:
                state["files"] = _collect_output_files(self.result)
            if self.status == "error":
                state["error"] = self.error
            if self.status == "cancelled":
                state["error"] = self.error or "Cancelled by user"
            if self.warnings:
                state["warnings"] = self.warnings
            if self.gpu_progress:
                state["gpu_progress"] = self.gpu_progress
            return state


# ---------------------------------------------------------------------------
# Background pipeline runner
# ---------------------------------------------------------------------------

def _cleanup_partial_audio(result: dict) -> None:
    """Remove ``_audio_*`` temp directories left by cancelled video builds."""
    video_dir = result.get("video_dir") if result else None
    if not video_dir or not os.path.isdir(video_dir):
        return
    import contextlib
    for audio_dir in glob.glob(os.path.join(video_dir, "_audio_*")):
        with contextlib.suppress(OSError):
            shutil.rmtree(audio_dir)


def _handle_pipeline_result(capture: ProgressCapture, result: dict) -> None:
    """Store a successful pipeline result in the capture."""
    with capture._lock:
        capture.result = result
        capture.percent = 100
        capture.status = "complete"


def _handle_pipeline_error(capture: ProgressCapture, error: Exception, old_stdout) -> None:
    """Store an error in the capture and print traceback."""
    import traceback
    with capture._lock:
        capture.status = "error"
        capture.error = str(error)
    traceback.print_exc(file=old_stdout)


def _run_pipeline_sync(file_paths: list[str], formats: list[str], capture: ProgressCapture):
    """Run the pipeline with stdout redirected to capture."""
    capture.formats = formats
    old_stdout = sys.stdout
    sys.stdout = capture  # type: ignore[assignment]
    try:
        result = run_job(file_paths, formats)
        _handle_pipeline_result(capture, result)
    except PipelineCancelledError:
        with capture._lock:
            capture.status = "cancelled"
            capture.error = "Cancelled by user"
            if capture.result is None:
                capture.result = {}
        _cleanup_partial_audio(capture.result)
    except Exception as e:
        _handle_pipeline_error(capture, e, old_stdout)
    finally:
        sys.stdout = old_stdout


# ---------------------------------------------------------------------------
# App lifespan (DB pool init/teardown)
# ---------------------------------------------------------------------------


async def _init_db_pool():
    """Initialize the database pool and run schema if DATABASE_URL is set."""
    if not settings.database_url:
        logger.info("No DATABASE_URL — running without database")
        return None
    try:
        from backend.db.connection import init_pool, run_schema

        pool = await init_pool(settings.database_url)
        await run_schema(pool)
        logger.info("Database pool initialized")

        from backend.services import db_client

        stale_count = await db_client.mark_stale_jobs_as_error(pool)
        if stale_count:
            logger.warning("Marked %d stale jobs as error on startup", stale_count)
        return pool
    except Exception:
        logger.warning("Database connection failed — running without DB", exc_info=True)
        return None


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Initialize resources on startup, clean up on shutdown."""
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    pool = await _init_db_pool()
    application.state.db_pool = pool

    yield

    if pool is not None:
        from backend.db.connection import close_pool

        await close_pool(pool)
        logger.info("Database pool closed")


# ---------------------------------------------------------------------------
# App creation
# ---------------------------------------------------------------------------

app = FastAPI(title="CR8 Learning Pipeline", lifespan=lifespan)

# In-memory job registry: job_id -> ProgressCapture
app.state.jobs = {}

# Parse allowed origins from config
_allowed_origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]

# Middleware order: last added = outermost (runs first).
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(AuthMiddleware)

# Mount route modules
app.include_router(auth_router)
app.include_router(job_router)
app.include_router(quiz_router)
app.include_router(view_router)


# ---------------------------------------------------------------------------
# Health check (public — no auth required)
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    """Health check endpoint for Cloud Run readiness probes."""
    jobs = app.state.jobs
    active_jobs = sum(1 for j in jobs.values() if j.status == "running")
    return {"status": "ok", "active_jobs": active_jobs}


# ---------------------------------------------------------------------------
# Static files + SPA catch-all (React) or legacy Jinja2 fallback
# ---------------------------------------------------------------------------

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
_HAS_REACT_BUILD = os.path.isfile(os.path.join(STATIC_DIR, "index.html"))

if _HAS_REACT_BUILD:
    from fastapi.staticfiles import StaticFiles

    # Serve React static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}", response_class=HTMLResponse)
    async def spa_catch_all(full_path: str):
        """Serve React SPA for all non-API routes."""
        index_path = os.path.join(STATIC_DIR, "index.html")
        with open(index_path) as f:
            return HTMLResponse(content=f.read())
else:
    # Legacy Jinja2 templates (kept during transition to React)
    @app.get("/login", response_class=HTMLResponse)
    async def login_page():
        """Serve the login page."""
        html_path = os.path.join(TEMPLATE_DIR, "login.html")
        with open(html_path) as f:
            return HTMLResponse(content=f.read())

    @app.get("/", response_class=HTMLResponse)
    async def index():
        """Serve the single-page HTML frontend."""
        html_path = os.path.join(TEMPLATE_DIR, "index.html")
        with open(html_path) as f:
            return HTMLResponse(content=f.read())


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    os.chdir(PROJECT_ROOT)
    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run("frontend.app:app", host="0.0.0.0", port=port, reload=True)
