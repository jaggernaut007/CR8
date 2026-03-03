"""Tests for ProgressCapture — stdout interception and progress parsing."""

import io
import threading
import time

from frontend.app import ProgressCapture


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
        assert cap.percent == 15  # cumulative after Ingest (15%)

    def test_generate_stage(self):
        cap = ProgressCapture()
        cap.write("[Generate] Module 1/5: Topic A\n")
        assert cap.current_stage == "Generate"

    def test_script_stage(self):
        cap = ProgressCapture()
        cap.write("[Script] Converting module to script\n")
        assert cap.current_stage == "Script"
        assert cap.percent == 90  # 15 + 50 + 25 = 90

    def test_video_stage(self):
        cap = ProgressCapture()
        cap.write("[Video] Submitting to HeyGen...\n")
        assert cap.current_stage == "Video"
        assert cap.percent == 98  # 15 + 50 + 25 + 8 = 98

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
        assert cap.percent == 15
        cap.write("[Generate] Starting...\n")
        assert cap.current_stage == "Generate"
        assert cap.percent == 65  # 15 + 50


# ---------------------------------------------------------------------------
# Sub-step progress — Topic X/Y parsing
# ---------------------------------------------------------------------------

class TestSubStepProgress:

    def test_research_topic_progress(self):
        cap = ProgressCapture()
        cap.write("[Research] Topic 4/8: Word Vectors\n")
        assert cap.current_stage == "Research"
        # 15 (Ingest done) + int(50 * 4/8) = 15 + 25 = 40
        assert cap.percent == 40

    def test_research_first_topic(self):
        cap = ProgressCapture()
        cap.write("[Research] Topic 1/10: Basics\n")
        # 15 + int(50 * 1/10) = 15 + 5 = 20
        assert cap.percent == 20

    def test_research_last_topic(self):
        cap = ProgressCapture()
        cap.write("[Research] Topic 10/10: Final\n")
        # 15 + int(50 * 10/10) = 15 + 50 = 65
        assert cap.percent == 65

    def test_generate_module_progress(self):
        cap = ProgressCapture()
        cap.write("[Generate] Module 3/5: Transformers\n")
        # 65 (Ingest+Research) + int(25 * 3/5) = 65 + 15 = 80
        assert cap.percent == 80

    def test_ingest_topic_progress(self):
        """Ingest doesn't typically print Topic X/Y, but if it did, it should work."""
        cap = ProgressCapture()
        cap.write("[Ingest] Topic 2/4: Something\n")
        # 0 (nothing before Ingest) + int(15 * 2/4) = 7
        assert cap.percent == 7

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
