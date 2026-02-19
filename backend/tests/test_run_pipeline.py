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
                result = run_job(["/tmp/fake.pdf"], [fmt])
                assert mock_pipeline.invoke.called

    def test_video_format_requires_heygen_keys(self):
        """Requesting video without HeyGen env vars should raise ValueError."""
        with patch("backend.run_pipeline.settings") as mock_settings:
            mock_settings.heygen_api_key = ""
            mock_settings.heygen_avatar_id = ""
            mock_settings.heygen_voice_id = ""
            with pytest.raises(ValueError, match="Video requires"):
                run_job(["/tmp/fake.pdf"], ["video"])

    def test_video_format_missing_partial_keys(self):
        """Even if some HeyGen keys are set, all three are required."""
        with patch("backend.run_pipeline.settings") as mock_settings:
            mock_settings.heygen_api_key = "key123"
            mock_settings.heygen_avatar_id = ""
            mock_settings.heygen_voice_id = ""
            with pytest.raises(ValueError, match="HEYGEN_AVATAR_ID"):
                run_job(["/tmp/fake.pdf"], ["video"])

    def test_video_format_with_all_keys_proceeds(self):
        """With all HeyGen keys set, video format should proceed to pipeline."""
        with patch("backend.run_pipeline.settings") as mock_settings, \
             patch("backend.run_pipeline.build_pipeline") as mock_build:
            mock_settings.heygen_api_key = "key"
            mock_settings.heygen_avatar_id = "avatar"
            mock_settings.heygen_voice_id = "voice"
            mock_settings.output_formats = []
            mock_pipeline = MagicMock()
            mock_pipeline.invoke.return_value = {"pdf_path": "", "video_dir": ""}
            mock_build.return_value = mock_pipeline
            run_job(["/tmp/fake.pdf"], ["video"])
            assert mock_pipeline.invoke.called


# ---------------------------------------------------------------------------
# Pipeline invocation
# ---------------------------------------------------------------------------

class TestRunJobPipelineInvocation:

    def test_sets_output_formats_on_settings(self):
        """run_job should set settings.output_formats before invoking pipeline."""
        with patch("backend.run_pipeline.build_pipeline") as mock_build, \
             patch("backend.run_pipeline.settings") as mock_settings:
            mock_settings.heygen_api_key = ""
            mock_pipeline = MagicMock()
            mock_pipeline.invoke.return_value = {"pdf_path": "/out.pdf"}
            mock_build.return_value = mock_pipeline
            run_job(["/tmp/test.pdf"], ["pdf", "script"])
            assert mock_settings.output_formats == ["pdf", "script"]

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
