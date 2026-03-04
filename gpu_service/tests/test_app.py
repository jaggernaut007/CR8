"""Tests for GPU video service FastAPI endpoints."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    """Create a test client with mocked worker."""
    with patch("gpu_service.app.run_video_job"):
        from gpu_service.app import app, _active_lock
        import gpu_service.app as app_module

        # Reset active count between tests
        with _active_lock:
            app_module._active_count = 0
        yield TestClient(app)


class TestHealth:
    def test_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    def test_detailed_returns_gpu_info(self, client):
        resp = client.get("/health/detailed")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "gpu" in data
        assert "ffmpeg_encoder" in data


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
        import gpu_service.app as app_module

        with app_module._active_lock:
            app_module._active_count = 1  # simulate full capacity

        with patch("gpu_service.config.gpu_settings") as mock_settings:
            mock_settings.max_concurrent_jobs = 1
            resp = client.post(
                "/api/v1/video-jobs",
                json={"job_id": "x", "gcs_prefix": "gs://b/x"},
            )
            assert resp.status_code == 429

    def test_missing_fields_returns_422(self, client):
        resp = client.post("/api/v1/video-jobs", json={"job_id": "abc"})
        assert resp.status_code == 422


class TestGetVideoJobStatus:
    def test_returns_job_when_exists(self, client):
        with patch("gpu_service.app.get_job") as mock_get:
            mock_get.return_value = {
                "video_job_id": "vj_1",
                "status": "tts",
                "progress": {"phase": "tts", "percent": 30},
            }
            resp = client.get("/api/v1/video-jobs/vj_1")
            assert resp.status_code == 200
            assert resp.json()["status"] == "tts"

    def test_returns_404_for_unknown_job(self, client):
        with patch("gpu_service.app.get_job", return_value=None):
            resp = client.get("/api/v1/video-jobs/nonexistent")
            assert resp.status_code == 404

    def test_returns_complete_with_output_paths(self, client):
        with patch("gpu_service.app.get_job") as mock_get:
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
        with patch("gpu_service.app.get_job") as mock_get:
            mock_get.return_value = {
                "video_job_id": "vj_3",
                "status": "error",
                "error": "OOM killed",
            }
            resp = client.get("/api/v1/video-jobs/vj_3")
            assert resp.status_code == 200
            assert resp.json()["error"] == "OOM killed"
