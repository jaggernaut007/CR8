"""Tests for GPU video service HTTP client."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture()
def gpu_client():
    with patch("backend.services.gpu_client.settings") as mock_settings:
        mock_settings.gpu_service_url = "https://cr8-gpu.example.com"
        from backend.services.gpu_client import GPUVideoClient

        return GPUVideoClient(base_url="https://cr8-gpu.example.com")


class TestIsAvailable:
    def test_returns_true_on_200(self, gpu_client):
        with patch("backend.services.gpu_client.requests") as mock_req:
            mock_req.get.return_value = MagicMock(status_code=200)
            assert gpu_client.is_available() is True

    def test_returns_false_on_500(self, gpu_client):
        with patch("backend.services.gpu_client.requests") as mock_req:
            mock_req.get.return_value = MagicMock(status_code=500)
            assert gpu_client.is_available() is False

    def test_returns_false_on_connection_error(self, gpu_client):
        with patch("backend.services.gpu_client.requests") as mock_req:
            mock_req.get.side_effect = ConnectionError("refused")
            assert gpu_client.is_available() is False


class TestSubmitJob:
    def test_posts_and_returns_video_job_id(self, gpu_client):
        with patch("backend.services.gpu_client.requests") as mock_req:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"video_job_id": "vj_abc_123", "status": "accepted"}
            mock_resp.raise_for_status = MagicMock()
            mock_req.post.return_value = mock_resp

            result = gpu_client.submit_job("abc", "gs://bucket/abc")

            assert result == "vj_abc_123"
            mock_req.post.assert_called_once()
            call_kwargs = mock_req.post.call_args
            assert call_kwargs[1]["json"]["job_id"] == "abc"
            assert call_kwargs[1]["json"]["gcs_prefix"] == "gs://bucket/abc"

    def test_raises_on_http_error(self, gpu_client):
        with patch("backend.services.gpu_client.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.raise_for_status.side_effect = Exception("403 Forbidden")
            mock_post.return_value = mock_resp

            with pytest.raises(Exception, match="403"):
                gpu_client.submit_job("abc", "gs://bucket/abc")


class TestPollUntilComplete:
    def test_returns_on_complete(self, gpu_client):
        with patch("backend.services.gpu_client.requests") as mock_req:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "status": "complete",
                "output_paths": ["01_topic.mp4"],
            }
            mock_resp.raise_for_status = MagicMock()
            mock_req.get.return_value = mock_resp

            result = gpu_client.poll_until_complete("vj_1", interval=0, timeout=5)
            assert result["status"] == "complete"

    def test_raises_on_error_status(self, gpu_client):
        with patch("backend.services.gpu_client.requests") as mock_req:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"status": "error", "error": "OOM"}
            mock_resp.raise_for_status = MagicMock()
            mock_req.get.return_value = mock_resp

            with pytest.raises(RuntimeError, match="OOM"):
                gpu_client.poll_until_complete("vj_1", interval=0, timeout=5)

    def test_raises_timeout(self, gpu_client):
        with patch("backend.services.gpu_client.requests") as mock_req:
            with patch("backend.services.gpu_client.time") as mock_time:
                mock_time.sleep = MagicMock()
                mock_resp = MagicMock()
                mock_resp.json.return_value = {
                    "status": "processing",
                    "progress": {"phase": "tts", "percent": 20},
                }
                mock_resp.raise_for_status = MagicMock()
                mock_req.get.return_value = mock_resp

                with pytest.raises(TimeoutError, match="not complete after 0s"):
                    gpu_client.poll_until_complete("vj_1", interval=1, timeout=0)

    def test_prints_progress_lines(self, gpu_client, capsys):
        """Progress lines should be emitted for ProgressCapture parsing."""
        with patch("backend.services.gpu_client.requests") as mock_req:
            with patch("backend.services.gpu_client.time") as mock_time:
                mock_time.sleep = MagicMock()
                responses = [
                    {
                        "status": "processing",
                        "progress": {"phase": "tts", "percent": 30},
                    },
                    {
                        "status": "complete",
                        "output_paths": ["vid.mp4"],
                    },
                ]
                mock_resp = MagicMock()
                mock_resp.json.side_effect = responses
                mock_resp.raise_for_status = MagicMock()
                mock_req.get.return_value = mock_resp

                gpu_client.poll_until_complete("vj_1", interval=0, timeout=60)

                captured = capsys.readouterr()
                assert "[Video] GPU: tts (30%)" in captured.out

    def test_polls_multiple_times_before_complete(self, gpu_client):
        with patch("backend.services.gpu_client.requests") as mock_req:
            with patch("backend.services.gpu_client.time") as mock_time:
                mock_time.sleep = MagicMock()
                responses = [
                    MagicMock(json=MagicMock(return_value={
                        "status": "tts",
                        "progress": {"phase": "tts", "percent": 20},
                    }), raise_for_status=MagicMock()),
                    MagicMock(json=MagicMock(return_value={
                        "status": "composing",
                        "progress": {"phase": "composing", "percent": 60},
                    }), raise_for_status=MagicMock()),
                    MagicMock(json=MagicMock(return_value={
                        "status": "complete",
                        "output_paths": ["v.mp4"],
                    }), raise_for_status=MagicMock()),
                ]
                mock_req.get.side_effect = responses

                result = gpu_client.poll_until_complete("vj_1", interval=1, timeout=60)
                assert result["status"] == "complete"
                assert mock_req.get.call_count == 3


class TestCancelJob:
    def test_cancel_returns_true_on_200(self, gpu_client):
        with patch("backend.services.gpu_client.requests") as mock_req:
            mock_resp = MagicMock(status_code=200)
            mock_req.post.return_value = mock_resp
            assert gpu_client.cancel_job("vj_1") is True
            mock_req.post.assert_called_once()
            assert "/cancel" in mock_req.post.call_args[0][0]

    def test_cancel_returns_true_on_409(self, gpu_client):
        with patch("backend.services.gpu_client.requests") as mock_req:
            mock_resp = MagicMock(status_code=409)
            mock_req.post.return_value = mock_resp
            assert gpu_client.cancel_job("vj_1") is True

    def test_cancel_returns_false_on_network_error(self, gpu_client):
        with patch("backend.services.gpu_client.requests") as mock_req:
            mock_req.post.side_effect = ConnectionError("refused")
            assert gpu_client.cancel_job("vj_1") is False


class TestPollCancelledStatus:
    def test_raises_on_cancelled_status(self, gpu_client):
        with patch("backend.services.gpu_client.requests") as mock_req:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"status": "cancelled"}
            mock_resp.raise_for_status = MagicMock()
            mock_req.get.return_value = mock_resp

            with pytest.raises(RuntimeError, match="cancelled"):
                gpu_client.poll_until_complete("vj_1", interval=0, timeout=5)

    def test_emits_structured_progress_lines(self, gpu_client, capsys):
        with patch("backend.services.gpu_client.requests") as mock_req:
            with patch("backend.services.gpu_client.time") as mock_time:
                mock_time.sleep = MagicMock()
                responses = [
                    {
                        "status": "processing",
                        "progress": {
                            "phase": "composing",
                            "percent": 55,
                            "completed_videos": 2,
                            "total_videos": 5,
                            "current_topic": 3,
                            "total_topics": 5,
                            "elapsed_s": 120,
                            "eta_s": 300,
                        },
                    },
                    {"status": "complete", "output_paths": ["v.mp4"]},
                ]
                mock_resp = MagicMock()
                mock_resp.json.side_effect = responses
                mock_resp.raise_for_status = MagicMock()
                mock_req.get.return_value = mock_resp

                gpu_client.poll_until_complete("vj_1", interval=0, timeout=60)

                captured = capsys.readouterr()
                assert "[Video] GPU_COMPOSE: 2/5" in captured.out
                assert "[Video] GPU_TTS: 3/5" in captured.out
                assert "[Video] GPU_TIME: elapsed=120 eta=300" in captured.out


class TestAuthHeaders:
    def test_includes_bearer_token_when_available(self, gpu_client):
        with patch("backend.services.gpu_client._get_identity_token", return_value="tok123"):
            headers = gpu_client._headers()
            assert headers["Authorization"] == "Bearer tok123"

    def test_no_auth_header_in_local_dev(self, gpu_client):
        with patch("backend.services.gpu_client._get_identity_token", return_value=None):
            headers = gpu_client._headers()
            assert "Authorization" not in headers
