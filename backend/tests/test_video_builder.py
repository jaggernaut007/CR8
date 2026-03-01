"""Tests for backend.services.video_builder.

All tests mock the HeyGen API (requests) so no real API calls are made.
"""

import os
from unittest.mock import patch, MagicMock

import pytest

from backend.services.video_builder import (
    _slugify,
    _split_into_scenes,
    _create_video,
    _poll_status,
    _download_video,
    build_videos,
)


# ---------------------------------------------------------------------------
# _slugify
# ---------------------------------------------------------------------------

class TestSlugify:
    def test_basic(self):
        assert _slugify("Word2Vec Embeddings") == "Word2Vec_Embeddings"

    def test_special_chars(self):
        assert _slugify("GloVe & Global (Methods)") == "GloVe_Global_Methods"

    def test_truncates_long_names(self):
        long_name = "A" * 200
        assert len(_slugify(long_name)) <= 80


# ---------------------------------------------------------------------------
# _split_into_scenes
# ---------------------------------------------------------------------------

class TestSplitIntoScenes:
    def test_short_script_single_scene(self):
        script = "Hello world. This is a test."
        scenes = _split_into_scenes(script)
        assert scenes == [script]

    def test_long_script_splits_on_paragraphs(self):
        # Build a script with 3 paragraphs, each ~2000 chars
        para = "A" * 2000
        script = f"{para}\n\n{para}\n\n{para}"
        scenes = _split_into_scenes(script)
        assert len(scenes) >= 2
        for scene in scenes:
            assert len(scene) <= 5000

    def test_very_long_paragraph_splits_on_sentences(self):
        # A single paragraph that's >5000 chars, made of short sentences
        sentences = ["This is sentence number {i}." for i in range(300)]
        script = " ".join(sentences)
        assert len(script) > 5000
        scenes = _split_into_scenes(script)
        assert len(scenes) >= 2
        for scene in scenes:
            assert len(scene) <= 5000


# ---------------------------------------------------------------------------
# _create_video (mocked)
# ---------------------------------------------------------------------------

class TestCreateVideo:
    @patch("backend.services.video_builder.requests.post")
    def test_returns_video_id(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "error": None,
            "data": {"video_id": "abc123"},
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        video_id = _create_video("fake-key", "Hello world", "avatar1", "voice1", "Test")
        assert video_id == "abc123"

        # Verify correct endpoint and auth
        call_args = mock_post.call_args
        assert "v2/video/generate" in call_args[0][0]
        assert call_args[1]["headers"]["x-api-key"] == "fake-key"

    @patch("backend.services.video_builder.requests.post")
    def test_raises_on_api_error(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "error": "insufficient_credits",
            "data": None,
        }
        mock_resp.raise_for_status = MagicMock()
        mock_post.return_value = mock_resp

        with pytest.raises(RuntimeError, match="HeyGen API error"):
            _create_video("fake-key", "Hello", "avatar1", "voice1", "Test")


# ---------------------------------------------------------------------------
# _poll_status (mocked)
# ---------------------------------------------------------------------------

class TestPollStatus:
    @patch("backend.services.video_builder.time.sleep")
    @patch("backend.services.video_builder.requests.get")
    def test_returns_on_completed(self, mock_get, mock_sleep):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": {
                "status": "completed",
                "video_url": "https://files.heygen.ai/test.mp4",
                "duration": 120.5,
            },
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = _poll_status("fake-key", "vid123", interval=1, timeout=10)
        assert result["status"] == "completed"
        assert result["video_url"] == "https://files.heygen.ai/test.mp4"

    @patch("backend.services.video_builder.time.sleep")
    @patch("backend.services.video_builder.requests.get")
    def test_raises_on_failed(self, mock_get, mock_sleep):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": {"status": "failed", "error": "rendering_error"},
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        with pytest.raises(RuntimeError, match="failed"):
            _poll_status("fake-key", "vid123", interval=1, timeout=10)

    @patch("backend.services.video_builder.time.sleep")
    @patch("backend.services.video_builder.requests.get")
    def test_raises_on_timeout(self, mock_get, mock_sleep):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "data": {"status": "processing"},
        }
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        with pytest.raises(TimeoutError):
            _poll_status("fake-key", "vid123", interval=1, timeout=3)


# ---------------------------------------------------------------------------
# _download_video (mocked)
# ---------------------------------------------------------------------------

class TestDownloadVideo:
    @patch("backend.services.video_builder.requests.get")
    def test_writes_file(self, mock_get, tmp_path):
        mock_resp = MagicMock()
        mock_resp.iter_content.return_value = [b"fake-video-data"]
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        out = str(tmp_path / "test.mp4")
        _download_video("https://example.com/video.mp4", out)
        assert os.path.exists(out)
        with open(out, "rb") as f:
            assert f.read() == b"fake-video-data"


# ---------------------------------------------------------------------------
# build_videos (integration, fully mocked)
# ---------------------------------------------------------------------------

class TestBuildVideos:
    def test_raises_not_implemented(self, tmp_path):
        """build_videos is not yet implemented — must raise NotImplementedError immediately."""
        with pytest.raises(NotImplementedError, match="not yet available"):
            build_videos(
                topics=[{"name": "Word2Vec"}],
                scripts=["Some script"],
                output_dir=str(tmp_path / "videos"),
                api_key="fake-key",
                avatar_id="avatar1",
                voice_id="voice1",
            )

    def test_raises_before_any_api_call(self, tmp_path):
        """NotImplementedError must fire before any HeyGen API call is attempted."""
        with patch("backend.services.video_builder._create_video") as mock_create:
            with pytest.raises(NotImplementedError):
                build_videos(
                    topics=[{"name": "T1"}],
                    scripts=["s"],
                    output_dir=str(tmp_path / "v"),
                    api_key="k",
                    avatar_id="a",
                    voice_id="v",
                )
            mock_create.assert_not_called()
