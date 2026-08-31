"""Tests for backend.services.gpu_utils — encoder detection and GPU device selection."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from backend.services import gpu_utils
from backend.services.gpu_utils import (
    _encoder_available,
    get_ffmpeg_encoder,
    get_torch_device,
)


# ---------------------------------------------------------------------------
# get_torch_device
# ---------------------------------------------------------------------------


class TestGetTorchDevice:
    def test_explicit_preference_returned_as_is(self):
        assert get_torch_device("cpu") == "cpu"
        assert get_torch_device("cuda") == "cuda"
        assert get_torch_device("mps") == "mps"

    def test_auto_with_no_torch(self):
        with patch.dict("sys.modules", {"torch": None}):
            # Force ImportError
            with patch("builtins.__import__", side_effect=ImportError):
                assert get_torch_device("auto") == "cpu"

    @patch("backend.services.gpu_utils.torch", create=True)
    def test_auto_prefers_cuda(self, mock_torch):
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.get_device_name.return_value = "NVIDIA L4"
        # Re-run with a fresh import mock
        with patch.dict("sys.modules", {"torch": mock_torch}):
            result = get_torch_device("auto")
        assert result == "cuda"


# ---------------------------------------------------------------------------
# _encoder_available
# ---------------------------------------------------------------------------


class TestEncoderAvailable:
    def test_returns_true_when_encode_succeeds(self, tmp_path):
        """Encoder probe should pass when ffmpeg returns 0 and file has content."""
        with patch("backend.services.gpu_utils.tempfile.mkstemp") as mock_mkstemp:
            fake_path = str(tmp_path / "probe.mp4")
            # Create a non-empty file to simulate ffmpeg output
            with open(fake_path, "wb") as f:
                f.write(b"\x00" * 100)
            mock_mkstemp.return_value = (0, fake_path)

            with patch("backend.services.gpu_utils.os.close"):
                with patch("backend.services.gpu_utils.subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(returncode=0)
                    assert _encoder_available("h264_nvenc") is True

    def test_returns_false_when_encode_fails(self, tmp_path):
        """Encoder probe should fail when ffmpeg returns non-zero."""
        with patch("backend.services.gpu_utils.tempfile.mkstemp") as mock_mkstemp:
            fake_path = str(tmp_path / "probe.mp4")
            open(fake_path, "w").close()  # Empty file
            mock_mkstemp.return_value = (0, fake_path)

            with patch("backend.services.gpu_utils.os.close"):
                with patch("backend.services.gpu_utils.subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(
                        returncode=1,
                        stderr=b"Unknown encoder 'h264_nvenc'",
                    )
                    assert _encoder_available("h264_nvenc") is False

    def test_returns_false_when_ffmpeg_not_found(self):
        """Missing ffmpeg binary should not crash, just return False."""
        with patch("backend.services.gpu_utils.tempfile.mkstemp") as mock_mkstemp:
            mock_mkstemp.return_value = (0, "/tmp/probe.mp4")
            with patch("backend.services.gpu_utils.os.close"):
                with patch("backend.services.gpu_utils.subprocess.run", side_effect=FileNotFoundError):
                    with patch("backend.services.gpu_utils.os.path.exists", return_value=False):
                        assert _encoder_available("h264_nvenc") is False

    def test_returns_false_on_timeout(self):
        """Encoder probe should fail gracefully on timeout."""
        with patch("backend.services.gpu_utils.tempfile.mkstemp") as mock_mkstemp:
            mock_mkstemp.return_value = (0, "/tmp/probe.mp4")
            with patch("backend.services.gpu_utils.os.close"), patch(
                "backend.services.gpu_utils.subprocess.run",
                side_effect=subprocess.TimeoutExpired(cmd="ffmpeg", timeout=15),
            ), patch("backend.services.gpu_utils.os.path.exists", return_value=False):
                assert _encoder_available("h264_nvenc") is False

    def test_writes_to_real_file_not_null(self):
        """The probe command must use a temp file path, not '-f null -'."""
        with patch("backend.services.gpu_utils.tempfile.mkstemp") as mock_mkstemp:
            mock_mkstemp.return_value = (0, "/tmp/probe_test.mp4")
            with patch("backend.services.gpu_utils.os.close"):
                with patch("backend.services.gpu_utils.subprocess.run") as mock_run:
                    mock_run.return_value = MagicMock(returncode=1, stderr=b"")
                    with patch("backend.services.gpu_utils.os.path.exists", return_value=True):
                        with patch("backend.services.gpu_utils.os.path.getsize", return_value=0):
                            with patch("backend.services.gpu_utils.os.unlink"):
                                _encoder_available("h264_nvenc")

                    cmd = mock_run.call_args[0][0]
                    # Must NOT contain "-f null -"
                    assert "-f" not in cmd or "null" not in cmd
                    # Must end with a file path
                    assert cmd[-1].endswith(".mp4")


# ---------------------------------------------------------------------------
# get_ffmpeg_encoder (with cache)
# ---------------------------------------------------------------------------


class TestGetFfmpegEncoder:
    @pytest.fixture(autouse=True)
    def _clear_cache(self):
        """Clear the module-level encoder cache before each test."""
        gpu_utils._cached_encoder = None
        yield
        gpu_utils._cached_encoder = None

    @patch("backend.services.gpu_utils._encoder_available")
    def test_returns_first_available_hw_encoder(self, mock_avail):
        mock_avail.side_effect = lambda name: name == "h264_nvenc"
        assert get_ffmpeg_encoder() == "h264_nvenc"

    @patch("backend.services.gpu_utils._encoder_available")
    def test_falls_back_to_libx264(self, mock_avail):
        mock_avail.return_value = False
        assert get_ffmpeg_encoder() == "libx264"

    @patch("backend.services.gpu_utils._encoder_available")
    def test_prefers_videotoolbox_over_nvenc(self, mock_avail):
        mock_avail.return_value = True  # All encoders "available"
        assert get_ffmpeg_encoder() == "h264_videotoolbox"

    @patch("backend.services.gpu_utils._encoder_available")
    def test_result_is_cached(self, mock_avail):
        mock_avail.return_value = False
        assert get_ffmpeg_encoder() == "libx264"
        # Second call should not probe again
        mock_avail.reset_mock()
        assert get_ffmpeg_encoder() == "libx264"
        mock_avail.assert_not_called()
