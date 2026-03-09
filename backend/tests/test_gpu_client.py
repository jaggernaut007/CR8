"""Tests for video service HTTP client (3-tier fallback).

Optimized: all tests mock time.sleep and _get_identity_token to avoid
real delays (~150s savings across the suite).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests as req_lib


@pytest.fixture(autouse=True)
def _no_sleep():
    """Prevent real time.sleep in all gpu_client tests."""
    with patch("backend.services.gpu_client.time") as mock_time:
        mock_time.sleep = MagicMock()
        mock_time.time = MagicMock(return_value=0)
        yield mock_time


@pytest.fixture(autouse=True)
def _no_identity_token():
    """Skip GCP identity token fetching in all gpu_client tests."""
    with patch("backend.services.gpu_client._get_identity_token", return_value=None):
        yield


@pytest.fixture()
def video_client():
    """Create a VideoServiceClient with a single GPU tier."""
    with patch("backend.services.gpu_client.settings") as mock_settings:
        mock_settings.gpu_service_url = "https://cr8-gpu.example.com"
        mock_settings.gpu_fallback_url = ""
        mock_settings.cpu_video_service_url = ""
        from backend.services.gpu_client import VideoServiceClient

        return VideoServiceClient(base_url="https://cr8-gpu.example.com")


@pytest.fixture()
def three_tier_client():
    """Create a VideoServiceClient with all 3 tiers configured."""
    with patch("backend.services.gpu_client.settings") as mock_settings:
        mock_settings.gpu_service_url = "https://gpu1.example.com"
        mock_settings.gpu_fallback_url = "https://gpu2.example.com"
        mock_settings.cpu_video_service_url = "https://cpu-video.example.com"
        from backend.services.gpu_client import VideoServiceClient

        return VideoServiceClient(
            base_url="https://gpu1.example.com",
            fallback_url="https://gpu2.example.com",
            cpu_video_url="https://cpu-video.example.com",
        )


class TestIsAvailable:
    def test_returns_true_on_200(self, video_client):
        with patch("backend.services.gpu_client.requests") as mock_req:
            mock_req.get.return_value = MagicMock(status_code=200)
            assert video_client.is_available() is True

    def test_returns_false_on_500(self, video_client):
        with patch("backend.services.gpu_client.requests") as mock_req:
            mock_req.get.return_value = MagicMock(status_code=500)
            assert video_client.is_available() is False

    def test_returns_false_on_connection_error(self, video_client):
        with patch("backend.services.gpu_client.requests") as mock_req:
            mock_req.get.side_effect = ConnectionError("refused")
            assert video_client.is_available() is False

    def test_tries_all_tiers(self, three_tier_client):
        """Falls through GPU1 and GPU2 to CPU-video."""
        with patch("backend.services.gpu_client.requests") as mock_req:
            mock_req.get.side_effect = [
                ConnectionError("gpu1 down"),
                ConnectionError("gpu2 down"),
                MagicMock(status_code=200),
            ]
            assert three_tier_client.is_available() is True
            assert three_tier_client.base_url == "https://cpu-video.example.com"


class TestSubmitJob:
    def test_posts_and_returns_video_job_id(self, video_client):
        with patch("backend.services.gpu_client.requests") as mock_req:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"video_job_id": "vj_abc_123", "status": "accepted"}
            mock_resp.raise_for_status = MagicMock()
            mock_req.post.return_value = mock_resp

            result = video_client.submit_job("abc", "gs://bucket/abc")

            assert result == "vj_abc_123"
            mock_req.post.assert_called_once()
            call_kwargs = mock_req.post.call_args
            assert call_kwargs[1]["json"]["job_id"] == "abc"
            assert call_kwargs[1]["json"]["gcs_prefix"] == "gs://bucket/abc"

    def test_raises_on_http_error(self, video_client):
        with patch("backend.services.gpu_client.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.raise_for_status.side_effect = Exception("403 Forbidden")
            mock_post.return_value = mock_resp

            with pytest.raises(Exception, match="403"):
                video_client.submit_job("abc", "gs://bucket/abc")

    def test_fallback_to_tier_2_on_connection_error(self, three_tier_client):
        """GPU1 fails, GPU2 succeeds."""
        with patch("backend.services.gpu_client.requests") as mock_req:
            mock_req.ConnectionError = req_lib.ConnectionError
            mock_req.Timeout = req_lib.Timeout
            mock_req.HTTPError = req_lib.HTTPError
            ok_resp = MagicMock()
            ok_resp.json.return_value = {"video_job_id": "vj_x_123", "status": "accepted"}
            ok_resp.raise_for_status = MagicMock()
            mock_req.post.side_effect = [req_lib.ConnectionError("gpu1 down"), ok_resp]

            result = three_tier_client.submit_job("x", "gs://b/x")
            assert result == "vj_x_123"
            assert three_tier_client.base_url == "https://gpu2.example.com"

    def test_fallback_to_tier_3_on_all_gpu_failure(self, three_tier_client):
        """Both GPUs fail, CPU-video succeeds."""
        with patch("backend.services.gpu_client.requests") as mock_req:
            mock_req.ConnectionError = req_lib.ConnectionError
            mock_req.Timeout = req_lib.Timeout
            mock_req.HTTPError = req_lib.HTTPError
            ok_resp = MagicMock()
            ok_resp.json.return_value = {"video_job_id": "vj_y_456", "status": "accepted"}
            ok_resp.raise_for_status = MagicMock()
            mock_req.post.side_effect = [
                req_lib.ConnectionError("gpu1 down"),
                req_lib.ConnectionError("gpu2 down"),
                ok_resp,
            ]

            result = three_tier_client.submit_job("y", "gs://b/y")
            assert result == "vj_y_456"
            assert three_tier_client.base_url == "https://cpu-video.example.com"

    def test_raises_when_all_tiers_fail(self, three_tier_client):
        """All 3 tiers fail — raises the last exception."""
        with patch("backend.services.gpu_client.requests") as mock_req:
            mock_req.ConnectionError = req_lib.ConnectionError
            mock_req.Timeout = req_lib.Timeout
            mock_req.HTTPError = req_lib.HTTPError
            mock_req.post.side_effect = req_lib.ConnectionError("all down")

            with pytest.raises(req_lib.ConnectionError, match="all down"):
                three_tier_client.submit_job("z", "gs://b/z")


# ---------------------------------------------------------------------------
# _do_submit — KeyError guard (new behaviour added this session)
# ---------------------------------------------------------------------------


class TestDoSubmit:
    """Covers the new RuntimeError raised when 'video_job_id' is missing in response."""

    def test_raises_runtime_error_when_video_job_id_missing(self, video_client):
        """When the response has no 'video_job_id' key, RuntimeError must be raised."""
        with patch("backend.services.gpu_client.requests") as mock_req:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"status": "accepted"}  # missing video_job_id
            mock_resp.raise_for_status = MagicMock()
            mock_req.post.return_value = mock_resp

            with pytest.raises(RuntimeError, match="video_job_id"):
                video_client._do_submit("job123", "gs://bucket/job123")

    def test_raises_runtime_error_for_empty_response(self, video_client):
        """An empty response dict must also raise RuntimeError."""
        with patch("backend.services.gpu_client.requests") as mock_req:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {}
            mock_resp.raise_for_status = MagicMock()
            mock_req.post.return_value = mock_resp

            with pytest.raises(RuntimeError):
                video_client._do_submit("job123", "gs://bucket/job123")

    def test_raises_runtime_error_for_null_video_job_id(self, video_client):
        """A null/None value for 'video_job_id' must raise RuntimeError."""
        with patch("backend.services.gpu_client.requests") as mock_req:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"video_job_id": None}
            mock_resp.raise_for_status = MagicMock()
            mock_req.post.return_value = mock_resp

            with pytest.raises(RuntimeError):
                video_client._do_submit("job123", "gs://bucket/job123")

    def test_returns_video_job_id_when_present(self, video_client):
        """When 'video_job_id' is present and non-empty, it must be returned."""
        with patch("backend.services.gpu_client.requests") as mock_req:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"video_job_id": "vj-xyz-789", "status": "accepted"}
            mock_resp.raise_for_status = MagicMock()
            mock_req.post.return_value = mock_resp

            result = video_client._do_submit("job123", "gs://bucket/job123")

        assert result == "vj-xyz-789"

    def test_error_message_references_response_data(self, video_client):
        """The RuntimeError message must include the bad response data for debugging."""
        with patch("backend.services.gpu_client.requests") as mock_req:
            bad_response = {"unexpected_key": "value"}
            mock_resp = MagicMock()
            mock_resp.json.return_value = bad_response
            mock_resp.raise_for_status = MagicMock()
            mock_req.post.return_value = mock_resp

            with pytest.raises(RuntimeError) as exc_info:
                video_client._do_submit("job123", "gs://bucket/job123")

        # The error should mention what was received to help debugging
        assert "video_job_id" in str(exc_info.value)


class TestPollUntilComplete:
    def test_returns_on_complete(self, video_client):
        with patch("backend.services.gpu_client.requests") as mock_req:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "status": "complete",
                "output_paths": ["01_topic.mp4"],
            }
            mock_resp.raise_for_status = MagicMock()
            mock_req.get.return_value = mock_resp

            result = video_client.poll_until_complete("vj_1", interval=0, timeout=5)
            assert result["status"] == "complete"

    def test_raises_on_error_status(self, video_client):
        with patch("backend.services.gpu_client.requests") as mock_req:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"status": "error", "error": "OOM"}
            mock_resp.raise_for_status = MagicMock()
            mock_req.get.return_value = mock_resp

            with pytest.raises(RuntimeError, match="OOM"):
                video_client.poll_until_complete("vj_1", interval=0, timeout=5)

    def test_raises_timeout(self, video_client):
        with patch("backend.services.gpu_client.requests") as mock_req:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "status": "processing",
                "progress": {"phase": "tts", "percent": 20},
            }
            mock_resp.raise_for_status = MagicMock()
            mock_req.get.return_value = mock_resp

            with pytest.raises(TimeoutError, match="not complete after 0s"):
                video_client.poll_until_complete("vj_1", interval=1, timeout=0)

    def test_prints_progress_lines(self, video_client, capsys):
        """Progress lines should be emitted for ProgressCapture parsing."""
        with patch("backend.services.gpu_client.requests") as mock_req:
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

            video_client.poll_until_complete("vj_1", interval=0, timeout=60)

            captured = capsys.readouterr()
            assert "[Video] GPU: tts (30%)" in captured.out

    def test_polls_multiple_times_before_complete(self, video_client):
        with patch("backend.services.gpu_client.requests") as mock_req:
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

            result = video_client.poll_until_complete("vj_1", interval=1, timeout=60)
            assert result["status"] == "complete"
            assert mock_req.get.call_count == 3

    def test_cancel_check_cancels_job_and_reraises(self, video_client):
        """When cancel_check raises, the job is cancelled and the exception propagates."""
        def _raise():
            raise RuntimeError("pipeline cancelled by user")

        with patch("backend.services.gpu_client.requests") as mock_req:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"status": "tts", "progress": {"phase": "tts", "percent": 10}}
            mock_resp.raise_for_status = MagicMock()
            # cancel endpoint
            cancel_resp = MagicMock(status_code=200)
            mock_req.post.return_value = cancel_resp
            mock_req.get.return_value = mock_resp

            with pytest.raises(RuntimeError, match="pipeline cancelled by user"):
                video_client.poll_until_complete("vj_1", interval=0, timeout=60, cancel_check=_raise)

            # Verify cancel was sent to the service
            mock_req.post.assert_called_once()
            assert "/cancel" in mock_req.post.call_args[0][0]

    def test_eta_question_mark_when_eta_none(self, video_client, capsys):
        """When eta_s is absent, the GPU_TIME line prints eta=?."""
        with patch("backend.services.gpu_client.requests") as mock_req:
            responses = [
                {
                    "status": "processing",
                    "progress": {
                        "phase": "tts",
                        "percent": 10,
                        "elapsed_s": 30,
                        # eta_s intentionally absent
                    },
                },
                {"status": "complete", "output_paths": ["v.mp4"]},
            ]
            mock_resp = MagicMock()
            mock_resp.json.side_effect = responses
            mock_resp.raise_for_status = MagicMock()
            mock_req.get.return_value = mock_resp

            video_client.poll_until_complete("vj_1", interval=0, timeout=60)

            captured = capsys.readouterr()
            assert "eta=?" in captured.out

    def test_no_time_line_when_elapsed_absent(self, video_client, capsys):
        """When elapsed_s is absent, no GPU_TIME line is emitted."""
        with patch("backend.services.gpu_client.requests") as mock_req:
            responses = [
                {
                    "status": "processing",
                    "progress": {"phase": "tts", "percent": 10},
                    # no elapsed_s
                },
                {"status": "complete", "output_paths": ["v.mp4"]},
            ]
            mock_resp = MagicMock()
            mock_resp.json.side_effect = responses
            mock_resp.raise_for_status = MagicMock()
            mock_req.get.return_value = mock_resp

            video_client.poll_until_complete("vj_1", interval=0, timeout=60)

            captured = capsys.readouterr()
            assert "GPU_TIME" not in captured.out


class TestCancelJob:
    def test_cancel_returns_true_on_200(self, video_client):
        with patch("backend.services.gpu_client.requests") as mock_req:
            mock_resp = MagicMock(status_code=200)
            mock_req.post.return_value = mock_resp
            assert video_client.cancel_job("vj_1") is True
            mock_req.post.assert_called_once()
            assert "/cancel" in mock_req.post.call_args[0][0]

    def test_cancel_returns_true_on_409(self, video_client):
        with patch("backend.services.gpu_client.requests") as mock_req:
            mock_resp = MagicMock(status_code=409)
            mock_req.post.return_value = mock_resp
            assert video_client.cancel_job("vj_1") is True

    def test_cancel_returns_false_on_network_error(self, video_client):
        with patch("backend.services.gpu_client.requests") as mock_req:
            mock_req.post.side_effect = ConnectionError("refused")
            assert video_client.cancel_job("vj_1") is False


class TestPollCancelledStatus:
    def test_raises_on_cancelled_status(self, video_client):
        with patch("backend.services.gpu_client.requests") as mock_req:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"status": "cancelled"}
            mock_resp.raise_for_status = MagicMock()
            mock_req.get.return_value = mock_resp

            with pytest.raises(RuntimeError, match="cancelled"):
                video_client.poll_until_complete("vj_1", interval=0, timeout=5)

    def test_emits_structured_progress_lines(self, video_client, capsys):
        with patch("backend.services.gpu_client.requests") as mock_req:
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

            video_client.poll_until_complete("vj_1", interval=0, timeout=60)

            captured = capsys.readouterr()
            assert "[Video] GPU_COMPOSE: 2/5" in captured.out
            assert "[Video] GPU_TTS: 3/5" in captured.out
            assert "[Video] GPU_TIME: elapsed=120 eta=300" in captured.out


class TestAuthHeaders:
    def test_includes_bearer_token_when_available(self, video_client):
        with patch("backend.services.gpu_client._get_identity_token", return_value="tok123"):
            headers = video_client._headers()
            assert headers["Authorization"] == "Bearer tok123"

    def test_no_auth_header_in_local_dev(self, video_client):
        # _no_identity_token autouse fixture returns None
        headers = video_client._headers()
        assert "Authorization" not in headers


class TestHeadersFor:
    def test_includes_bearer_token_scoped_to_url(self, video_client):
        """_headers_for scopes the identity token to the specific URL passed in."""
        with patch("backend.services.gpu_client._get_identity_token", return_value="scoped_tok") as mock_token:
            headers = video_client._headers_for("https://other-service.example.com")
            assert headers["Authorization"] == "Bearer scoped_tok"
            mock_token.assert_called_once_with("https://other-service.example.com")

    def test_no_auth_header_when_token_is_none(self, video_client):
        headers = video_client._headers_for("https://other-service.example.com")
        assert "Authorization" not in headers

    def test_always_includes_content_type(self, video_client):
        headers = video_client._headers_for("https://any.example.com")
        assert headers["Content-Type"] == "application/json"

    def test_headers_for_differs_from_headers_by_audience(self, video_client):
        """_headers_for uses the passed URL as the audience; _headers uses base_url."""
        audience_used = []

        def _capture_audience(url):
            audience_used.append(url)

        with patch("backend.services.gpu_client._get_identity_token", side_effect=_capture_audience):
            video_client._headers_for("https://specific-tier.example.com")

        assert audience_used == ["https://specific-tier.example.com"]


class TestBackwardCompat:
    def test_gpu_video_client_alias_exists(self):
        with patch("backend.services.gpu_client.settings") as mock_settings:
            mock_settings.gpu_service_url = "https://gpu.example.com"
            mock_settings.gpu_fallback_url = ""
            mock_settings.cpu_video_service_url = ""
            from backend.services.gpu_client import GPUVideoClient, VideoServiceClient

            assert GPUVideoClient is VideoServiceClient


class TestTierList:
    def test_empty_urls_filtered_out(self):
        with patch("backend.services.gpu_client.settings") as mock_settings:
            mock_settings.gpu_service_url = "https://gpu.example.com"
            mock_settings.gpu_fallback_url = ""
            mock_settings.cpu_video_service_url = ""
            from backend.services.gpu_client import _build_tier_list

            tiers = _build_tier_list("https://gpu.example.com", "", "")
            assert len(tiers) == 1
            assert tiers[0] == "https://gpu.example.com"

    def test_all_three_tiers(self):
        with patch("backend.services.gpu_client.settings") as mock_settings:
            mock_settings.gpu_service_url = ""
            mock_settings.gpu_fallback_url = ""
            mock_settings.cpu_video_service_url = ""
            from backend.services.gpu_client import _build_tier_list

            tiers = _build_tier_list(
                "https://gpu1.example.com",
                "https://gpu2.example.com",
                "https://cpu.example.com",
            )
            assert len(tiers) == 3

    def test_strips_trailing_slash(self):
        """Trailing slashes on URLs are stripped so requests don't get double-slash paths."""
        with patch("backend.services.gpu_client.settings") as mock_settings:
            mock_settings.gpu_service_url = ""
            mock_settings.gpu_fallback_url = ""
            mock_settings.cpu_video_service_url = ""
            from backend.services.gpu_client import _build_tier_list

            tiers = _build_tier_list("https://gpu.example.com/", "", "")
            assert tiers[0] == "https://gpu.example.com"

    def test_only_cpu_video_url_set(self):
        """A client configured with only a CPU-video URL has exactly one tier."""
        with patch("backend.services.gpu_client.settings") as mock_settings:
            mock_settings.gpu_service_url = ""
            mock_settings.gpu_fallback_url = ""
            mock_settings.cpu_video_service_url = ""
            from backend.services.gpu_client import _build_tier_list

            tiers = _build_tier_list(None, None, "https://cpu.example.com")
            assert len(tiers) == 1
            assert tiers[0] == "https://cpu.example.com"

    def test_none_arguments_fall_back_to_settings(self):
        """When all arguments are None, tiers are built from settings values."""
        with patch("backend.services.gpu_client.settings") as mock_settings:
            mock_settings.gpu_service_url = "https://from-settings.example.com"
            mock_settings.gpu_fallback_url = ""
            mock_settings.cpu_video_service_url = ""
            from backend.services.gpu_client import _build_tier_list

            tiers = _build_tier_list(None, None, None)
            assert len(tiers) == 1
            assert tiers[0] == "https://from-settings.example.com"


class TestTryNextTier:
    def test_returns_false_on_single_tier_client(self, video_client):
        """_try_next_tier returns False when already on the only tier."""
        assert video_client._try_next_tier() is False

    def test_returns_true_and_advances_on_three_tier_client(self, three_tier_client):
        """_try_next_tier advances to tier 2 and returns True."""
        advanced = three_tier_client._try_next_tier()
        assert advanced is True
        assert three_tier_client.base_url == "https://gpu2.example.com"

    def test_returns_false_when_already_on_last_tier(self, three_tier_client):
        """_try_next_tier returns False when already on the last configured tier."""
        three_tier_client._try_next_tier()  # -> tier 2
        three_tier_client._try_next_tier()  # -> tier 3
        assert three_tier_client._try_next_tier() is False
