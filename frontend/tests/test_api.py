"""Tests for FastAPI endpoints — upload, start, progress, download."""

import io
import os
import time
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from frontend.app import app, jobs, ProgressCapture, UPLOAD_DIR


@pytest.fixture(autouse=True)
def clean_jobs():
    """Clear the in-memory job registry before each test."""
    jobs.clear()
    yield
    jobs.clear()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def sample_pdf(tmp_path):
    """Create a minimal valid PDF file for upload tests."""
    pdf_path = tmp_path / "test.pdf"
    # Minimal PDF 1.0 structure
    pdf_path.write_bytes(
        b"%PDF-1.0\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n"
        b"xref\n0 4\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n0\n%%EOF"
    )
    return pdf_path


# ---------------------------------------------------------------------------
# GET / — HTML UI
# ---------------------------------------------------------------------------

class TestIndexRoute:

    def test_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_returns_html(self, client):
        resp = client.get("/")
        assert "text/html" in resp.headers["content-type"]

    def test_contains_page_title(self, client):
        resp = client.get("/")
        assert "CR8 Learning Pipeline" in resp.text

    def test_contains_upload_elements(self, client):
        resp = client.get("/")
        assert 'id="file-input"' in resp.text
        assert 'id="btn-generate"' in resp.text

    def test_contains_format_checkboxes(self, client):
        resp = client.get("/")
        assert 'id="chk-script"' in resp.text
        assert 'id="chk-video"' in resp.text

    def test_video_checkbox_disabled(self, client):
        resp = client.get("/")
        assert 'id="chk-video"' in resp.text
        # The video checkbox should have disabled attribute
        video_line = [l for l in resp.text.split("\n") if "chk-video" in l][0]
        assert "disabled" in video_line


# ---------------------------------------------------------------------------
# POST /api/upload
# ---------------------------------------------------------------------------

class TestUploadEndpoint:

    def test_upload_pdf_returns_job_id(self, client, sample_pdf):
        with open(sample_pdf, "rb") as f:
            resp = client.post("/api/upload", files={"file": ("test.pdf", f, "application/pdf")})
        assert resp.status_code == 200
        data = resp.json()
        assert "job_id" in data
        assert data["filename"] == "test.pdf"

    def test_upload_creates_file_on_disk(self, client, sample_pdf):
        with open(sample_pdf, "rb") as f:
            resp = client.post("/api/upload", files={"file": ("test.pdf", f, "application/pdf")})
        job_id = resp.json()["job_id"]
        saved_path = os.path.join(UPLOAD_DIR, job_id, "test.pdf")
        assert os.path.exists(saved_path)
        # Cleanup
        os.remove(saved_path)
        os.rmdir(os.path.join(UPLOAD_DIR, job_id))

    def test_upload_rejects_non_pdf(self, client):
        fake_txt = io.BytesIO(b"not a pdf")
        resp = client.post("/api/upload", files={"file": ("notes.txt", fake_txt, "text/plain")})
        assert resp.status_code == 400
        assert "PDF" in resp.json()["error"]

    def test_upload_rejects_no_file(self, client):
        resp = client.post("/api/upload")
        assert resp.status_code == 422  # FastAPI validation error

    def test_upload_rejects_docx(self, client):
        fake = io.BytesIO(b"fake docx content")
        resp = client.post("/api/upload", files={"file": ("doc.docx", fake, "application/octet-stream")})
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# POST /api/start
# ---------------------------------------------------------------------------

class TestStartEndpoint:

    def test_start_with_missing_job_id(self, client):
        resp = client.post("/api/start", json={"formats": ["pdf"]})
        assert resp.status_code == 400

    def test_start_with_nonexistent_job(self, client):
        resp = client.post("/api/start", json={"job_id": "nonexistent", "formats": ["pdf"]})
        assert resp.status_code == 404

    def test_start_launches_pipeline(self, client, sample_pdf):
        # First upload
        with open(sample_pdf, "rb") as f:
            upload_resp = client.post("/api/upload", files={"file": ("test.pdf", f, "application/pdf")})
        job_id = upload_resp.json()["job_id"]

        # Mock the pipeline so it doesn't actually run
        with patch("frontend.app.run_job") as mock_run:
            mock_run.return_value = {"pdf_path": "/fake/out.pdf", "video_dir": ""}
            resp = client.post("/api/start", json={"job_id": job_id, "formats": ["pdf"]})

        assert resp.status_code == 200
        assert resp.json()["status"] == "running"
        assert job_id in jobs

        # Cleanup
        job_dir = os.path.join(UPLOAD_DIR, job_id)
        for f in os.listdir(job_dir):
            os.remove(os.path.join(job_dir, f))
        os.rmdir(job_dir)

    def test_start_rejects_concurrent_job(self, client, sample_pdf):
        """Only one job at a time in prototype mode."""
        # Simulate a running job
        cap = ProgressCapture()
        cap.status = "running"
        jobs["existing_job"] = cap

        with open(sample_pdf, "rb") as f:
            upload_resp = client.post("/api/upload", files={"file": ("test.pdf", f, "application/pdf")})
        job_id = upload_resp.json()["job_id"]

        resp = client.post("/api/start", json={"job_id": job_id, "formats": ["pdf"]})
        assert resp.status_code == 409
        assert "already running" in resp.json()["error"]

        # Cleanup
        job_dir = os.path.join(UPLOAD_DIR, job_id)
        for f in os.listdir(job_dir):
            os.remove(os.path.join(job_dir, f))
        os.rmdir(job_dir)

    def test_start_allows_new_job_after_completion(self, client, sample_pdf):
        """A completed job should not block a new one."""
        cap = ProgressCapture()
        cap.status = "complete"
        jobs["old_job"] = cap

        with open(sample_pdf, "rb") as f:
            upload_resp = client.post("/api/upload", files={"file": ("test.pdf", f, "application/pdf")})
        job_id = upload_resp.json()["job_id"]

        with patch("frontend.app.run_job") as mock_run:
            mock_run.return_value = {"pdf_path": "", "video_dir": ""}
            resp = client.post("/api/start", json={"job_id": job_id, "formats": ["pdf"]})

        assert resp.status_code == 200

        # Cleanup
        job_dir = os.path.join(UPLOAD_DIR, job_id)
        for f in os.listdir(job_dir):
            os.remove(os.path.join(job_dir, f))
        os.rmdir(job_dir)

    def test_start_defaults_to_pdf_format(self, client, sample_pdf):
        """If no formats specified, should default to pdf."""
        with open(sample_pdf, "rb") as f:
            upload_resp = client.post("/api/upload", files={"file": ("test.pdf", f, "application/pdf")})
        job_id = upload_resp.json()["job_id"]

        with patch("frontend.app.run_job") as mock_run:
            mock_run.return_value = {"pdf_path": "", "video_dir": ""}
            resp = client.post("/api/start", json={"job_id": job_id})

        assert resp.status_code == 200

        # Cleanup
        job_dir = os.path.join(UPLOAD_DIR, job_id)
        for f in os.listdir(job_dir):
            os.remove(os.path.join(job_dir, f))
        os.rmdir(job_dir)


# ---------------------------------------------------------------------------
# GET /api/progress/<job_id>
# ---------------------------------------------------------------------------

class TestProgressEndpoint:

    def test_unknown_job_returns_404(self, client):
        resp = client.get("/api/progress/nonexistent")
        assert resp.status_code == 404

    def test_returns_running_state(self, client):
        cap = ProgressCapture()
        cap._original_stdout = io.StringIO()
        cap.write("[Ingest] Processing file.pdf\n")
        jobs["test123"] = cap

        resp = client.get("/api/progress/test123")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "running"
        assert data["stage"] == "Ingest"
        assert data["percent"] >= 0
        assert len(data["logs"]) >= 1

    def test_returns_complete_state_with_files(self, client, tmp_path):
        # Create a fake output PDF
        fake_pdf = tmp_path / "guide.pdf"
        fake_pdf.write_bytes(b"%PDF-1.0 fake content")

        cap = ProgressCapture()
        cap.status = "complete"
        cap.percent = 100
        cap.result = {"pdf_path": str(fake_pdf), "video_dir": ""}
        jobs["done123"] = cap

        resp = client.get("/api/progress/done123")
        data = resp.json()
        assert data["status"] == "complete"
        assert data["percent"] == 100
        assert len(data["files"]) == 1
        assert data["files"][0]["type"] == "pdf"

    def test_returns_error_state(self, client):
        cap = ProgressCapture()
        cap.status = "error"
        cap.error = "API key invalid"
        jobs["err123"] = cap

        resp = client.get("/api/progress/err123")
        data = resp.json()
        assert data["status"] == "error"
        assert data["error"] == "API key invalid"


# ---------------------------------------------------------------------------
# GET /api/download/<job_id>/<file_type>
# ---------------------------------------------------------------------------

class TestDownloadEndpoint:

    def test_download_unknown_job_returns_404(self, client):
        resp = client.get("/api/download/nonexistent/pdf")
        assert resp.status_code == 404

    def test_download_incomplete_job_returns_404(self, client):
        cap = ProgressCapture()
        cap.status = "running"
        cap.result = None
        jobs["running123"] = cap

        resp = client.get("/api/download/running123/pdf")
        assert resp.status_code == 404

    def test_download_pdf(self, client, tmp_path):
        fake_pdf = tmp_path / "learning_guide.pdf"
        fake_pdf.write_bytes(b"%PDF-1.0 test content for download")

        cap = ProgressCapture()
        cap.status = "complete"
        cap.result = {"pdf_path": str(fake_pdf), "video_dir": ""}
        jobs["dl_pdf"] = cap

        resp = client.get("/api/download/dl_pdf/pdf")
        assert resp.status_code == 200
        assert resp.content.startswith(b"%PDF-1.0")

    def test_download_scripts_as_zip(self, client, tmp_path):
        # Create fake scripts directory
        video_dir = tmp_path / "videos"
        scripts_dir = video_dir / "scripts"
        scripts_dir.mkdir(parents=True)
        (scripts_dir / "01_Topic.txt").write_text("Script content 1")
        (scripts_dir / "02_Topic.txt").write_text("Script content 2")

        cap = ProgressCapture()
        cap.status = "complete"
        cap.result = {"pdf_path": "", "video_dir": str(video_dir)}
        jobs["dl_scripts"] = cap

        resp = client.get("/api/download/dl_scripts/scripts")
        assert resp.status_code == 200
        # ZIP files start with PK magic bytes
        assert resp.content[:2] == b"PK"

    def test_download_videos_as_zip(self, client, tmp_path):
        video_dir = tmp_path / "videos"
        video_dir.mkdir()
        (video_dir / "01_Topic.mp4").write_bytes(b"\x00\x00\x00 ftyp")
        (video_dir / "scripts").mkdir()  # scripts subdir should be excluded from video zip

        cap = ProgressCapture()
        cap.status = "complete"
        cap.result = {"pdf_path": "", "video_dir": str(video_dir)}
        jobs["dl_vids"] = cap

        resp = client.get("/api/download/dl_vids/videos")
        assert resp.status_code == 200
        assert resp.content[:2] == b"PK"

    def test_download_nonexistent_type_returns_404(self, client):
        cap = ProgressCapture()
        cap.status = "complete"
        cap.result = {"pdf_path": "", "video_dir": ""}
        jobs["dl_none"] = cap

        resp = client.get("/api/download/dl_none/pdf")
        assert resp.status_code == 404

    def test_download_missing_pdf_returns_404(self, client):
        """pdf_path set but file doesn't exist on disk."""
        cap = ProgressCapture()
        cap.status = "complete"
        cap.result = {"pdf_path": "/nonexistent/path.pdf", "video_dir": ""}
        jobs["dl_missing"] = cap

        resp = client.get("/api/download/dl_missing/pdf")
        assert resp.status_code == 404
