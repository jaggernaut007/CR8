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
    _get_topic_images,
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
    def test_heygen_raises_not_implemented(self, tmp_path):
        """HeyGen provider still raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="not yet available"):
            build_videos(
                topics=[{"name": "Word2Vec"}],
                scripts=["Some script"],
                output_dir=str(tmp_path / "videos"),
                api_key="fake-key",
                avatar_id="avatar1",
                voice_id="voice1",
                provider="heygen",
            )

    def test_synthesia_raises_not_implemented(self, tmp_path):
        """Synthesia provider still raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="not yet available"):
            build_videos(
                topics=[{"name": "T1"}],
                scripts=["s"],
                output_dir=str(tmp_path / "v"),
                provider="synthesia",
            )

    def test_heygen_raises_before_any_api_call(self, tmp_path):
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
                    provider="heygen",
                )
            mock_create.assert_not_called()


class TestBuildVideosKokoro:
    """Tests for the two-phase Kokoro pipeline (sequential TTS → parallel compose)."""

    def _mock_tts_and_compose(self):
        """Helper: mock TTS engine and compose to avoid real model/ffmpeg."""
        mock_engine_cls = patch("backend.services.tts_engine.TTSEngine")
        mock_parse = patch("backend.services.script_parser.parse_script")
        mock_compose = patch("backend.services.video_builder._compose_video")
        return mock_engine_cls, mock_parse, mock_compose

    def test_kokoro_provider_dispatches_to_two_phase_pipeline(self, tmp_path):
        """provider='kokoro' dispatches to sequential TTS then parallel compose."""
        with (
            patch("backend.services.tts_engine.TTSEngine") as mock_cls,
            patch("backend.services.script_parser.parse_script") as mock_parse,
            patch("backend.services.video_builder._compose_video") as mock_compose,
        ):
            mock_engine = MagicMock()
            mock_engine.synthesize_segments.return_value = [str(tmp_path / "a.wav")]
            mock_cls.return_value = mock_engine
            mock_parse.return_value = [{"slide_num": 1, "text": "Hello"}]

            result = build_videos(
                topics=[{"name": "Topic1"}],
                scripts=["[SLIDE 1]\nHello"],
                output_dir=str(tmp_path / "videos"),
                provider="kokoro",
                slide_images=[str(tmp_path / "slide.png")],
            )
            assert len(result) == 1
            mock_engine.synthesize_segments.assert_called_once()
            mock_compose.assert_called_once()

    def test_kokoro_saves_script_to_disk(self, tmp_path):
        """Kokoro path saves script .txt before generating video."""
        fake_img = tmp_path / "slide.png"
        fake_img.write_bytes(b"PNG")
        with (
            patch("backend.services.tts_engine.TTSEngine") as mock_cls,
            patch("backend.services.script_parser.parse_script") as mock_parse,
            patch("backend.services.video_builder._compose_video"),
        ):
            mock_engine = MagicMock()
            mock_engine.synthesize_segments.return_value = [str(tmp_path / "a.wav")]
            mock_cls.return_value = mock_engine
            mock_parse.return_value = [{"slide_num": 1, "text": "Hello"}]

            build_videos(
                topics=[{"name": "Word2Vec"}],
                scripts=["Test script content"],
                output_dir=str(tmp_path / "videos"),
                provider="kokoro",
                slide_images=[str(fake_img)],
            )
            scripts_dir = tmp_path / "videos" / "scripts"
            assert scripts_dir.exists()
            script_files = list(scripts_dir.glob("*.txt"))
            assert len(script_files) == 1
            assert script_files[0].read_text() == "Test script content"

    def test_kokoro_handles_tts_failure_gracefully(self, tmp_path):
        """If TTS raises during phase 1, error is caught and video is None."""
        fake_img = tmp_path / "slide.png"
        fake_img.write_bytes(b"PNG")
        with (
            patch("backend.services.tts_engine.TTSEngine") as mock_cls,
            patch("backend.services.script_parser.parse_script") as mock_parse,
            patch("backend.services.video_builder._compose_video") as mock_compose,
        ):
            mock_engine = MagicMock()
            mock_engine.synthesize_segments.side_effect = RuntimeError("TTS failed")
            mock_cls.return_value = mock_engine
            mock_parse.return_value = [{"slide_num": 1, "text": "Hello"}]

            result = build_videos(
                topics=[{"name": "Topic1"}],
                scripts=["Script"],
                output_dir=str(tmp_path / "videos"),
                provider="kokoro",
                slide_images=[str(fake_img)],
            )
            assert result == [None]
            mock_compose.assert_not_called()

    def test_kokoro_handles_compose_failure_gracefully(self, tmp_path):
        """If composition raises during phase 2, error is caught and video is None."""
        fake_img = tmp_path / "slide.png"
        fake_img.write_bytes(b"PNG")
        with (
            patch("backend.services.tts_engine.TTSEngine") as mock_cls,
            patch("backend.services.script_parser.parse_script") as mock_parse,
            patch("backend.services.video_builder._compose_video") as mock_compose,
        ):
            mock_engine = MagicMock()
            mock_engine.synthesize_segments.return_value = [str(tmp_path / "a.wav")]
            mock_cls.return_value = mock_engine
            mock_parse.return_value = [{"slide_num": 1, "text": "Hello"}]
            mock_compose.side_effect = RuntimeError("ffmpeg crashed")

            result = build_videos(
                topics=[{"name": "Topic1"}],
                scripts=["Script"],
                output_dir=str(tmp_path / "videos"),
                provider="kokoro",
                slide_images=[str(fake_img)],
            )
            assert result == [None]

    def test_kokoro_rejects_empty_slide_images(self, tmp_path):
        """Empty slide_images should raise RuntimeError early."""
        with pytest.raises(RuntimeError, match="No slide images"):
            build_videos(
                topics=[{"name": "Topic1"}],
                scripts=["Script"],
                output_dir=str(tmp_path / "videos"),
                provider="kokoro",
                slide_images=[],
            )

    def test_kokoro_shares_single_tts_engine(self, tmp_path):
        """All topics should share one TTSEngine instance (model loaded once)."""
        imgs = [str(tmp_path / f"s{i}.png") for i in range(3)]
        for img in imgs:
            open(img, "w").close()
        with (
            patch("backend.services.tts_engine.TTSEngine") as mock_cls,
            patch("backend.services.script_parser.parse_script") as mock_parse,
            patch("backend.services.video_builder._compose_video"),
        ):
            mock_engine = MagicMock()
            mock_engine.synthesize_segments.return_value = [str(tmp_path / "a.wav")]
            mock_cls.return_value = mock_engine
            mock_parse.return_value = [{"slide_num": 1, "text": "Hello"}]

            build_videos(
                topics=[{"name": "T1"}, {"name": "T2"}, {"name": "T3"}],
                scripts=["S1", "S2", "S3"],
                output_dir=str(tmp_path / "videos"),
                provider="kokoro",
                slide_images=imgs,
            )
            # TTSEngine should only be instantiated ONCE (shared across topics)
            mock_cls.assert_called_once()


class TestComposeVideoFallback:
    """Tests for _compose_video encoder fallback (hw encoder → libx264)."""

    def test_retries_with_libx264_on_encoder_failure(self, tmp_path):
        """If hardware encoder fails with OSError, _compose_video retries with libx264."""
        from backend.services.video_builder import _compose_video

        segments = [{"slide_num": 1, "text": "Hello"}]
        audio_paths = [str(tmp_path / "a.wav")]
        slide_images = [str(tmp_path / "slide.png")]
        output_path = str(tmp_path / "out.mp4")

        call_count = 0

        def mock_write_videofile(path, **kwargs):
            nonlocal call_count
            call_count += 1
            if kwargs.get("codec") == "h264_nvenc":
                raise OSError("[Errno 32] Broken pipe")

        mock_audio_inst = MagicMock()
        mock_audio_inst.duration = 5.0
        mock_img_inst = MagicMock()
        mock_img_inst.resized.return_value = mock_img_inst
        mock_img_inst.with_duration.return_value = mock_img_inst
        mock_img_inst.with_audio.return_value = mock_img_inst
        mock_final = MagicMock()
        mock_final.write_videofile = mock_write_videofile

        mock_moviepy = MagicMock()
        mock_moviepy.AudioFileClip.return_value = mock_audio_inst
        mock_moviepy.ImageClip.return_value = mock_img_inst
        mock_moviepy.concatenate_videoclips.return_value = mock_final

        with (
            patch.dict("sys.modules", {"moviepy": mock_moviepy}),
            patch("backend.services.gpu_utils.get_ffmpeg_encoder", return_value="h264_nvenc"),
        ):
            _compose_video(segments, audio_paths, slide_images, output_path)

            # Should have been called twice: once with h264_nvenc (fails), once with libx264
            assert call_count == 2

    def test_no_retry_when_libx264_fails(self, tmp_path):
        """If libx264 itself fails, exception should propagate (no infinite retry)."""
        from backend.services.video_builder import _compose_video

        segments = [{"slide_num": 1, "text": "Hello"}]
        audio_paths = [str(tmp_path / "a.wav")]
        slide_images = [str(tmp_path / "slide.png")]
        output_path = str(tmp_path / "out.mp4")

        mock_audio_inst = MagicMock()
        mock_audio_inst.duration = 5.0
        mock_img_inst = MagicMock()
        mock_img_inst.resized.return_value = mock_img_inst
        mock_img_inst.with_duration.return_value = mock_img_inst
        mock_img_inst.with_audio.return_value = mock_img_inst
        mock_final = MagicMock()
        mock_final.write_videofile.side_effect = OSError("ffmpeg not found")

        mock_moviepy = MagicMock()
        mock_moviepy.AudioFileClip.return_value = mock_audio_inst
        mock_moviepy.ImageClip.return_value = mock_img_inst
        mock_moviepy.concatenate_videoclips.return_value = mock_final

        with (
            patch.dict("sys.modules", {"moviepy": mock_moviepy}),
            patch("backend.services.gpu_utils.get_ffmpeg_encoder", return_value="libx264"),
        ):
            with pytest.raises(OSError, match="ffmpeg not found"):
                _compose_video(segments, audio_paths, slide_images, output_path)


class TestGetTopicImages:
    def test_returns_topic_images_from_map(self):
        images = ["a.png", "b.png", "c.png", "d.png", "e.png"]
        topic_map = {"T1": [1, 2], "T2": [3, 4]}
        result = _get_topic_images("T1", images, topic_map)
        assert result == ["b.png", "c.png"]

    def test_returns_all_when_no_map(self):
        images = ["a.png", "b.png"]
        result = _get_topic_images("T1", images, None)
        assert result == images

    def test_returns_all_when_topic_not_in_map(self):
        images = ["a.png", "b.png"]
        result = _get_topic_images("Unknown", images, {"T1": [0]})
        assert result == images

    def test_handles_out_of_range_indices(self):
        images = ["a.png", "b.png"]
        result = _get_topic_images("T1", images, {"T1": [0, 5, 10]})
        assert result == ["a.png"]
