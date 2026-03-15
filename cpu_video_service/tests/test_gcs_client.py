"""Tests for CPUGCSClient and _strip_gs_prefix.

All GCS API calls are mocked via MagicMock — no real Google Cloud credentials
are required or used.
"""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from cpu_video_service.gcs_client import CPUGCSClient, _strip_gs_prefix


# ---------------------------------------------------------------------------
# _strip_gs_prefix
# ---------------------------------------------------------------------------


class TestStripGsPrefix:
    def test_strips_gs_scheme_and_bucket(self):
        assert _strip_gs_prefix("gs://my-bucket/jobs/abc123") == "jobs/abc123"

    def test_strips_bucket_only_no_path(self):
        # gs://bucket with no trailing path gives empty string
        assert _strip_gs_prefix("gs://my-bucket") == ""

    def test_passthrough_when_no_gs_prefix(self):
        assert _strip_gs_prefix("jobs/abc123") == "jobs/abc123"

    def test_handles_deep_path(self):
        assert _strip_gs_prefix("gs://cr8-jobs/org/course/run/job_x") == "org/course/run/job_x"

    def test_handles_empty_string(self):
        assert _strip_gs_prefix("") == ""


# ---------------------------------------------------------------------------
# CPUGCSClient fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_storage():
    """Patch google.cloud.storage.Client so no real GCS call is made."""
    with patch("google.cloud.storage.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_bucket = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.bucket.return_value = mock_bucket
        yield mock_bucket


@pytest.fixture()
def gcs(mock_storage):
    """Return a CPUGCSClient whose underlying bucket is fully mocked."""
    return CPUGCSClient("cr8-jobs")


# ---------------------------------------------------------------------------
# download_manifest
# ---------------------------------------------------------------------------


class TestDownloadManifest:
    def test_returns_parsed_json(self, gcs, mock_storage, tmp_path):
        manifest_data = {"job_id": "abc", "topics": [{"name": "Topic A"}]}

        def _write_manifest(local_path):
            with open(local_path, "w") as f:
                json.dump(manifest_data, f)

        mock_blob = MagicMock()
        mock_blob.download_to_filename.side_effect = _write_manifest
        mock_storage.blob.return_value = mock_blob

        result = gcs.download_manifest("gs://cr8-jobs/abc", str(tmp_path))

        assert result["job_id"] == "abc"
        assert result["topics"][0]["name"] == "Topic A"

    def test_uses_correct_blob_path(self, gcs, mock_storage, tmp_path):
        manifest_data = {"job_id": "xyz"}

        def _write(local_path):
            with open(local_path, "w") as f:
                json.dump(manifest_data, f)

        mock_blob = MagicMock()
        mock_blob.download_to_filename.side_effect = _write
        mock_storage.blob.return_value = mock_blob

        gcs.download_manifest("gs://cr8-jobs/xyz", str(tmp_path))

        mock_storage.blob.assert_called_once_with("xyz/input/manifest.json")

    def test_wraps_gcs_error_in_runtime_error(self, gcs, mock_storage, tmp_path):
        mock_blob = MagicMock()
        mock_blob.download_to_filename.side_effect = Exception("403 Forbidden")
        mock_storage.blob.return_value = mock_blob

        with pytest.raises(RuntimeError, match="GCS manifest download failed"):
            gcs.download_manifest("gs://cr8-jobs/abc", str(tmp_path))

    def test_error_message_includes_gcs_prefix(self, gcs, mock_storage, tmp_path):
        mock_blob = MagicMock()
        mock_blob.download_to_filename.side_effect = Exception("boom")
        mock_storage.blob.return_value = mock_blob

        with pytest.raises(RuntimeError, match="gs://cr8-jobs/abc"):
            gcs.download_manifest("gs://cr8-jobs/abc", str(tmp_path))


# ---------------------------------------------------------------------------
# download_slides
# ---------------------------------------------------------------------------


class TestDownloadSlides:
    def test_returns_local_paths(self, gcs, mock_storage, tmp_path):
        mock_blob = MagicMock()
        mock_storage.blob.return_value = mock_blob
        slide_dir = str(tmp_path / "slides")

        result = gcs.download_slides(
            "gs://cr8-jobs/abc", ["slide_001.png", "slide_002.png"], slide_dir
        )

        assert len(result) == 2
        assert result[0].endswith("slide_001.png")
        assert result[1].endswith("slide_002.png")

    def test_downloads_each_slide(self, gcs, mock_storage, tmp_path):
        mock_blob = MagicMock()
        mock_storage.blob.return_value = mock_blob
        slide_dir = str(tmp_path / "slides")

        gcs.download_slides("gs://cr8-jobs/abc", ["a.png", "b.png", "c.png"], slide_dir)

        assert mock_blob.download_to_filename.call_count == 3

    def test_creates_local_dir(self, gcs, mock_storage, tmp_path):
        mock_blob = MagicMock()
        mock_storage.blob.return_value = mock_blob
        slide_dir = str(tmp_path / "new_dir" / "slides")

        gcs.download_slides("gs://cr8-jobs/abc", ["slide_001.png"], slide_dir)

        assert os.path.isdir(slide_dir)

    def test_empty_slide_list_returns_empty(self, gcs, mock_storage, tmp_path):
        slide_dir = str(tmp_path / "slides")
        result = gcs.download_slides("gs://cr8-jobs/abc", [], slide_dir)
        assert result == []

    def test_wraps_gcs_error_in_runtime_error(self, gcs, mock_storage, tmp_path):
        mock_blob = MagicMock()
        mock_blob.download_to_filename.side_effect = Exception("Network error")
        mock_storage.blob.return_value = mock_blob

        with pytest.raises(RuntimeError, match="GCS slide download failed"):
            gcs.download_slides("gs://cr8-jobs/abc", ["slide.png"], str(tmp_path))


# ---------------------------------------------------------------------------
# download_pptx
# ---------------------------------------------------------------------------


class TestDownloadPptx:
    def test_returns_local_path(self, gcs, mock_storage, tmp_path):
        """download_pptx returns the local file path where the PPTX was saved."""
        mock_blob = MagicMock()
        mock_storage.blob.return_value = mock_blob

        result = gcs.download_pptx("gs://cr8-jobs/abc", "deck.pptx", str(tmp_path))

        assert result == os.path.join(str(tmp_path), "deck.pptx")

    def test_downloads_correct_blob(self, gcs, mock_storage, tmp_path):
        """download_pptx fetches the blob at {prefix}/input/{pptx_name}."""
        mock_blob = MagicMock()
        mock_storage.blob.return_value = mock_blob

        gcs.download_pptx("gs://cr8-jobs/abc", "deck.pptx", str(tmp_path))

        mock_storage.blob.assert_called_once_with("abc/input/deck.pptx")

    def test_uses_basename_for_safety(self, gcs, mock_storage, tmp_path):
        """download_pptx uses os.path.basename on pptx_name to prevent path traversal."""
        mock_blob = MagicMock()
        mock_storage.blob.return_value = mock_blob

        # pptx_name contains a directory component — only the basename should be used
        result = gcs.download_pptx("gs://cr8-jobs/abc", "subdir/deck.pptx", str(tmp_path))

        # Local path must use basename only
        assert os.path.basename(result) == "deck.pptx"
        # Blob path must also use basename only
        mock_storage.blob.assert_called_once_with("abc/input/deck.pptx")

    def test_creates_local_dir_if_missing(self, gcs, mock_storage, tmp_path):
        """download_pptx creates the local_dir if it does not exist."""
        mock_blob = MagicMock()
        mock_storage.blob.return_value = mock_blob

        new_dir = str(tmp_path / "new_subdir")
        gcs.download_pptx("gs://cr8-jobs/abc", "deck.pptx", new_dir)

        assert os.path.isdir(new_dir)

    def test_calls_download_to_filename(self, gcs, mock_storage, tmp_path):
        """download_pptx delegates the actual download to blob.download_to_filename."""
        mock_blob = MagicMock()
        mock_storage.blob.return_value = mock_blob

        expected_path = os.path.join(str(tmp_path), "deck.pptx")
        gcs.download_pptx("gs://cr8-jobs/abc", "deck.pptx", str(tmp_path))

        mock_blob.download_to_filename.assert_called_once_with(expected_path)

    def test_wraps_gcs_error_in_runtime_error(self, gcs, mock_storage, tmp_path):
        """GCS errors are re-raised as RuntimeError."""
        mock_blob = MagicMock()
        mock_blob.download_to_filename.side_effect = Exception("403 Forbidden")
        mock_storage.blob.return_value = mock_blob

        with pytest.raises(RuntimeError, match="GCS PPTX download failed"):
            gcs.download_pptx("gs://cr8-jobs/abc", "deck.pptx", str(tmp_path))

    def test_error_message_includes_gcs_prefix(self, gcs, mock_storage, tmp_path):
        """The RuntimeError message includes the original GCS prefix for debugging."""
        mock_blob = MagicMock()
        mock_blob.download_to_filename.side_effect = Exception("timeout")
        mock_storage.blob.return_value = mock_blob

        with pytest.raises(RuntimeError, match="gs://cr8-jobs/abc"):
            gcs.download_pptx("gs://cr8-jobs/abc", "deck.pptx", str(tmp_path))


# ---------------------------------------------------------------------------
# upload_videos
# ---------------------------------------------------------------------------


class TestUploadVideos:
    def test_returns_gcs_blob_names(self, gcs, mock_storage, tmp_path):
        mock_blob = MagicMock()
        mock_storage.blob.return_value = mock_blob

        # Create real temp files so os.path.basename works
        f1 = tmp_path / "01_Topic_A.mp4"
        f2 = tmp_path / "02_Topic_B.mp4"
        f1.write_bytes(b"fake")
        f2.write_bytes(b"fake")

        result = gcs.upload_videos("gs://cr8-jobs/abc", [str(f1), str(f2)])

        assert len(result) == 2
        assert result[0] == "abc/output/01_Topic_A.mp4"
        assert result[1] == "abc/output/02_Topic_B.mp4"

    def test_uploads_with_video_content_type(self, gcs, mock_storage, tmp_path):
        mock_blob = MagicMock()
        mock_storage.blob.return_value = mock_blob

        f = tmp_path / "vid.mp4"
        f.write_bytes(b"fake")

        gcs.upload_videos("gs://cr8-jobs/abc", [str(f)])

        mock_blob.upload_from_filename.assert_called_once_with(
            str(f), content_type="video/mp4"
        )

    def test_empty_list_returns_empty(self, gcs, mock_storage):
        result = gcs.upload_videos("gs://cr8-jobs/abc", [])
        assert result == []

    def test_wraps_gcs_error_in_runtime_error(self, gcs, mock_storage, tmp_path):
        mock_blob = MagicMock()
        mock_blob.upload_from_filename.side_effect = Exception("Upload failed")
        mock_storage.blob.return_value = mock_blob

        f = tmp_path / "vid.mp4"
        f.write_bytes(b"fake")

        with pytest.raises(RuntimeError, match="GCS video upload failed"):
            gcs.upload_videos("gs://cr8-jobs/abc", [str(f)])


# ---------------------------------------------------------------------------
# upload_status
# ---------------------------------------------------------------------------


class TestUploadStatus:
    def test_uploads_json_string(self, gcs, mock_storage):
        mock_blob = MagicMock()
        mock_storage.blob.return_value = mock_blob

        status = {"video_job_id": "vj_1", "status": "complete"}
        gcs.upload_status("gs://cr8-jobs/abc", status)

        mock_blob.upload_from_string.assert_called_once()
        call_args = mock_blob.upload_from_string.call_args
        payload = json.loads(call_args[0][0])
        assert payload["status"] == "complete"

    def test_uses_correct_blob_path(self, gcs, mock_storage):
        mock_blob = MagicMock()
        mock_storage.blob.return_value = mock_blob

        gcs.upload_status("gs://cr8-jobs/abc", {"status": "error"})

        mock_storage.blob.assert_called_once_with("abc/output/status.json")

    def test_content_type_is_json(self, gcs, mock_storage):
        mock_blob = MagicMock()
        mock_storage.blob.return_value = mock_blob

        gcs.upload_status("gs://cr8-jobs/abc", {"status": "ok"})

        call_kwargs = mock_blob.upload_from_string.call_args[1]
        assert call_kwargs["content_type"] == "application/json"

    def test_wraps_gcs_error_in_runtime_error(self, gcs, mock_storage):
        mock_blob = MagicMock()
        mock_blob.upload_from_string.side_effect = Exception("Quota exceeded")
        mock_storage.blob.return_value = mock_blob

        with pytest.raises(RuntimeError, match="GCS status upload failed"):
            gcs.upload_status("gs://cr8-jobs/abc", {"status": "ok"})
