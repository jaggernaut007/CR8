"""Tests for the run_job() programmatic pipeline entry point."""

from unittest.mock import patch, MagicMock

import pytest

from backend.run_pipeline import run_job, VALID_FORMATS


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

class TestRunJobValidation:

    def test_rejects_invalid_format(self):
        with pytest.raises(ValueError, match="Invalid format"):
            run_job(["/tmp/fake.pdf"], ["pdf", "banana"])

    def test_rejects_completely_unknown_format(self):
        with pytest.raises(ValueError, match="Invalid format"):
            run_job(["/tmp/fake.pdf"], ["docx"])

    def test_accepts_all_valid_formats(self):
        """Each format string in VALID_FORMATS should be accepted (pipeline mocked)."""
        for fmt in VALID_FORMATS:
            if fmt == "video":
                continue  # video needs HeyGen keys, tested separately
            with patch("backend.run_pipeline.build_pipeline") as mock_build:
                mock_pipeline = MagicMock()
                mock_pipeline.invoke.return_value = {"pdf_path": "", "video_dir": ""}
                mock_build.return_value = mock_pipeline
                run_job(["/tmp/fake.pdf"], [fmt])
                assert mock_pipeline.invoke.called

    def test_video_format_rejected(self):
        """Video format is not yet implemented — run_job must reject it immediately."""
        with pytest.raises(ValueError, match="not yet available"):
            run_job(["/tmp/fake.pdf"], ["video"])

    def test_video_format_rejected_regardless_of_keys(self):
        """Video rejection happens before any API key check — no settings mutation."""
        with patch("backend.run_pipeline.build_pipeline") as mock_build:
            mock_pipeline = MagicMock()
            mock_build.return_value = mock_pipeline
            with pytest.raises(ValueError, match="not yet available"):
                run_job(["/tmp/fake.pdf"], ["pdf", "video"])
            mock_pipeline.invoke.assert_not_called()


# ---------------------------------------------------------------------------
# Pipeline invocation
# ---------------------------------------------------------------------------

class TestRunJobPipelineInvocation:

    def test_output_formats_passed_in_state(self):
        """run_job must pass output_formats in initial_state, not via settings mutation."""
        with patch("backend.run_pipeline.build_pipeline") as mock_build:
            mock_pipeline = MagicMock()
            mock_pipeline.invoke.return_value = {"pdf_path": "/out.pdf"}
            mock_build.return_value = mock_pipeline
            run_job(["/tmp/test.pdf"], ["pdf", "script"])
            call_state = mock_pipeline.invoke.call_args[0][0]
            assert call_state["output_formats"] == "pdf,script"

    def test_invokes_pipeline_with_correct_state_shape(self):
        """The initial_state passed to pipeline.invoke should have all required keys."""
        with patch("backend.run_pipeline.build_pipeline") as mock_build:
            mock_pipeline = MagicMock()
            mock_pipeline.invoke.return_value = {}
            mock_build.return_value = mock_pipeline
            run_job(["/tmp/a.pdf", "/tmp/b.pdf"], ["pdf"])

            call_args = mock_pipeline.invoke.call_args[0][0]
            assert "job_id" in call_args
            assert call_args["file_paths"] == ["/tmp/a.pdf", "/tmp/b.pdf"]
            assert call_args["topics"] == []
            assert call_args["raw_text"] == ""
            assert call_args["curriculum_scope"] == ""
            assert call_args["gap_summary"] == []
            assert call_args["pdf_path"] == ""
            assert call_args["video_dir"] == ""
            assert call_args["output_formats"] == "pdf"
            assert call_args["current_stage"] == "starting"

    def test_returns_pipeline_result(self):
        """run_job should return whatever pipeline.invoke returns."""
        fake_result = {
            "topics": [{"name": "T1"}],
            "pdf_path": "/outputs/guide.pdf",
            "video_dir": "",
        }
        with patch("backend.run_pipeline.build_pipeline") as mock_build:
            mock_pipeline = MagicMock()
            mock_pipeline.invoke.return_value = fake_result
            mock_build.return_value = mock_pipeline
            result = run_job(["/tmp/test.pdf"], ["pdf"])
            assert result == fake_result

    def test_generates_unique_job_ids(self):
        """Each call to run_job should produce a different job_id."""
        job_ids = []
        with patch("backend.run_pipeline.build_pipeline") as mock_build:
            mock_pipeline = MagicMock()
            mock_pipeline.invoke.side_effect = lambda state: state
            mock_build.return_value = mock_pipeline
            for _ in range(5):
                result = run_job(["/tmp/test.pdf"], ["pdf"])
                job_ids.append(result["job_id"])
        assert len(set(job_ids)) == 5
