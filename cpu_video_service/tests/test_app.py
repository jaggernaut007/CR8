"""Tests for CPU video service FastAPI endpoints."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    """Create a test client with mocked worker."""
    with patch("cpu_video_service.app.run_video_job"):
        from cpu_video_service.app import app, _active_lock
        import cpu_video_service.app as app_module

        with _active_lock:
            app_module._active_count = 0
        yield TestClient(app)


class TestHealth:
    def test_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    def test_returns_cpu_type(self, client):
        resp = client.get("/health")
        assert resp.json()["type"] == "cpu-video"


class TestCreateVideoJob:
    def test_returns_202_with_job_id(self, client):
        resp = client.post(
            "/api/v1/video-jobs",
            json={"job_id": "abc", "gcs_prefix": "gs://bucket/abc"},
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["video_job_id"].startswith("vj_abc_")
        assert data["status"] == "accepted"

    def test_rejects_when_max_concurrent_reached(self, client):
        import cpu_video_service.app as app_module

        with app_module._active_lock:
            app_module._active_count = 1

        with patch("cpu_video_service.config.cpu_video_settings") as mock_settings:
            mock_settings.max_concurrent_jobs = 1
            resp = client.post(
                "/api/v1/video-jobs",
                json={"job_id": "x", "gcs_prefix": "gs://b/x"},
            )
            assert resp.status_code == 429

    def test_missing_fields_returns_422(self, client):
        resp = client.post("/api/v1/video-jobs", json={"job_id": "abc"})
        assert resp.status_code == 422

    def test_missing_job_id_returns_422(self, client):
        resp = client.post("/api/v1/video-jobs", json={"gcs_prefix": "gs://b/abc"})
        assert resp.status_code == 422

    def test_job_pre_registered_before_thread_starts(self, client):
        """The job must be findable immediately after the POST returns (before thread runs)."""
        from cpu_video_service.worker import get_job

        resp = client.post(
            "/api/v1/video-jobs",
            json={"job_id": "precheck", "gcs_prefix": "gs://bucket/precheck"},
        )
        assert resp.status_code == 202
        video_job_id = resp.json()["video_job_id"]

        job = get_job(video_job_id)
        assert job is not None
        assert job["status"] == "accepted"

    def test_video_job_id_contains_uuid_suffix(self, client):
        """The generated ID should be vj_{job_id}_{6-char hex suffix}."""
        resp = client.post(
            "/api/v1/video-jobs",
            json={"job_id": "mytest", "gcs_prefix": "gs://b/mytest"},
        )
        assert resp.status_code == 202
        vid = resp.json()["video_job_id"]
        parts = vid.split("_")
        # vj + mytest + 6-char hex = at least 3 underscore-separated tokens
        assert parts[0] == "vj"
        assert parts[1] == "mytest"
        assert len(parts[2]) == 6


class TestGetVideoJobStatus:
    def test_returns_job_when_exists(self, client):
        with patch("cpu_video_service.app.get_job") as mock_get:
            mock_get.return_value = {
                "video_job_id": "vj_1",
                "status": "tts",
                "progress": {"phase": "tts", "percent": 30},
            }
            resp = client.get("/api/v1/video-jobs/vj_1")
            assert resp.status_code == 200
            assert resp.json()["status"] == "tts"

    def test_returns_404_for_unknown_job(self, client):
        with patch("cpu_video_service.app.get_job", return_value=None):
            resp = client.get("/api/v1/video-jobs/nonexistent")
            assert resp.status_code == 404

    def test_returns_complete_with_output_paths(self, client):
        with patch("cpu_video_service.app.get_job") as mock_get:
            mock_get.return_value = {
                "video_job_id": "vj_2",
                "status": "complete",
                "progress": {"phase": "complete", "percent": 100},
                "output_paths": ["01_Topic.mp4", "02_Topic.mp4"],
            }
            resp = client.get("/api/v1/video-jobs/vj_2")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "complete"
            assert len(data["output_paths"]) == 2

    def test_returns_error_with_message(self, client):
        with patch("cpu_video_service.app.get_job") as mock_get:
            mock_get.return_value = {
                "video_job_id": "vj_3",
                "status": "error",
                "error": "TTS failed",
            }
            resp = client.get("/api/v1/video-jobs/vj_3")
            assert resp.status_code == 200
            assert resp.json()["error"] == "TTS failed"

    def test_returns_warnings_field_when_present(self, client):
        with patch("cpu_video_service.app.get_job") as mock_get:
            mock_get.return_value = {
                "video_job_id": "vj_warn",
                "status": "complete",
                "progress": {"phase": "complete", "percent": 100},
                "output_paths": ["01.mp4"],
                "warnings": ["'Topic B' TTS failed: OOM"],
            }
            resp = client.get("/api/v1/video-jobs/vj_warn")
            data = resp.json()
            assert data["warnings"] == ["'Topic B' TTS failed: OOM"]


class TestCancelVideoJob:
    def test_cancel_returns_cancelling(self, client):
        with patch("cpu_video_service.app.get_job") as mock_get:
            mock_get.return_value = {"video_job_id": "vj_c", "status": "tts"}
            with patch("cpu_video_service.app.cancel_job", return_value=True):
                resp = client.post("/api/v1/video-jobs/vj_c/cancel")
                assert resp.status_code == 200
                assert resp.json()["status"] == "cancelling"

    def test_cancel_returns_404_for_unknown(self, client):
        with patch("cpu_video_service.app.get_job", return_value=None):
            resp = client.post("/api/v1/video-jobs/nonexistent/cancel")
            assert resp.status_code == 404

    def test_cancel_already_complete_returns_status(self, client):
        with patch("cpu_video_service.app.get_job") as mock_get:
            mock_get.return_value = {"video_job_id": "vj_done", "status": "complete"}
            resp = client.post("/api/v1/video-jobs/vj_done/cancel")
            assert resp.status_code == 200
            assert resp.json()["status"] == "complete"

    def test_cancel_already_error_returns_status(self, client):
        """A job in 'error' state is treated as already finished; cancel returns its status."""
        with patch("cpu_video_service.app.get_job") as mock_get:
            mock_get.return_value = {"video_job_id": "vj_err", "status": "error"}
            resp = client.post("/api/v1/video-jobs/vj_err/cancel")
            assert resp.status_code == 200
            assert resp.json()["status"] == "error"

    def test_cancel_already_cancelled_returns_status(self, client):
        """A job in 'cancelled' state is treated as already finished."""
        with patch("cpu_video_service.app.get_job") as mock_get:
            mock_get.return_value = {"video_job_id": "vj_c2", "status": "cancelled"}
            resp = client.post("/api/v1/video-jobs/vj_c2/cancel")
            assert resp.status_code == 200
            assert resp.json()["status"] == "cancelled"

    def test_cancel_returns_409_when_cancel_job_returns_false(self, client):
        """If cancel_job() returns False, the endpoint responds with HTTP 409."""
        with patch("cpu_video_service.app.get_job") as mock_get:
            mock_get.return_value = {"video_job_id": "vj_no_cancel", "status": "tts"}
            with patch("cpu_video_service.app.cancel_job", return_value=False):
                resp = client.post("/api/v1/video-jobs/vj_no_cancel/cancel")
                assert resp.status_code == 409
