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
    @patch("backend.services.video_builder._download_video")
    @patch("backend.services.video_builder._poll_status")
    @patch("backend.services.video_builder._create_video")
    def test_end_to_end(self, mock_create, mock_poll, mock_download, tmp_path):
        mock_create.side_effect = ["vid_001", "vid_002"]
        mock_poll.side_effect = [
            {"status": "completed", "video_url": "https://h.ai/1.mp4", "duration": 150.0},
            {"status": "completed", "video_url": "https://h.ai/2.mp4", "duration": 180.0},
        ]
        mock_download.side_effect = lambda url, path: open(path, "wb").write(b"mp4data")

        output_dir = str(tmp_path / "videos")
        topics = [{"name": "Word2Vec"}, {"name": "GloVe"}]
        scripts = ["Script about Word2Vec...", "Script about GloVe..."]

        paths = build_videos(
            topics=topics,
            scripts=scripts,
            output_dir=output_dir,
            api_key="fake-key",
            avatar_id="avatar1",
            voice_id="voice1",
        )

        assert len(paths) == 2
        assert mock_create.call_count == 2
        assert mock_poll.call_count == 2
        assert mock_download.call_count == 2

        # Scripts saved to disk
        scripts_dir = os.path.join(output_dir, "scripts")
        assert os.path.isdir(scripts_dir)
        script_files = os.listdir(scripts_dir)
        assert len(script_files) == 2

    @patch("backend.services.video_builder._download_video")
    @patch("backend.services.video_builder._poll_status")
    @patch("backend.services.video_builder._create_video")
    def test_preserves_order(self, mock_create, mock_poll, mock_download, tmp_path):
        mock_create.side_effect = ["vid_a", "vid_b"]
        mock_poll.side_effect = [
            {"status": "completed", "video_url": "https://h.ai/a.mp4", "duration": 120.0},
            {"status": "completed", "video_url": "https://h.ai/b.mp4", "duration": 130.0},
        ]
        mock_download.side_effect = lambda url, path: open(path, "wb").write(b"data")

        output_dir = str(tmp_path / "videos")
        topics = [{"name": "TopicA"}, {"name": "TopicB"}]
        scripts = ["Script A", "Script B"]

        paths = build_videos(
            topics=topics,
            scripts=scripts,
            output_dir=output_dir,
            api_key="key",
            avatar_id="av",
            voice_id="vo",
        )

        assert "01_TopicA" in paths[0]
        assert "02_TopicB" in paths[1]
