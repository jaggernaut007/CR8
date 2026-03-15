"""Tests for GPU video worker (job lifecycle)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from gpu_service.worker import get_job, run_video_job, _jobs, _jobs_lock


@pytest.fixture(autouse=True)
def clear_jobs():
    """Reset in-memory job store between tests."""
    with _jobs_lock:
        _jobs.clear()
    yield
    with _jobs_lock:
        _jobs.clear()


@pytest.fixture()
def mock_gcs():
    with patch("gpu_service.worker.GPUGCSClient") as MockGCS:
        mock = MockGCS.return_value
        mock.download_manifest.return_value = {
            "job_id": "test1",
            "topics": [{"name": "Topic A"}],
            "scripts": ["[SLIDE 1]\nHello world."],
            "slide_images": ["slide_001.png"],
            "topic_slide_map": None,
            "config": {"voice": "af_heart", "lang": "a", "fps": 24},
        }
        mock.download_slides.return_value = ["/tmp/slides/slide_001.png"]
        mock.upload_videos.return_value = ["test1/output/01_Topic_A_slide.mp4"]
        yield mock


@pytest.fixture()
def mock_tts():
    """Patch TTSEngine at the source module (lazy import in run_video_job)."""
    with patch("backend.services.tts_engine.TTSEngine") as MockTTS:
        engine = MockTTS.return_value
        engine.synthesize_segments.return_value = ["/tmp/audio/slide_001.wav"]
        yield engine


@pytest.fixture()
def mock_compose():
    """Patch _compose_video at the source module."""
    with patch("backend.services.video_builder._compose_video") as mock:
        mock.return_value = "/tmp/output/01_Topic_A_slide.mp4"
        yield mock


@pytest.fixture()
def mock_parse():
    """Patch parse_script at the source module."""
    with patch("backend.services.script_parser.parse_script") as mock:
        mock.return_value = [{"slide_num": 1, "text": "Hello world."}]
        yield mock


@pytest.fixture()
def mock_slugify():
    """Patch _slugify at the source module."""
    with patch("backend.services.video_builder._slugify", side_effect=lambda n: n.replace(" ", "_")):
        yield


@pytest.fixture()
def mock_get_topic_images():
    """Patch _get_topic_images to return all slide images."""
    with patch(
        "backend.services.video_builder._get_topic_images",
        side_effect=lambda name, imgs, tmap: imgs,
    ):
        yield


class TestRunVideoJob:
    def test_full_lifecycle(
        self, mock_gcs, mock_tts, mock_compose, mock_parse, mock_slugify, mock_get_topic_images
    ):
        run_video_job("vj_test", "gs://bucket/test1")

        job = get_job("vj_test")
        assert job is not None
        assert job["status"] == "complete"
        assert len(job["output_paths"]) == 1

        mock_gcs.download_manifest.assert_called_once()
        mock_gcs.download_slides.assert_called_once()
        mock_gcs.upload_videos.assert_called_once()
        mock_gcs.upload_status.assert_called_once()

    def test_tts_called_with_correct_params(
        self, mock_gcs, mock_tts, mock_compose, mock_parse, mock_slugify, mock_get_topic_images
    ):
        run_video_job("vj_tts", "gs://bucket/test1")
        mock_tts.synthesize_segments.assert_called_once()

    def test_compose_called_after_tts(
        self, mock_gcs, mock_tts, mock_compose, mock_parse, mock_slugify, mock_get_topic_images
    ):
        run_video_job("vj_comp", "gs://bucket/test1")
        mock_compose.assert_called_once()

    def test_error_sets_error_status(self, mock_gcs):
        mock_gcs.download_manifest.side_effect = RuntimeError("GCS unreachable")

        run_video_job("vj_err", "gs://bucket/test1")

        job = get_job("vj_err")
        assert job["status"] == "error"
        assert "GCS unreachable" in job["error"]

    def test_tts_failure_for_one_topic_continues(
        self, mock_gcs, mock_tts, mock_compose, mock_parse, mock_slugify, mock_get_topic_images
    ):
        """When TTS fails for one topic, remaining topics still process."""
        mock_gcs.download_manifest.return_value = {
            "job_id": "test2",
            "topics": [{"name": "Topic A"}, {"name": "Topic B"}],
            "scripts": ["[SLIDE 1]\nA.", "[SLIDE 1]\nB."],
            "slide_images": ["slide_001.png", "slide_002.png"],
            "topic_slide_map": None,
            "config": {},
        }
        mock_gcs.download_slides.return_value = ["/tmp/s/slide_001.png", "/tmp/s/slide_002.png"]

        mock_tts.synthesize_segments.side_effect = [
            ["/tmp/audio1.wav"],
            RuntimeError("TTS OOM"),
        ]

        run_video_job("vj_partial", "gs://bucket/test2")

        job = get_job("vj_partial")
        assert job["status"] == "complete"
        assert "warnings" in job

    def test_progress_updates_during_tts(
        self, mock_gcs, mock_tts, mock_compose, mock_parse, mock_slugify, mock_get_topic_images
    ):
        run_video_job("vj_prog", "gs://bucket/test1")

        job = get_job("vj_prog")
        assert job["progress"]["phase"] == "complete"
        assert job["progress"]["percent"] == 100

    def test_pptx_export_called_when_manifest_has_pptx_name_and_no_slides(
        self, mock_gcs, mock_tts, mock_compose, mock_parse, mock_slugify, mock_get_topic_images
    ):
        """When manifest has pptx_name and empty slide_images, _export_slides_from_pptx is used."""
        mock_gcs.download_manifest.return_value = {
            "job_id": "pptx_job",
            "topics": [{"name": "Topic A"}],
            "scripts": ["[SLIDE 1]\nHello."],
            "slide_images": [],
            "pptx_name": "deck.pptx",
            "topic_slide_map": None,
            "config": {},
        }
        mock_gcs.download_pptx.return_value = "/tmp/workdir/deck.pptx"

        with patch("gpu_service.worker._export_slides_from_pptx") as mock_export:
            mock_export.return_value = ["/tmp/slides/slide_001.png"]
            run_video_job("vj_pptx", "gs://bucket/pptx_job")

        mock_export.assert_called_once()

    def test_regular_slide_download_used_when_slide_images_present(
        self, mock_gcs, mock_tts, mock_compose, mock_parse, mock_slugify, mock_get_topic_images
    ):
        """When manifest has both slide_images and pptx_name, regular download is used (not PPTX export)."""
        mock_gcs.download_manifest.return_value = {
            "job_id": "both_job",
            "topics": [{"name": "Topic A"}],
            "scripts": ["[SLIDE 1]\nHello."],
            "slide_images": ["slide_001.png"],
            "pptx_name": "deck.pptx",
            "topic_slide_map": None,
            "config": {},
        }
        mock_gcs.download_slides.return_value = ["/tmp/slides/slide_001.png"]

        with patch("gpu_service.worker._export_slides_from_pptx") as mock_export:
            run_video_job("vj_both", "gs://bucket/both_job")

        mock_gcs.download_slides.assert_called_once()
        mock_export.assert_not_called()


class TestGetJob:
    def test_returns_none_for_unknown(self):
        assert get_job("nonexistent") is None

    def test_returns_copy_not_reference(
        self, mock_gcs, mock_tts, mock_compose, mock_parse, mock_slugify, mock_get_topic_images
    ):
        run_video_job("vj_copy", "gs://bucket/test1")
        job1 = get_job("vj_copy")
        job2 = get_job("vj_copy")
        assert job1 is not job2
        assert job1 == job2
