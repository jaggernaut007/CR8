"""Tests for CPU video worker (job lifecycle)."""

from __future__ import annotations

import threading
from unittest.mock import patch

import pytest

from cpu_video_service.worker import (
    _cancel_events,
    _estimate_eta,
    _is_cancelled,
    _jobs,
    _jobs_lock,
    cancel_job,
    get_job,
    run_video_job,
)


@pytest.fixture(autouse=True)
def clear_jobs():
    """Reset in-memory job store and cancel events between tests."""
    with _jobs_lock:
        _jobs.clear()
    _cancel_events.clear()
    yield
    with _jobs_lock:
        _jobs.clear()
    _cancel_events.clear()


@pytest.fixture()
def mock_gcs():
    with patch("cpu_video_service.worker.CPUGCSClient") as MockGCS:
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
    """Patch TTSEngine at the source module (lazy import in worker)."""
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

    def test_tts_called(
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

    def test_no_slides_sets_error_status(self, mock_gcs):
        """If GCS returns zero slide images, the job ends with error status."""
        mock_gcs.download_slides.return_value = []

        run_video_job("vj_noslides", "gs://bucket/test1")

        job = get_job("vj_noslides")
        assert job["status"] == "error"
        assert "slide" in job["error"].lower()

    def test_scripts_padded_when_fewer_than_topics(
        self, mock_gcs, mock_tts, mock_compose, mock_parse, mock_slugify, mock_get_topic_images
    ):
        """When fewer scripts than topics, the last script is repeated (no crash)."""
        mock_gcs.download_manifest.return_value = {
            "job_id": "pad",
            "topics": [{"name": "A"}, {"name": "B"}, {"name": "C"}],
            "scripts": ["[SLIDE 1]\nOnly script."],
            "slide_images": ["slide_001.png"],
            "topic_slide_map": None,
            "config": {},
        }
        mock_gcs.download_slides.return_value = ["/tmp/s.png"]

        run_video_job("vj_pad", "gs://bucket/pad")

        job = get_job("vj_pad")
        assert job is not None
        assert job["status"] == "complete"

    def test_error_status_uploaded_to_gcs(self, mock_gcs):
        """On failure, error status dict is uploaded to GCS."""
        mock_gcs.download_manifest.side_effect = RuntimeError("fail")

        run_video_job("vj_upload_err", "gs://bucket/test1")

        mock_gcs.upload_status.assert_called_once()
        uploaded = mock_gcs.upload_status.call_args[0][1]
        assert uploaded["status"] == "error"

    def test_error_upload_status_failure_is_silent(self, mock_gcs):
        """If GCS upload_status itself throws during error handling, no exception escapes."""
        mock_gcs.download_manifest.side_effect = RuntimeError("fail")
        mock_gcs.upload_status.side_effect = Exception("GCS also down")

        # Must not raise — second exception is swallowed with a warning
        run_video_job("vj_double_fail", "gs://bucket/test1")

        job = get_job("vj_double_fail")
        assert job["status"] == "error"

    def test_cancel_event_cleaned_up_after_completion(
        self, mock_gcs, mock_tts, mock_compose, mock_parse, mock_slugify, mock_get_topic_images
    ):
        """The per-job cancel event is removed from _cancel_events when the job finishes."""
        run_video_job("vj_cleanup", "gs://bucket/test1")
        assert "vj_cleanup" not in _cancel_events


class TestCancellationFlow:
    def test_cancellation_during_tts_sets_cancelled_status(
        self, mock_gcs, mock_tts, mock_compose, mock_parse, mock_slugify, mock_get_topic_images
    ):
        """Patching _is_cancelled to return True causes the TTS loop to raise InterruptedError."""
        with patch("cpu_video_service.worker._is_cancelled", return_value=True):
            run_video_job("vj_cancel_tts", "gs://bucket/test1")

        job = get_job("vj_cancel_tts")
        assert job is not None
        assert job["status"] == "cancelled"

    def test_cancellation_before_compose_sets_cancelled_status(
        self, mock_gcs, mock_tts, mock_compose, mock_parse, mock_slugify, mock_get_topic_images
    ):
        """Cancel check at the start of _phase_compose raises InterruptedError."""
        # First call (_is_cancelled inside TTS loop) returns False,
        # second call (start of _phase_compose) returns True.
        with patch("cpu_video_service.worker._is_cancelled", side_effect=[False, True]):
            run_video_job("vj_cancel_compose", "gs://bucket/test1")

        job = get_job("vj_cancel_compose")
        assert job["status"] == "cancelled"

    def test_cancel_status_uploaded_to_gcs_on_cancellation(
        self, mock_gcs, mock_tts, mock_compose, mock_parse, mock_slugify, mock_get_topic_images
    ):
        """When a job is cancelled, cancel status is persisted to GCS."""
        with patch("cpu_video_service.worker._is_cancelled", return_value=True):
            run_video_job("vj_gcs_cancel", "gs://bucket/test1")

        mock_gcs.upload_status.assert_called()
        uploaded = mock_gcs.upload_status.call_args[0][1]
        assert uploaded["status"] == "cancelled"

    def test_cancel_gcs_upload_failure_is_silent(
        self, mock_gcs, mock_tts, mock_compose, mock_parse, mock_slugify, mock_get_topic_images
    ):
        """If GCS upload_status throws during cancellation handling, no exception propagates."""
        mock_gcs.upload_status.side_effect = Exception("GCS down")

        with patch("cpu_video_service.worker._is_cancelled", return_value=True):
            run_video_job("vj_cancel_upload_fail", "gs://bucket/test1")

        job = get_job("vj_cancel_upload_fail")
        assert job["status"] == "cancelled"

    def test_cancel_event_cleaned_up_after_cancellation(
        self, mock_gcs, mock_tts, mock_compose, mock_parse, mock_slugify, mock_get_topic_images
    ):
        """The per-job cancel event is removed from _cancel_events even after cancellation."""
        with patch("cpu_video_service.worker._is_cancelled", return_value=True):
            run_video_job("vj_cancel_cleanup", "gs://bucket/test1")

        assert "vj_cancel_cleanup" not in _cancel_events


class TestCancelJob:
    def test_cancel_known_job_returns_true(self):
        """cancel_job returns True and sets the event for a known running job."""
        evt = threading.Event()
        _cancel_events["vj_cancel"] = evt
        with _jobs_lock:
            _jobs["vj_cancel"] = {"video_job_id": "vj_cancel", "status": "tts"}

        assert cancel_job("vj_cancel") is True
        assert evt.is_set()

    def test_cancel_known_job_sets_status_to_cancelling(self):
        """cancel_job updates the in-memory job status to 'cancelling'."""
        evt = threading.Event()
        _cancel_events["vj_status"] = evt
        with _jobs_lock:
            _jobs["vj_status"] = {"video_job_id": "vj_status", "status": "tts"}

        cancel_job("vj_status")

        assert get_job("vj_status")["status"] == "cancelling"

    def test_cancel_unknown_job_returns_false(self):
        """cancel_job returns False when no cancel event exists for the given ID."""
        assert cancel_job("nonexistent") is False


class TestIsCancelled:
    def test_returns_false_when_no_event_registered(self):
        assert _is_cancelled("nonexistent") is False

    def test_returns_false_when_event_exists_but_not_set(self):
        _cancel_events["vj_unset"] = threading.Event()
        assert _is_cancelled("vj_unset") is False

    def test_returns_true_when_event_is_set(self):
        evt = threading.Event()
        evt.set()
        _cancel_events["vj_set"] = evt
        assert _is_cancelled("vj_set") is True


class TestEstimateEta:
    def test_returns_none_when_pct_is_zero(self):
        assert _estimate_eta(0, 100) is None

    def test_returns_none_when_pct_is_negative(self):
        assert _estimate_eta(-5, 100) is None

    def test_returns_integer_remaining_seconds(self):
        # 50% done in 50s → 50s remaining
        assert _estimate_eta(50, 50) == 50

    def test_returns_zero_when_fully_complete(self):
        # 100% done → 0s remaining
        assert _estimate_eta(100, 200) == 0

    def test_proportional_estimate(self):
        # 25% done in 100s → 300s remaining
        assert _estimate_eta(25, 100) == 300


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
