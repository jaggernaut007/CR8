"""Tests for ProgressCapture — stdout interception and progress parsing."""

import io
import threading
import time

import pytest

from frontend.app import PipelineCancelledError, ProgressCapture


# ---------------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------------

class TestProgressCaptureInit:

    def test_initial_status_is_running(self):
        cap = ProgressCapture()
        assert cap.status == "running"

    def test_initial_percent_is_zero(self):
        cap = ProgressCapture()
        assert cap.percent == 0

    def test_initial_stage_is_starting(self):
        cap = ProgressCapture()
        assert cap.current_stage == "starting"

    def test_initial_logs_empty(self):
        cap = ProgressCapture()
        assert cap.logs == []

    def test_initial_result_is_none(self):
        cap = ProgressCapture()
        assert cap.result is None

    def test_initial_error_is_none(self):
        cap = ProgressCapture()
        assert cap.error is None


# ---------------------------------------------------------------------------
# get_state() shape
# ---------------------------------------------------------------------------

class TestGetState:

    def test_returns_required_keys(self):
        cap = ProgressCapture()
        state = cap.get_state()
        assert "status" in state
        assert "stage" in state
        assert "percent" in state
        assert "logs" in state
        assert "elapsed" in state

    def test_elapsed_increases(self):
        cap = ProgressCapture()
        time.sleep(0.05)
        state = cap.get_state()
        assert state["elapsed"] >= 0.04

    def test_includes_files_on_complete(self):
        cap = ProgressCapture()
        cap.status = "complete"
        cap.result = {"pdf_path": "", "video_dir": ""}
        state = cap.get_state()
        assert "files" in state

    def test_includes_error_on_error(self):
        cap = ProgressCapture()
        cap.status = "error"
        cap.error = "Something broke"
        state = cap.get_state()
        assert state["error"] == "Something broke"

    def test_logs_capped_at_30(self):
        cap = ProgressCapture()
        for i in range(50):
            cap.logs.append(f"line {i}")
        state = cap.get_state()
        assert len(state["logs"]) == 30
        assert state["logs"][0] == "line 20"  # last 30 of 50


# ---------------------------------------------------------------------------
# Stage parsing — generic [Stage] lines
# ---------------------------------------------------------------------------

class TestStageTransitions:

    def test_ingest_stage(self):
        cap = ProgressCapture()
        cap.write("[Ingest] Starting...\n")
        assert cap.current_stage == "Ingest"
        assert cap.percent == 0  # start of Ingest = 0%

    def test_research_stage(self):
        cap = ProgressCapture()
        cap.write("[Research] Starting...\n")
        assert cap.current_stage == "Research"
        assert cap.percent == 10  # cumulative after Ingest (10%)

    def test_generate_stage(self):
        cap = ProgressCapture()
        cap.write("[Generate] Module 1/5: Topic A\n")
        assert cap.current_stage == "Generate"

    def test_script_stage(self):
        cap = ProgressCapture()
        cap.write("[Script] Converting module to script\n")
        assert cap.current_stage == "Script"
        assert cap.percent == 65  # 10 + 35 + 20 = 65

    def test_video_stage(self):
        cap = ProgressCapture()
        cap.write("[Video] Submitting to HeyGen...\n")
        assert cap.current_stage == "Video"
        assert cap.percent == 75  # 10 + 35 + 20 + 10 = 75

    def test_unknown_bracket_prefix_ignored(self):
        cap = ProgressCapture()
        cap.write("[Unknown] Some message\n")
        assert cap.current_stage == "starting"
        assert cap.percent == 0

    def test_sequential_stage_transitions(self):
        cap = ProgressCapture()
        cap.write("[Ingest] Parsed file.pdf\n")
        assert cap.current_stage == "Ingest"
        cap.write("[Research] Starting...\n")
        assert cap.current_stage == "Research"
        assert cap.percent == 10
        cap.write("[Generate] Starting...\n")
        assert cap.current_stage == "Generate"
        assert cap.percent == 45  # 10 + 35


# ---------------------------------------------------------------------------
# Sub-step progress — Topic X/Y parsing
# ---------------------------------------------------------------------------

class TestSubStepProgress:

    def test_research_topic_progress(self):
        cap = ProgressCapture()
        cap.write("[Research] Topic 4/8: Word Vectors\n")
        assert cap.current_stage == "Research"
        # 10 (Ingest done) + int(35 * 4/8) = 10 + 17 = 27
        assert cap.percent == 27

    def test_research_first_topic(self):
        cap = ProgressCapture()
        cap.write("[Research] Topic 1/10: Basics\n")
        # 10 + int(35 * 1/10) = 10 + 3 = 13
        assert cap.percent == 13

    def test_research_last_topic(self):
        cap = ProgressCapture()
        cap.write("[Research] Topic 10/10: Final\n")
        # 10 + int(35 * 10/10) = 10 + 35 = 45
        assert cap.percent == 45

    def test_generate_module_progress(self):
        cap = ProgressCapture()
        cap.write("[Generate] Module 3/5: Transformers\n")
        # 45 (Ingest+Research) + int(20 * 3/5) = 45 + 12 = 57
        assert cap.percent == 57

    def test_ingest_topic_progress(self):
        """Ingest doesn't typically print Topic X/Y, but if it did, it should work."""
        cap = ProgressCapture()
        cap.write("[Ingest] Topic 2/4: Something\n")
        # 0 (nothing before Ingest) + int(10 * 2/4) = 5
        assert cap.percent == 5

    def test_percent_capped_at_99(self):
        """Progress should never exceed 99% until explicitly set to 100."""
        cap = ProgressCapture()
        cap.write("[Video] Topic 1/1: Done\n")
        assert cap.percent <= 99


# ---------------------------------------------------------------------------
# write() behavior
# ---------------------------------------------------------------------------

class TestWriteBehavior:

    def test_tees_to_original_stdout(self):
        cap = ProgressCapture()
        buf = io.StringIO()
        cap._original_stdout = buf
        cap.write("hello world\n")
        assert "hello world" in buf.getvalue()

    def test_appends_to_logs(self):
        cap = ProgressCapture()
        cap._original_stdout = io.StringIO()  # suppress actual output
        cap.write("[Ingest] Parsed file.pdf — 42 pages\n")
        assert len(cap.logs) == 1
        assert "42 pages" in cap.logs[0]

    def test_multiline_write_splits_correctly(self):
        cap = ProgressCapture()
        cap._original_stdout = io.StringIO()
        cap.write("[Ingest] Line 1\n[Research] Line 2\n")
        assert len(cap.logs) == 2
        assert cap.current_stage == "Research"

    def test_empty_write_ignored(self):
        cap = ProgressCapture()
        cap._original_stdout = io.StringIO()
        cap.write("")
        assert len(cap.logs) == 0

    def test_whitespace_only_write_ignored(self):
        cap = ProgressCapture()
        cap._original_stdout = io.StringIO()
        cap.write("   \n  \n")
        assert len(cap.logs) == 0

    def test_flush_calls_original_flush(self):
        cap = ProgressCapture()
        buf = io.StringIO()
        cap._original_stdout = buf
        cap.flush()  # should not raise


# ---------------------------------------------------------------------------
# Thread safety
# ---------------------------------------------------------------------------

class TestThreadSafety:

    def test_concurrent_writes_dont_crash(self):
        """Multiple threads writing simultaneously should not raise."""
        cap = ProgressCapture()
        cap._original_stdout = io.StringIO()
        errors = []

        def writer(thread_id):
            try:
                for i in range(100):
                    cap.write(f"[Research] Topic {i}/100: Thread {thread_id}\n")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(t,)) for t in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(cap.logs) == 400

    def test_concurrent_get_state_doesnt_crash(self):
        """Reading state while writing should not raise."""
        cap = ProgressCapture()
        cap._original_stdout = io.StringIO()
        errors = []

        def writer():
            try:
                for i in range(200):
                    cap.write(f"[Research] Topic {i}/200: data\n")
            except Exception as e:
                errors.append(e)

        def reader():
            try:
                for _ in range(200):
                    cap.get_state()
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=writer)
        t2 = threading.Thread(target=reader)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert len(errors) == 0


# ---------------------------------------------------------------------------
# Stage-aware ETA fields
# ---------------------------------------------------------------------------

class TestStageTimeBudgets:

    def test_get_state_includes_stage_time_budgets(self):
        cap = ProgressCapture()
        state = cap.get_state()
        assert "stage_time_budgets" in state
        assert state["stage_time_budgets"]["Video"] == 1690

    def test_get_state_includes_stage_elapsed(self):
        cap = ProgressCapture()
        state = cap.get_state()
        assert "stage_elapsed" in state
        assert isinstance(state["stage_elapsed"], float)

    def test_has_video_false_by_default(self):
        cap = ProgressCapture()
        state = cap.get_state()
        assert state["has_video"] is False

    def test_has_video_true_when_formats_set(self):
        cap = ProgressCapture()
        cap.formats = ["pdf", "ppt", "script", "video"]
        state = cap.get_state()
        assert state["has_video"] is True

    def test_stage_elapsed_resets_on_stage_change(self):
        cap = ProgressCapture()
        cap._original_stdout = io.StringIO()
        cap.write("[Ingest] Processing...\n")
        time.sleep(0.05)
        cap.write("[Research] Starting...\n")
        state = cap.get_state()
        # stage_elapsed should be very small since Research just started
        assert state["stage_elapsed"] < 0.2

    def test_stage_start_time_initialized(self):
        cap = ProgressCapture()
        assert hasattr(cap, "stage_start_time")
        assert cap.stage_start_time > 0

    def test_formats_initialized_empty(self):
        cap = ProgressCapture()
        assert cap.formats == []


# ---------------------------------------------------------------------------
# Cancellation
# ---------------------------------------------------------------------------

class TestCancellation:

    def test_cancel_requested_initially_false(self):
        cap = ProgressCapture()
        assert cap.is_cancelled() is False

    def test_request_cancel_sets_flag(self):
        cap = ProgressCapture()
        cap.request_cancel()
        assert cap.is_cancelled() is True

    def test_get_state_shows_cancelling_when_running(self):
        cap = ProgressCapture()
        cap.request_cancel()
        state = cap.get_state()
        assert state["status"] == "cancelling"

    def test_get_state_shows_cancelled_status(self):
        cap = ProgressCapture()
        cap.status = "cancelled"
        cap.error = "Cancelled by user"
        cap.result = {}
        state = cap.get_state()
        assert state["status"] == "cancelled"
        assert state["error"] == "Cancelled by user"

    def test_cancel_at_stage_boundary_raises(self):
        cap = ProgressCapture()
        cap._original_stdout = io.StringIO()
        # Set Ingest as current stage first (without cancel)
        cap.write("[Ingest] Starting...\n")
        assert cap.current_stage == "Ingest"
        # Now request cancel — next stage transition should raise
        cap.request_cancel()
        with pytest.raises(PipelineCancelledError):
            cap.write("[Research] Starting...\n")

    def test_no_cancel_without_request(self):
        """Stage transitions without cancel_requested should NOT raise."""
        cap = ProgressCapture()
        cap._original_stdout = io.StringIO()
        cap.write("[Ingest] Starting...\n")
        cap.write("[Research] Starting...\n")
        cap.write("[Generate] Starting...\n")
        assert cap.current_stage == "Generate"

    def test_cancelled_state_includes_partial_files(self, tmp_path):
        fake_pdf = tmp_path / "guide.pdf"
        fake_pdf.write_bytes(b"%PDF-1.0 partial content")

        cap = ProgressCapture()
        cap.status = "cancelled"
        cap.result = {"pdf_path": str(fake_pdf), "video_dir": ""}
        state = cap.get_state()
        assert state["status"] == "cancelled"
        assert len(state["files"]) == 1
        assert state["files"][0]["type"] == "pdf"


# ---------------------------------------------------------------------------
# GPU progress parsing
# ---------------------------------------------------------------------------

class TestGPUProgressParsing:

    def test_parse_gpu_job_id(self):
        cap = ProgressCapture()
        cap._original_stdout = io.StringIO()
        cap.write("[Video] GPU_JOB_ID: vj_abc123_def456\n")
        assert cap.video_job_id == "vj_abc123_def456"

    def test_parse_gpu_compose_progress(self):
        cap = ProgressCapture()
        cap._original_stdout = io.StringIO()
        cap.write("[Video] GPU_COMPOSE: 3/5\n")
        assert cap.gpu_progress is not None
        assert cap.gpu_progress["completed_videos"] == 3
        assert cap.gpu_progress["total_videos"] == 5

    def test_parse_gpu_tts_progress(self):
        cap = ProgressCapture()
        cap._original_stdout = io.StringIO()
        cap.write("[Video] GPU_TTS: 2/5\n")
        assert cap.gpu_progress is not None
        assert cap.gpu_progress["current_topic"] == 2
        assert cap.gpu_progress["total_topics"] == 5

    def test_parse_gpu_time_with_eta(self):
        cap = ProgressCapture()
        cap._original_stdout = io.StringIO()
        cap.write("[Video] GPU_TIME: elapsed=120 eta=300\n")
        assert cap.gpu_progress is not None
        assert cap.gpu_progress["elapsed_s"] == 120
        assert cap.gpu_progress["eta_s"] == 300

    def test_parse_gpu_time_with_unknown_eta(self):
        cap = ProgressCapture()
        cap._original_stdout = io.StringIO()
        cap.write("[Video] GPU_TIME: elapsed=60 eta=?\n")
        assert cap.gpu_progress is not None
        assert cap.gpu_progress["elapsed_s"] == 60
        assert cap.gpu_progress["eta_s"] is None

    def test_gpu_progress_in_get_state(self):
        cap = ProgressCapture()
        cap._original_stdout = io.StringIO()
        cap.write("[Video] GPU_COMPOSE: 2/5\n")
        cap.write("[Video] GPU_TIME: elapsed=90 eta=200\n")
        state = cap.get_state()
        assert "gpu_progress" in state
        assert state["gpu_progress"]["completed_videos"] == 2
        assert state["gpu_progress"]["elapsed_s"] == 90

    def test_no_gpu_progress_by_default(self):
        cap = ProgressCapture()
        state = cap.get_state()
        assert "gpu_progress" not in state

    def test_video_warning_captured(self):
        cap = ProgressCapture()
        cap._original_stdout = io.StringIO()
        cap.write("[Video] WARNING: Slide 3 missing audio\n")
        assert len(cap.warnings) == 1
        assert "Slide 3" in cap.warnings[0]

    def test_video_error_captured(self):
        cap = ProgressCapture()
        cap._original_stdout = io.StringIO()
        cap.write("[Video] ERROR: ffmpeg failed\n")
        assert len(cap.warnings) == 1
        assert "ffmpeg failed" in cap.warnings[0]
