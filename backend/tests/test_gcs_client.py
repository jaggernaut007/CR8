"""Tests for GCS video client (CPU ↔ GPU data transfer)."""

from __future__ import annotations

import json
import os
import sys
import types
from unittest.mock import MagicMock, patch

import pytest

# Ensure google.cloud.storage is importable even without the real package.
# GCSVideoClient does a lazy `from google.cloud import storage` in __init__,
# so we need the module path to exist in sys.modules.
if "google.cloud.storage" not in sys.modules:
    _google = types.ModuleType("google")
    _google.__path__ = []
    _google_cloud = types.ModuleType("google.cloud")
    _google_cloud.__path__ = []
    _google.cloud = _google_cloud
    _google_cloud_storage = types.ModuleType("google.cloud.storage")
    _google_cloud_storage.Client = MagicMock()
    _google_cloud.storage = _google_cloud_storage
    sys.modules.setdefault("google", _google)
    sys.modules.setdefault("google.cloud", _google_cloud)
    sys.modules.setdefault("google.cloud.storage", _google_cloud_storage)


@pytest.fixture()
def mock_storage():
    """Patch google.cloud.storage.Client and return (mock_client, mock_bucket)."""
    with patch("backend.services.gcs_client.settings") as mock_settings:
        mock_settings.gcs_bucket = "test-bucket"
        with patch("google.cloud.storage.Client") as MockClient:
            mock_client = MockClient.return_value
            mock_bucket = MagicMock()
            mock_bucket.name = "test-bucket"
            mock_client.bucket.return_value = mock_bucket
            yield mock_client, mock_bucket


@pytest.fixture()
def gcs_client(mock_storage):
    from backend.services.gcs_client import GCSVideoClient

    return GCSVideoClient(bucket_name="test-bucket")


class TestUploadJobInputs:
    def test_uploads_manifest_and_slides(self, gcs_client, mock_storage, tmp_path):
        _, mock_bucket = mock_storage
        mock_blob = MagicMock()
        mock_bucket.blob.return_value = mock_blob

        # Create fake slide images
        slide1 = tmp_path / "slide_001.png"
        slide2 = tmp_path / "slide_002.png"
        slide1.write_bytes(b"PNG1")
        slide2.write_bytes(b"PNG2")

        manifest = {"job_id": "abc", "scripts": ["hello"], "slide_images": ["slide_001.png"]}

        result = gcs_client.upload_job_inputs(
            "abc", [str(slide1), str(slide2)], manifest
        )

        assert result == "gs://test-bucket/abc"
        # Should create blobs for manifest + 2 slides = 3 blob() calls
        assert mock_bucket.blob.call_count == 3
        mock_bucket.blob.assert_any_call("abc/input/manifest.json")
        mock_bucket.blob.assert_any_call("abc/input/slide_001.png")
        mock_bucket.blob.assert_any_call("abc/input/slide_002.png")

    def test_manifest_uploaded_as_json(self, gcs_client, mock_storage):
        _, mock_bucket = mock_storage
        mock_blob = MagicMock()
        mock_bucket.blob.return_value = mock_blob

        manifest = {"job_id": "x", "topics": [{"name": "T"}]}
        gcs_client.upload_job_inputs("x", [], manifest)

        # First call is the manifest upload
        upload_call = mock_blob.upload_from_string.call_args
        uploaded_data = json.loads(upload_call[0][0])
        assert uploaded_data["job_id"] == "x"
        assert upload_call[1]["content_type"] == "application/json"

    def test_returns_gcs_prefix_with_bucket_name(self, gcs_client, mock_storage):
        _, mock_bucket = mock_storage
        mock_bucket.name = "my-bucket"
        mock_bucket.blob.return_value = MagicMock()

        result = gcs_client.upload_job_inputs("job99", [], {})
        assert result == "gs://my-bucket/job99"


class TestDownloadVideos:
    def test_downloads_mp4_files(self, gcs_client, mock_storage, tmp_path):
        mock_client, mock_bucket = mock_storage

        # Simulate GCS listing
        blob1 = MagicMock()
        blob1.name = "job1/output/01_Topic.mp4"
        blob2 = MagicMock()
        blob2.name = "job1/output/02_Topic.mp4"
        blob_json = MagicMock()
        blob_json.name = "job1/output/status.json"
        mock_client.list_blobs.return_value = [blob1, blob_json, blob2]

        result = gcs_client.download_videos("job1", str(tmp_path))

        assert len(result) == 2
        assert all(p.endswith(".mp4") for p in result)
        # Should only download MP4s, not status.json
        blob1.download_to_filename.assert_called_once()
        blob2.download_to_filename.assert_called_once()
        blob_json.download_to_filename.assert_not_called()

    def test_creates_output_dir(self, gcs_client, mock_storage, tmp_path):
        mock_client, _ = mock_storage
        mock_client.list_blobs.return_value = []

        target = str(tmp_path / "new_dir")
        gcs_client.download_videos("job1", target)
        assert os.path.isdir(target)

    def test_returns_sorted_paths(self, gcs_client, mock_storage, tmp_path):
        mock_client, _ = mock_storage
        blob_b = MagicMock()
        blob_b.name = "j/output/02_B.mp4"
        blob_a = MagicMock()
        blob_a.name = "j/output/01_A.mp4"
        mock_client.list_blobs.return_value = [blob_b, blob_a]

        result = gcs_client.download_videos("j", str(tmp_path))
        assert os.path.basename(result[0]) == "01_A.mp4"
        assert os.path.basename(result[1]) == "02_B.mp4"


class TestCleanupJob:
    def test_deletes_all_blobs(self, gcs_client, mock_storage):
        mock_client, _ = mock_storage
        blob1 = MagicMock()
        blob2 = MagicMock()
        mock_client.list_blobs.return_value = [blob1, blob2]

        count = gcs_client.cleanup_job("old_job")

        assert count == 2
        blob1.delete.assert_called_once()
        blob2.delete.assert_called_once()

    def test_returns_zero_for_empty_job(self, gcs_client, mock_storage):
        mock_client, _ = mock_storage
        mock_client.list_blobs.return_value = []

        assert gcs_client.cleanup_job("nonexistent") == 0


# ---------------------------------------------------------------------------
# job_id validation (new behaviour added this session)
# ---------------------------------------------------------------------------


class TestJobIdValidation:
    """Covers the _VALID_JOB_ID regex guard on all three GCSVideoClient methods."""

    # upload_job_inputs

    def test_upload_rejects_path_traversal(self, gcs_client):
        """Path traversal sequences like '../etc' must raise ValueError."""
        with pytest.raises(ValueError, match="Invalid job_id"):
            gcs_client.upload_job_inputs("../traversal", [], {})

    def test_upload_rejects_empty_string(self, gcs_client):
        """An empty job_id must raise ValueError."""
        with pytest.raises(ValueError, match="Invalid job_id"):
            gcs_client.upload_job_inputs("", [], {})

    def test_upload_rejects_job_id_with_slash(self, gcs_client):
        """A job_id containing a slash must raise ValueError."""
        with pytest.raises(ValueError, match="Invalid job_id"):
            gcs_client.upload_job_inputs("job/subdir", [], {})

    def test_upload_rejects_job_id_exceeding_128_chars(self, gcs_client):
        """A job_id longer than 128 characters must raise ValueError."""
        long_id = "a" * 129
        with pytest.raises(ValueError, match="Invalid job_id"):
            gcs_client.upload_job_inputs(long_id, [], {})

    def test_upload_accepts_alphanumeric_id(self, gcs_client, mock_storage):
        """A purely alphanumeric job_id must be accepted."""
        _, mock_bucket = mock_storage
        mock_bucket.blob.return_value = MagicMock()
        # Should not raise
        gcs_client.upload_job_inputs("abc123", [], {})

    def test_upload_accepts_id_with_hyphens_and_underscores(self, gcs_client, mock_storage):
        """Hyphens and underscores are valid job_id characters."""
        _, mock_bucket = mock_storage
        mock_bucket.blob.return_value = MagicMock()
        gcs_client.upload_job_inputs("job-abc_def-123", [], {})

    def test_upload_accepts_exactly_128_char_id(self, gcs_client, mock_storage):
        """A 128-character job_id is at the boundary and must be accepted."""
        _, mock_bucket = mock_storage
        mock_bucket.blob.return_value = MagicMock()
        gcs_client.upload_job_inputs("a" * 128, [], {})

    # download_videos

    def test_download_rejects_path_traversal(self, gcs_client):
        """Path traversal in download_videos must raise ValueError."""
        with pytest.raises(ValueError, match="Invalid job_id"):
            gcs_client.download_videos("../etc/passwd", "/tmp/out")

    def test_download_rejects_empty_string(self, gcs_client):
        """Empty job_id in download_videos must raise ValueError."""
        with pytest.raises(ValueError, match="Invalid job_id"):
            gcs_client.download_videos("", "/tmp/out")

    def test_download_accepts_valid_id(self, gcs_client, mock_storage, tmp_path):
        """A valid alphanumeric job_id must not raise in download_videos."""
        mock_client, _ = mock_storage
        mock_client.list_blobs.return_value = []
        gcs_client.download_videos("valid123", str(tmp_path))  # no exception

    # cleanup_job

    def test_cleanup_rejects_path_traversal(self, gcs_client):
        """Path traversal in cleanup_job must raise ValueError."""
        with pytest.raises(ValueError, match="Invalid job_id"):
            gcs_client.cleanup_job("../../root")

    def test_cleanup_rejects_empty_string(self, gcs_client):
        """Empty job_id in cleanup_job must raise ValueError."""
        with pytest.raises(ValueError, match="Invalid job_id"):
            gcs_client.cleanup_job("")

    def test_cleanup_accepts_valid_id(self, gcs_client, mock_storage):
        """A valid alphanumeric job_id must not raise in cleanup_job."""
        mock_client, _ = mock_storage
        mock_client.list_blobs.return_value = []
        gcs_client.cleanup_job("validjob123")  # no exception
