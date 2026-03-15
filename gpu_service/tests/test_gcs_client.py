"""Tests for GPUGCSClient — download_pptx and _strip_gs_prefix.

All Google Cloud Storage API calls are mocked via MagicMock — no real
credentials are required or used.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from gpu_service.gcs_client import GPUGCSClient, _strip_gs_prefix


# ---------------------------------------------------------------------------
# _strip_gs_prefix
# ---------------------------------------------------------------------------


class TestStripGsPrefix:
    def test_strips_gs_scheme_and_bucket(self):
        assert _strip_gs_prefix("gs://my-bucket/jobs/abc123") == "jobs/abc123"

    def test_strips_bucket_only_no_path(self):
        assert _strip_gs_prefix("gs://my-bucket") == ""

    def test_passthrough_when_no_gs_prefix(self):
        assert _strip_gs_prefix("jobs/abc123") == "jobs/abc123"

    def test_handles_empty_string(self):
        assert _strip_gs_prefix("") == ""


# ---------------------------------------------------------------------------
# GPUGCSClient fixtures
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
    """Return a GPUGCSClient whose underlying bucket is fully mocked."""
    return GPUGCSClient("cr8-jobs")


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
