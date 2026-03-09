"""Tests for new/changed behaviour in frontend/job_routes.py (added this session).

Covers:
- GET /api/jobs/{job_id} — requires auth (401 without), ownership check (404 for wrong owner)
- POST /api/start — validates formats list (422 for invalid values)
- GET /api/jobs — limit parameter is capped at 100

Notes on patch paths:
- job_routes.py does lazy ``from backend.services import db_client as dbc`` inside each
  route function. The module path to patch is therefore ``backend.services.db_client``.
"""

from __future__ import annotations

import secrets
import time
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from frontend.app import app
from frontend.middleware import _failed_attempts, _sessions
from backend.services import auth_service


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clean_state():
    """Clear sessions, rate-limit state, and job registry before and after each test."""
    _sessions.clear()
    _failed_attempts.clear()
    app.state.jobs.clear()
    yield
    _sessions.clear()
    _failed_attempts.clear()
    app.state.jobs.clear()


@pytest.fixture
def authed_client():
    """TestClient with a pre-seeded valid legacy session cookie."""
    c = TestClient(app, raise_server_exceptions=False)
    token = secrets.token_hex(32)
    _sessions[token] = time.time() + 3600
    c.cookies.set("cr8_session", token)
    yield c
    _sessions.pop(token, None)


@pytest.fixture
def jwt_client():
    """TestClient authenticated with a real JWT Bearer token. Returns (client, user_id)."""
    user_id = str(uuid.uuid4())
    email = "owner@example.com"
    token = auth_service.create_access_token(user_id, email, "user")
    c = TestClient(app, raise_server_exceptions=False)
    c.headers.update({"Authorization": f"Bearer {token}"})
    return c, user_id


@pytest.fixture
def unauthenticated_client():
    """TestClient with no auth credentials."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def mock_db_pool():
    """Attach a sentinel db_pool to app.state, yield, then remove."""
    sentinel = object()
    app.state.db_pool = sentinel
    yield sentinel
    if hasattr(app.state, "db_pool"):
        del app.state.db_pool


# ---------------------------------------------------------------------------
# GET /api/jobs/{job_id} — auth + ownership
# ---------------------------------------------------------------------------


class TestGetJobById:
    """Covers the new auth + ownership check added to GET /api/jobs/{job_id}."""

    def test_get_job_without_auth_returns_401(self, unauthenticated_client, mock_db_pool):
        """Unauthenticated request must receive 401."""
        resp = unauthenticated_client.get("/api/jobs/some-job-uuid")
        assert resp.status_code == 401

    def test_get_job_without_db_returns_503(self, authed_client):
        """When no DB pool is configured, must return 503."""
        if hasattr(app.state, "db_pool"):
            del app.state.db_pool
        resp = authed_client.get("/api/jobs/some-job-uuid")
        assert resp.status_code == 503

    def test_get_job_returns_404_when_job_not_found(self, jwt_client, mock_db_pool):
        """A job that doesn't exist in the DB must return 404."""
        client, user_id = jwt_client
        with patch("backend.services.db_client.get_job", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            resp = client.get("/api/jobs/nonexistent-id")
        assert resp.status_code == 404

    def test_get_job_returns_404_for_wrong_owner(self, jwt_client, mock_db_pool):
        """A job owned by a different user must return 404 (not 403)."""
        client, user_id = jwt_client
        other_user_id = str(uuid.uuid4())
        job = {"id": "job-abc", "user_id": other_user_id, "status": "complete"}
        with patch("backend.services.db_client.get_job", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = job
            resp = client.get("/api/jobs/job-abc")
        assert resp.status_code == 404

    def test_get_job_returns_200_for_correct_owner(self, jwt_client, mock_db_pool):
        """A job owned by the requesting user must be returned with 200."""
        client, user_id = jwt_client
        job = {"id": "job-xyz", "user_id": user_id, "status": "complete"}
        with patch("backend.services.db_client.get_job", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = job
            resp = client.get("/api/jobs/job-xyz")
        assert resp.status_code == 200

    def test_get_job_legacy_session_returns_403(self, authed_client, mock_db_pool):
        """Legacy-session users must receive 403 (JWT required for job lookup)."""
        resp = authed_client.get("/api/jobs/some-job-uuid")
        assert resp.status_code == 403

    def test_get_job_unauthenticated_error_message_has_error_key(
        self, unauthenticated_client, mock_db_pool
    ):
        """401 response must include an error key."""
        resp = unauthenticated_client.get("/api/jobs/some-job-uuid")
        assert "error" in resp.json()

    def test_get_job_wrong_owner_error_message_says_not_found(self, jwt_client, mock_db_pool):
        """Ownership mismatch 404 must include a 'not found' message."""
        client, user_id = jwt_client
        other_user_id = str(uuid.uuid4())
        job = {"id": "job-abc", "user_id": other_user_id, "status": "complete"}
        with patch("backend.services.db_client.get_job", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = job
            resp = client.get("/api/jobs/job-abc")
        assert "not found" in resp.json()["error"].lower()


# ---------------------------------------------------------------------------
# POST /api/start — format validation
# ---------------------------------------------------------------------------


class TestStartFormatValidation:
    """Covers the new format list validation added to POST /api/start."""

    def _make_job_dir(self, tmp_path, job_id: str) -> None:
        """Create a minimal upload directory so the job is 'found'."""
        job_dir = tmp_path / "uploads" / job_id
        job_dir.mkdir(parents=True)
        (job_dir / "lecture.pdf").write_bytes(b"%PDF-1.0 fake")

    def test_start_invalid_format_value_returns_422(self, authed_client, tmp_path):
        """An unrecognised format value must return 422."""
        job_id = "aabbccdd"
        self._make_job_dir(tmp_path, job_id)
        with patch("frontend.job_routes.UPLOAD_DIR", str(tmp_path / "uploads")):
            resp = authed_client.post(
                "/api/start",
                json={"job_id": job_id, "formats": ["pdf", "invalid_format"]},
            )
        assert resp.status_code == 422

    def test_start_formats_not_a_list_returns_422(self, authed_client, tmp_path):
        """When formats is a plain string (not a list), must return 422."""
        job_id = "aabbccdd"
        self._make_job_dir(tmp_path, job_id)
        with patch("frontend.job_routes.UPLOAD_DIR", str(tmp_path / "uploads")):
            resp = authed_client.post(
                "/api/start",
                json={"job_id": job_id, "formats": "pdf"},
            )
        assert resp.status_code == 422

    def test_start_invalid_format_error_message_mentions_allowed(self, authed_client, tmp_path):
        """The 422 response must mention the allowed formats."""
        job_id = "aabbccdd"
        self._make_job_dir(tmp_path, job_id)
        with patch("frontend.job_routes.UPLOAD_DIR", str(tmp_path / "uploads")):
            resp = authed_client.post(
                "/api/start",
                json={"job_id": job_id, "formats": ["bad"]},
            )
        assert resp.status_code == 422
        body = resp.json()["error"].lower()
        assert "allowed" in body

    def test_start_invalid_format_error_message_lists_valid_formats(
        self, authed_client, tmp_path
    ):
        """The 422 error must name the four accepted formats."""
        job_id = "aabbccdd"
        self._make_job_dir(tmp_path, job_id)
        with patch("frontend.job_routes.UPLOAD_DIR", str(tmp_path / "uploads")):
            resp = authed_client.post(
                "/api/start",
                json={"job_id": job_id, "formats": ["unknown"]},
            )
        error_text = resp.json()["error"]
        assert "pdf" in error_text

    def test_start_valid_pdf_format_does_not_return_422(self, authed_client, tmp_path):
        """The 'pdf' format value is valid and must not trigger a 422."""
        job_id = "aabbccdd"
        self._make_job_dir(tmp_path, job_id)
        with (
            patch("frontend.job_routes.UPLOAD_DIR", str(tmp_path / "uploads")),
            patch("frontend.app.ProgressCapture", MagicMock),
            patch("frontend.app._run_pipeline_sync", MagicMock),
            patch("asyncio.get_running_loop") as mock_loop,
        ):
            mock_loop.return_value.run_in_executor = MagicMock()
            resp = authed_client.post(
                "/api/start",
                json={"job_id": job_id, "formats": ["pdf"]},
            )
        assert resp.status_code != 422


# ---------------------------------------------------------------------------
# GET /api/jobs — limit cap at 100
# ---------------------------------------------------------------------------


class TestListJobsLimitCap:
    """Covers the new limit=min(requested, 100) guard added to GET /api/jobs."""

    def test_list_jobs_caps_limit_at_100(self, jwt_client, mock_db_pool):
        """Requesting limit=500 must result in the DB being called with limit<=100."""
        client, user_id = jwt_client
        captured_limits: list[int] = []

        async def fake_list_jobs(pool, uid, limit=20, offset=0):
            captured_limits.append(limit)
            return []

        with patch("backend.services.db_client.list_jobs", side_effect=fake_list_jobs):
            client.get("/api/jobs?limit=500")

        assert len(captured_limits) == 1
        assert captured_limits[0] <= 100

    def test_list_jobs_limit_1000_capped_to_100(self, jwt_client, mock_db_pool):
        """Extreme limit values (1000) must be reduced to exactly 100."""
        client, user_id = jwt_client
        captured_limits: list[int] = []

        async def fake_list_jobs(pool, uid, limit=20, offset=0):
            captured_limits.append(limit)
            return []

        with patch("backend.services.db_client.list_jobs", side_effect=fake_list_jobs):
            client.get("/api/jobs?limit=1000")

        assert captured_limits[0] == 100

    def test_list_jobs_limit_below_100_passes_through(self, jwt_client, mock_db_pool):
        """A limit of 20 must be passed through unchanged."""
        client, user_id = jwt_client
        captured_limits: list[int] = []

        async def fake_list_jobs(pool, uid, limit=20, offset=0):
            captured_limits.append(limit)
            return []

        with patch("backend.services.db_client.list_jobs", side_effect=fake_list_jobs):
            client.get("/api/jobs?limit=20")

        assert captured_limits[0] == 20

    def test_list_jobs_exactly_100_passes_through(self, jwt_client, mock_db_pool):
        """A limit of exactly 100 must not be reduced."""
        client, user_id = jwt_client
        captured_limits: list[int] = []

        async def fake_list_jobs(pool, uid, limit=20, offset=0):
            captured_limits.append(limit)
            return []

        with patch("backend.services.db_client.list_jobs", side_effect=fake_list_jobs):
            client.get("/api/jobs?limit=100")

        assert captured_limits[0] == 100

    def test_list_jobs_without_auth_returns_401(self, unauthenticated_client, mock_db_pool):
        """GET /api/jobs must require authentication."""
        resp = unauthenticated_client.get("/api/jobs")
        assert resp.status_code == 401

    def test_list_jobs_legacy_session_returns_403(self, authed_client, mock_db_pool):
        """Legacy-session users must receive 403 for the job list."""
        resp = authed_client.get("/api/jobs")
        assert resp.status_code == 403

    def test_list_jobs_invalid_limit_returns_400(self, jwt_client, mock_db_pool):
        """A non-numeric limit parameter must return 400."""
        client, user_id = jwt_client
        resp = client.get("/api/jobs?limit=notanumber")
        assert resp.status_code == 400

    def test_list_jobs_no_db_returns_503(self, jwt_client):
        """When no DB pool is configured, GET /api/jobs must return 503."""
        if hasattr(app.state, "db_pool"):
            del app.state.db_pool
        client, user_id = jwt_client
        resp = client.get("/api/jobs")
        assert resp.status_code == 503
