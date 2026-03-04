"""Tests for backend.services.tts_engine — all Kokoro calls mocked.

soundfile and kokoro may or may not be installed in dev, so we patch
soundfile.write in each test that checks audio output.
"""

import os
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# Stub soundfile if not installed so tts_engine can be imported
_sf_mock = MagicMock()
sys.modules.setdefault("soundfile", _sf_mock)

from backend.services.tts_engine import SAMPLE_RATE, TTSEngine, _validate_path  # noqa: E402


def _mock_pipeline():
    """Return a mock KPipeline that yields fake audio chunks."""
    mock_pipe = MagicMock()
    chunk = SimpleNamespace(audio=np.zeros(2400, dtype=np.float32))
    mock_pipe.return_value = [chunk]
    return mock_pipe


class TestTTSEngine:
    """Tests for TTSEngine."""

    @patch("soundfile.write")
    def test_synthesize_writes_wav(self, mock_sf_write, tmp_path):
        engine = TTSEngine()
        engine._pipeline = _mock_pipeline()

        out = os.path.join(str(tmp_path), "out.wav")
        result = engine.synthesize("Hello world", out)

        assert result == out
        mock_sf_write.assert_called_once()
        args = mock_sf_write.call_args
        assert args[0][0] == out
        assert args[0][2] == SAMPLE_RATE

    def test_synthesize_calls_pipeline_with_voice(self, tmp_path):
        engine = TTSEngine(voice="bf_emma")
        mock_pipe = _mock_pipeline()
        engine._pipeline = mock_pipe

        with patch("soundfile.write"):
            out = os.path.join(str(tmp_path), "out.wav")
            engine.synthesize("Test", out)

        mock_pipe.assert_called_once_with("Test", voice="bf_emma")

    @patch("soundfile.write")
    def test_synthesize_segments_creates_all_files(self, mock_sf_write, tmp_path):
        engine = TTSEngine()
        engine._pipeline = _mock_pipeline()

        segments = [
            {"slide_num": 1, "text": "Segment one"},
            {"slide_num": 2, "text": "Segment two"},
            {"slide_num": 3, "text": "Segment three"},
        ]
        out_dir = os.path.join(str(tmp_path), "audio")
        paths = engine.synthesize_segments(segments, out_dir)

        assert len(paths) == 3
        assert all("slide_" in p for p in paths)
        assert mock_sf_write.call_count == 3

    def test_lazy_initialization(self):
        engine = TTSEngine()
        assert engine._pipeline is None

    def test_pipeline_created_on_first_call(self, tmp_path):
        engine = TTSEngine()
        mock_kpipeline_cls = MagicMock()
        mock_pipe = _mock_pipeline()
        mock_kpipeline_cls.return_value = mock_pipe

        with (
            patch.dict("sys.modules", {"kokoro": MagicMock(KPipeline=mock_kpipeline_cls)}),
            patch("soundfile.write"),
        ):
            engine._pipeline = None
            out = os.path.join(str(tmp_path), "out.wav")
            engine.synthesize("Hello", out)

        mock_kpipeline_cls.assert_called_once()

    def test_custom_voice_override(self):
        engine = TTSEngine(voice="custom_voice", lang="b")
        assert engine._voice == "custom_voice"
        assert engine._lang == "b"

    @patch("soundfile.write")
    def test_concatenates_multiple_chunks(self, mock_sf_write, tmp_path):
        engine = TTSEngine()
        mock_pipe = MagicMock()
        chunks = [
            SimpleNamespace(audio=np.ones(1000, dtype=np.float32)),
            SimpleNamespace(audio=np.ones(2000, dtype=np.float32)),
        ]
        mock_pipe.return_value = chunks
        engine._pipeline = mock_pipe

        out = os.path.join(str(tmp_path), "out.wav")
        engine.synthesize("Hello", out)

        written_audio = mock_sf_write.call_args[0][1]
        assert len(written_audio) == 3000


class TestValidatePath:
    """Tests for _validate_path."""

    def test_path_traversal_rejected(self):
        with pytest.raises(ValueError, match="Path traversal"):
            _validate_path("/etc/passwd")

    def test_tmp_path_allowed(self, tmp_path):
        _validate_path(str(tmp_path / "test.wav"))

    def test_cwd_path_allowed(self):
        _validate_path(os.path.join(os.getcwd(), "outputs", "test.wav"))
