"""Tests for FastAPI endpoints — auth, upload, start, progress, download."""

import io
import os
import secrets
import time
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# Ensure AUTH_PASSWORD is set before importing app (which hashes at import time)
os.environ.setdefault("AUTH_PASSWORD", "CR8-AI")

from frontend.app import app, ProgressCapture, UPLOAD_DIR
from frontend.middleware import _sessions, _failed_attempts

# Alias for job registry (now on app.state)
jobs = app.state.jobs


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_jobs():
    """Clear the in-memory job registry before each test."""
    jobs.clear()
    yield
    jobs.clear()


@pytest.fixture(autouse=True)
def clean_auth_state():
    """Clear sessions and rate-limit state before each test."""
    _sessions.clear()
    _failed_attempts.clear()
    yield
    _sessions.clear()
    _failed_attempts.clear()


@pytest.fixture
def client():
    """Unauthenticated test client — use for auth and public-route tests only."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def authed_client():
    """Test client with a pre-seeded valid session cookie.

    Seeds the session directly into the server-side store to avoid
    bcrypt overhead on every test run.
    """
    c = TestClient(app, raise_server_exceptions=False)
    token = secrets.token_hex(32)
    _sessions[token] = time.time() + 3600
    c.cookies.set("cr8_session", token)
    yield c
    _sessions.pop(token, None)


@pytest.fixture
def sample_pdf(tmp_path):
    """Create a minimal valid PDF file for upload tests."""
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_bytes(
        b"%PDF-1.0\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n"
        b"xref\n0 4\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n0\n%%EOF"
    )
    return pdf_path


@pytest.fixture
def sample_pptx(tmp_path):
    """Create a minimal valid PPTX file for upload tests.

    PPTX files are ZIP archives (Office Open XML), so they start with PK magic bytes.
    """
    pptx_path = tmp_path / "test.pptx"
    import zipfile
    with zipfile.ZipFile(pptx_path, "w") as zf:
        zf.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"></Types>')
    return pptx_path


# ---------------------------------------------------------------------------
# Auth endpoints (public — no session required)
# ---------------------------------------------------------------------------

class TestAuthEndpoints:

    def test_login_page_is_public(self, client):
        resp = client.get("/login")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "Sign in" in resp.text

    def test_correct_password_returns_200_and_sets_cookie(self, client):
        resp = client.post("/api/auth/login", json={"password": "CR8-AI"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        assert "cr8_session" in resp.cookies

    def test_wrong_password_returns_401(self, client):
        resp = client.post("/api/auth/login", json={"password": "wrong"})
        assert resp.status_code == 401
        assert "error" in resp.json()

    def test_missing_password_returns_401(self, client):
        resp = client.post("/api/auth/login", json={})
        assert resp.status_code == 401

    def test_rate_limit_after_5_failures(self, client):
        for _ in range(5):
            client.post("/api/auth/login", json={"password": "bad"})
        resp = client.post("/api/auth/login", json={"password": "bad"})
        assert resp.status_code == 429
        assert "15 minutes" in resp.json()["error"]

    def test_rate_limit_does_not_block_different_password_but_correct(self, client):
        # 4 failures — should still let in on correct password
        for _ in range(4):
            client.post("/api/auth/login", json={"password": "bad"})
        resp = client.post("/api/auth/login", json={"password": "CR8-AI"})
        assert resp.status_code == 200

    def test_logout_clears_session(self, authed_client):
        # After logout the session cookie should be gone and / should redirect
        authed_client.post("/api/auth/logout")
        resp = authed_client.get("/", follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.headers["location"]

    def test_health_is_public(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Unauthenticated access is blocked
# ---------------------------------------------------------------------------

class TestAuthEnforcement:

    def test_index_without_session_redirects_to_login(self, client):
        resp = client.get("/", follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.headers["location"]

    def test_upload_without_session_returns_401(self, client):
        resp = client.post("/api/upload", files={"file": ("f.pdf", b"%PDF-1.0", "application/pdf")})
        assert resp.status_code == 401

    def test_start_without_session_returns_401(self, client):
        resp = client.post("/api/start", json={"job_id": "abc12345"})
        assert resp.status_code == 401

    def test_progress_without_session_returns_401(self, client):
        resp = client.get("/api/progress/abc12345")
        assert resp.status_code == 401

    def test_download_without_session_returns_401(self, client):
        resp = client.get("/api/download/abc12345/pdf")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET / — HTML UI (authenticated)
# ---------------------------------------------------------------------------

class TestIndexRoute:

    def test_returns_200(self, authed_client):
        resp = authed_client.get("/")
        assert resp.status_code == 200

    def test_returns_html(self, authed_client):
        resp = authed_client.get("/")
        assert "text/html" in resp.headers["content-type"]

    def test_contains_page_title(self, authed_client):
        resp = authed_client.get("/")
        assert "CR8 Learning Pipeline" in resp.text

    def test_contains_upload_elements(self, authed_client):
        resp = authed_client.get("/")
        assert 'id="file-input"' in resp.text
        assert 'id="btn-generate"' in resp.text

    def test_file_input_accepts_pdf_and_pptx(self, authed_client):
        resp = authed_client.get("/")
        assert 'accept=".pdf,.pptx"' in resp.text

    def test_drop_zone_mentions_pptx(self, authed_client):
        resp = authed_client.get("/")
        assert "PPTX" in resp.text

    def test_contains_format_checkboxes(self, authed_client):
        resp = authed_client.get("/")
        assert 'id="chk-script"' in resp.text
        assert 'id="chk-video"' in resp.text

    def test_video_checkbox_enabled(self, authed_client):
        resp = authed_client.get("/")
        video_line = next(line for line in resp.text.split("\n") if "chk-video" in line)
        assert "disabled" not in video_line

    def test_video_label_mentions_kokoro(self, authed_client):
        resp = authed_client.get("/")
        assert "Kokoro TTS" in resp.text

    def test_contains_sign_out_button(self, authed_client):
        resp = authed_client.get("/")
        assert "Sign out" in resp.text


# ---------------------------------------------------------------------------
# Upload endpoint tests (authenticated)
# ---------------------------------------------------------------------------

class TestUploadEndpoint:

    def test_upload_pdf_returns_job_id(self, authed_client, sample_pdf):
        with open(sample_pdf, "rb") as f:
            resp = authed_client.post("/api/upload", files={"file": ("test.pdf", f, "application/pdf")})
        assert resp.status_code == 200
        data = resp.json()
        assert "job_id" in data
        assert data["filename"] == "test.pdf"

    def test_upload_creates_file_on_disk(self, authed_client, sample_pdf):
        with open(sample_pdf, "rb") as f:
            resp = authed_client.post("/api/upload", files={"file": ("test.pdf", f, "application/pdf")})
        job_id = resp.json()["job_id"]
        saved_path = os.path.join(UPLOAD_DIR, job_id, "test.pdf")
        assert os.path.exists(saved_path)
        os.remove(saved_path)
        os.rmdir(os.path.join(UPLOAD_DIR, job_id))

    def test_upload_rejects_non_pdf_extension(self, authed_client):
        fake_txt = io.BytesIO(b"not a pdf")
        resp = authed_client.post("/api/upload", files={"file": ("notes.txt", fake_txt, "text/plain")})
        assert resp.status_code == 400
        assert "PDF or PPTX" in resp.json()["error"]

    def test_upload_rejects_no_file(self, authed_client):
        resp = authed_client.post("/api/upload")
        assert resp.status_code == 422  # FastAPI validation error

    def test_upload_rejects_docx(self, authed_client):
        fake = io.BytesIO(b"fake docx content")
        resp = authed_client.post("/api/upload", files={"file": ("doc.docx", fake, "application/octet-stream")})
        assert resp.status_code == 400

    def test_upload_rejects_file_with_invalid_magic_bytes(self, authed_client):
        """A .pdf extension with non-PDF content should be rejected."""
        fake = io.BytesIO(b"NOT A PDF - just text pretending to be one")
        resp = authed_client.post("/api/upload", files={"file": ("evil.pdf", fake, "application/pdf")})
        assert resp.status_code == 400
        assert "valid PDF" in resp.json()["error"]

    def test_upload_rejects_oversized_file(self, authed_client):
        """Files over MAX_UPLOAD_SIZE_MB should be rejected."""
        from frontend.middleware import MAX_UPLOAD_BYTES
        big = io.BytesIO(b"%PDF-" + b"x" * (MAX_UPLOAD_BYTES + 1))
        resp = authed_client.post("/api/upload", files={"file": ("big.pdf", big, "application/pdf")})
        assert resp.status_code == 413
        assert "too large" in resp.json()["error"]

    def test_upload_sanitizes_filename(self, authed_client, sample_pdf):
        """Path traversal characters in filename should be stripped."""
        with open(sample_pdf, "rb") as f:
            resp = authed_client.post(
                "/api/upload",
                files={"file": ("../../../etc/evil.pdf", f, "application/pdf")},
            )
        assert resp.status_code == 200
        # Sanitized filename should not contain path separators
        assert "/" not in resp.json()["filename"]
        assert ".." not in resp.json()["filename"]
        # Cleanup
        job_id = resp.json()["job_id"]
        job_dir = os.path.join(UPLOAD_DIR, job_id)
        for fname in os.listdir(job_dir):
            os.remove(os.path.join(job_dir, fname))
        os.rmdir(job_dir)

    def test_upload_pptx_returns_job_id(self, authed_client, sample_pptx):
        with open(sample_pptx, "rb") as f:
            resp = authed_client.post(
                "/api/upload",
                files={"file": ("slides.pptx", f, "application/vnd.openxmlformats-officedocument.presentationml.presentation")},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "job_id" in data
        assert data["filename"] == "slides.pptx"
        # Cleanup
        job_id = data["job_id"]
        job_dir = os.path.join(UPLOAD_DIR, job_id)
        for fname in os.listdir(job_dir):
            os.remove(os.path.join(job_dir, fname))
        os.rmdir(job_dir)

    def test_upload_pptx_creates_file_on_disk(self, authed_client, sample_pptx):
        with open(sample_pptx, "rb") as f:
            resp = authed_client.post(
                "/api/upload",
                files={"file": ("test.pptx", f, "application/octet-stream")},
            )
        job_id = resp.json()["job_id"]
        saved_path = os.path.join(UPLOAD_DIR, job_id, "test.pptx")
        assert os.path.exists(saved_path)
        os.remove(saved_path)
        os.rmdir(os.path.join(UPLOAD_DIR, job_id))

    def test_upload_rejects_pptx_with_invalid_magic_bytes(self, authed_client):
        """A .pptx extension with non-ZIP content should be rejected."""
        fake = io.BytesIO(b"NOT A PPTX - just text pretending")
        resp = authed_client.post(
            "/api/upload",
            files={"file": ("evil.pptx", fake, "application/octet-stream")},
        )
        assert resp.status_code == 400
        assert "valid PPTX" in resp.json()["error"]


# ---------------------------------------------------------------------------
# Start endpoint tests (authenticated)
# ---------------------------------------------------------------------------

class TestStartEndpoint:

    def test_start_with_missing_job_id(self, authed_client):
        resp = authed_client.post("/api/start", json={"formats": ["pdf"]})
        assert resp.status_code == 400

    def test_start_with_invalid_job_id_format(self, authed_client):
        resp = authed_client.post("/api/start", json={"job_id": "../../etc"})
        assert resp.status_code == 400

    def test_start_with_nonexistent_job(self, authed_client):
        resp = authed_client.post("/api/start", json={"job_id": "deadbeef", "formats": ["pdf"]})
        assert resp.status_code == 404

    def test_start_launches_pipeline(self, authed_client, sample_pdf):
        with open(sample_pdf, "rb") as f:
            upload_resp = authed_client.post("/api/upload", files={"file": ("test.pdf", f, "application/pdf")})
        job_id = upload_resp.json()["job_id"]

        with patch("frontend.app.run_job") as mock_run:
            mock_run.return_value = {"pdf_path": "/fake/out.pdf", "video_dir": ""}
            resp = authed_client.post("/api/start", json={"job_id": job_id, "formats": ["pdf"]})

        assert resp.status_code == 200
        assert resp.json()["status"] == "running"
        assert job_id in jobs

        job_dir = os.path.join(UPLOAD_DIR, job_id)
        for f in os.listdir(job_dir):
            os.remove(os.path.join(job_dir, f))
        os.rmdir(job_dir)

    def test_start_rejects_concurrent_job(self, authed_client, sample_pdf):
        cap = ProgressCapture()
        cap.status = "running"
        jobs["existing_"] = cap

        with open(sample_pdf, "rb") as f:
            upload_resp = authed_client.post("/api/upload", files={"file": ("test.pdf", f, "application/pdf")})
        job_id = upload_resp.json()["job_id"]

        resp = authed_client.post("/api/start", json={"job_id": job_id, "formats": ["pdf"]})
        assert resp.status_code == 409
        assert "already running" in resp.json()["error"]

        job_dir = os.path.join(UPLOAD_DIR, job_id)
        for f in os.listdir(job_dir):
            os.remove(os.path.join(job_dir, f))
        os.rmdir(job_dir)

    def test_start_allows_new_job_after_completion(self, authed_client, sample_pdf):
        cap = ProgressCapture()
        cap.status = "complete"
        jobs["old_job_"] = cap

        with open(sample_pdf, "rb") as f:
            upload_resp = authed_client.post("/api/upload", files={"file": ("test.pdf", f, "application/pdf")})
        job_id = upload_resp.json()["job_id"]

        with patch("frontend.app.run_job") as mock_run:
            mock_run.return_value = {"pdf_path": "", "video_dir": ""}
            resp = authed_client.post("/api/start", json={"job_id": job_id, "formats": ["pdf"]})

        assert resp.status_code == 200

        job_dir = os.path.join(UPLOAD_DIR, job_id)
        for f in os.listdir(job_dir):
            os.remove(os.path.join(job_dir, f))
        os.rmdir(job_dir)

    def test_start_launches_pipeline_with_pptx(self, authed_client, sample_pptx):
        with open(sample_pptx, "rb") as f:
            upload_resp = authed_client.post(
                "/api/upload",
                files={"file": ("slides.pptx", f, "application/octet-stream")},
            )
        job_id = upload_resp.json()["job_id"]

        with patch("frontend.app.run_job") as mock_run:
            mock_run.return_value = {"pdf_path": "/fake/out.pdf", "video_dir": ""}
            resp = authed_client.post("/api/start", json={"job_id": job_id, "formats": ["pdf"]})

        assert resp.status_code == 200
        assert resp.json()["status"] == "running"
        # Verify the PPTX file was passed to run_job
        call_args = mock_run.call_args
        assert any(f.endswith(".pptx") for f in call_args[0][0])

        job_dir = os.path.join(UPLOAD_DIR, job_id)
        for f in os.listdir(job_dir):
            os.remove(os.path.join(job_dir, f))
        os.rmdir(job_dir)

    def test_start_with_video_format_calls_run_job(self, authed_client, sample_pdf):
        with open(sample_pdf, "rb") as f:
            upload_resp = authed_client.post("/api/upload", files={"file": ("test.pdf", f, "application/pdf")})
        job_id = upload_resp.json()["job_id"]

        with patch("frontend.app.run_job") as mock_run:
            mock_run.return_value = {"pdf_path": "/fake/out.pdf", "ppt_path": "", "video_dir": "/fake/videos"}
            resp = authed_client.post(
                "/api/start",
                json={"job_id": job_id, "formats": ["pdf", "ppt", "script", "video"]},
            )

        assert resp.status_code == 200
        # Verify run_job was called with video in formats
        call_args = mock_run.call_args
        assert "video" in call_args[0][1]  # second positional arg = formats list

        job_dir = os.path.join(UPLOAD_DIR, job_id)
        for f in os.listdir(job_dir):
            os.remove(os.path.join(job_dir, f))
        os.rmdir(job_dir)

    def test_start_defaults_to_pdf_format(self, authed_client, sample_pdf):
        with open(sample_pdf, "rb") as f:
            upload_resp = authed_client.post("/api/upload", files={"file": ("test.pdf", f, "application/pdf")})
        job_id = upload_resp.json()["job_id"]

        with patch("frontend.app.run_job") as mock_run:
            mock_run.return_value = {"pdf_path": "", "video_dir": ""}
            resp = authed_client.post("/api/start", json={"job_id": job_id})

        assert resp.status_code == 200

        job_dir = os.path.join(UPLOAD_DIR, job_id)
        for f in os.listdir(job_dir):
            os.remove(os.path.join(job_dir, f))
        os.rmdir(job_dir)


# ---------------------------------------------------------------------------
# GET /api/progress/<job_id> (authenticated)
# ---------------------------------------------------------------------------

class TestProgressEndpoint:

    def test_invalid_job_id_format_returns_400(self, authed_client):
        # job_id must be exactly 8 lowercase hex chars
        resp = authed_client.get("/api/progress/notvalid")
        assert resp.status_code == 400

    def test_unknown_job_returns_404(self, authed_client):
        resp = authed_client.get("/api/progress/deadbeef")
        assert resp.status_code == 404

    def test_returns_running_state(self, authed_client):
        cap = ProgressCapture()
        cap._original_stdout = io.StringIO()
        cap.write("[Ingest] Processing file.pdf\n")
        jobs["ab001234"] = cap

        resp = authed_client.get("/api/progress/ab001234")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "running"
        assert data["stage"] == "Ingest"
        assert data["percent"] >= 0
        assert len(data["logs"]) >= 1

    def test_returns_complete_state_with_files(self, authed_client, tmp_path):
        fake_pdf = tmp_path / "guide.pdf"
        fake_pdf.write_bytes(b"%PDF-1.0 fake content")

        cap = ProgressCapture()
        cap.status = "complete"
        cap.percent = 100
        cap.result = {"pdf_path": str(fake_pdf), "video_dir": ""}
        jobs["bead1234"] = cap

        resp = authed_client.get("/api/progress/bead1234")
        data = resp.json()
        assert data["status"] == "complete"
        assert data["percent"] == 100
        assert len(data["files"]) == 1
        assert data["files"][0]["type"] == "pdf"

    def test_returns_complete_state_with_video_files(self, authed_client, tmp_path):
        fake_pdf = tmp_path / "guide.pdf"
        fake_pdf.write_bytes(b"%PDF-1.0 fake content")
        video_dir = tmp_path / "videos"
        video_dir.mkdir()
        (video_dir / "01_Topic.mp4").write_bytes(b"\x00\x00\x00 ftyp")
        scripts_dir = video_dir / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "01_Topic.txt").write_text("Script content")

        cap = ProgressCapture()
        cap.status = "complete"
        cap.percent = 100
        cap.result = {"pdf_path": str(fake_pdf), "ppt_path": "", "video_dir": str(video_dir)}
        jobs["abed1234"] = cap

        resp = authed_client.get("/api/progress/abed1234")
        data = resp.json()
        assert data["status"] == "complete"
        file_types = [f["type"] for f in data["files"]]
        assert "pdf" in file_types
        assert "scripts" in file_types
        assert "videos" in file_types

    def test_returns_error_state(self, authed_client):
        cap = ProgressCapture()
        cap.status = "error"
        cap.error = "API key invalid"
        jobs["cafe1234"] = cap

        resp = authed_client.get("/api/progress/cafe1234")
        data = resp.json()
        assert data["status"] == "error"
        assert data["error"] == "API key invalid"


# ---------------------------------------------------------------------------
# GET /api/download/<job_id>/<file_type> (authenticated)
# ---------------------------------------------------------------------------

class TestDownloadEndpoint:

    def test_invalid_job_id_format_returns_400(self, authed_client):
        # job_id must be exactly 8 lowercase hex chars
        resp = authed_client.get("/api/download/notvalid/pdf")
        assert resp.status_code == 400

    def test_download_unknown_job_returns_404(self, authed_client):
        resp = authed_client.get("/api/download/deadbeef/pdf")
        assert resp.status_code == 404

    def test_download_incomplete_job_returns_404(self, authed_client):
        cap = ProgressCapture()
        cap.status = "running"
        cap.result = None
        jobs["babe1234"] = cap

        resp = authed_client.get("/api/download/babe1234/pdf")
        assert resp.status_code == 404

    def test_download_pdf(self, authed_client, tmp_path):
        fake_pdf = tmp_path / "learning_guide.pdf"
        fake_pdf.write_bytes(b"%PDF-1.0 test content for download")

        cap = ProgressCapture()
        cap.status = "complete"
        cap.result = {"pdf_path": str(fake_pdf), "video_dir": ""}
        jobs["feed1234"] = cap

        resp = authed_client.get("/api/download/feed1234/pdf")
        assert resp.status_code == 200
        assert resp.content.startswith(b"%PDF-1.0")

    def test_download_scripts_as_zip(self, authed_client, tmp_path):
        video_dir = tmp_path / "videos"
        scripts_dir = video_dir / "scripts"
        scripts_dir.mkdir(parents=True)
        (scripts_dir / "01_Topic.txt").write_text("Script content 1")
        (scripts_dir / "02_Topic.txt").write_text("Script content 2")

        cap = ProgressCapture()
        cap.status = "complete"
        cap.result = {"pdf_path": "", "video_dir": str(video_dir)}
        jobs["bafe1234"] = cap

        resp = authed_client.get("/api/download/bafe1234/scripts")
        assert resp.status_code == 200
        assert resp.content[:2] == b"PK"

    def test_download_videos_as_zip(self, authed_client, tmp_path):
        video_dir = tmp_path / "videos"
        video_dir.mkdir()
        (video_dir / "01_Topic.mp4").write_bytes(b"\x00\x00\x00 ftyp")
        (video_dir / "scripts").mkdir()

        cap = ProgressCapture()
        cap.status = "complete"
        cap.result = {"pdf_path": "", "video_dir": str(video_dir)}
        jobs["caed1234"] = cap

        resp = authed_client.get("/api/download/caed1234/videos")
        assert resp.status_code == 200
        assert resp.content[:2] == b"PK"

    def test_download_nonexistent_type_returns_404(self, authed_client):
        cap = ProgressCapture()
        cap.status = "complete"
        cap.result = {"pdf_path": "", "video_dir": ""}
        jobs["dace1234"] = cap

        resp = authed_client.get("/api/download/dace1234/pdf")
        assert resp.status_code == 404

    def test_download_all_artifacts_from_video_job(self, authed_client, tmp_path):
        """Full video job produces PDF + scripts + videos — all downloadable."""
        fake_pdf = tmp_path / "guide.pdf"
        fake_pdf.write_bytes(b"%PDF-1.0 test content")
        video_dir = tmp_path / "videos"
        video_dir.mkdir()
        (video_dir / "01_Topic.mp4").write_bytes(b"\x00\x00\x00 ftyp")
        scripts_dir = video_dir / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "01_Topic.txt").write_text("Script for topic 1")

        cap = ProgressCapture()
        cap.status = "complete"
        cap.result = {"pdf_path": str(fake_pdf), "ppt_path": "", "video_dir": str(video_dir)}
        jobs["aace1234"] = cap

        # PDF download
        resp = authed_client.get("/api/download/aace1234/pdf")
        assert resp.status_code == 200
        assert resp.content.startswith(b"%PDF-1.0")

        # Scripts download (zip)
        resp = authed_client.get("/api/download/aace1234/scripts")
        assert resp.status_code == 200
        assert resp.content[:2] == b"PK"

        # Videos download (zip)
        resp = authed_client.get("/api/download/aace1234/videos")
        assert resp.status_code == 200
        assert resp.content[:2] == b"PK"

    def test_download_missing_pdf_returns_404(self, authed_client):
        cap = ProgressCapture()
        cap.status = "complete"
        cap.result = {"pdf_path": "/nonexistent/path.pdf", "video_dir": ""}
        jobs["face1234"] = cap

        resp = authed_client.get("/api/download/face1234/pdf")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/cancel/<job_id> (authenticated)
# ---------------------------------------------------------------------------

class TestCancelEndpoint:

    def test_cancel_without_auth_returns_401(self, client):
        resp = client.post("/api/cancel/ab001234")
        assert resp.status_code == 401

    def test_cancel_invalid_job_id_returns_400(self, authed_client):
        resp = authed_client.post("/api/cancel/notvalid")
        assert resp.status_code == 400

    def test_cancel_unknown_job_returns_404(self, authed_client):
        resp = authed_client.post("/api/cancel/deadbeef")
        assert resp.status_code == 404

    def test_cancel_running_job_returns_cancelling(self, authed_client):
        cap = ProgressCapture()
        cap._original_stdout = io.StringIO()
        cap.status = "running"
        jobs["ab001234"] = cap

        resp = authed_client.post("/api/cancel/ab001234")
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelling"
        assert cap.cancel_requested is True

    def test_cancel_completed_job_returns_409(self, authed_client):
        cap = ProgressCapture()
        cap.status = "complete"
        cap.result = {"pdf_path": "", "video_dir": ""}
        jobs["ab001234"] = cap

        resp = authed_client.post("/api/cancel/ab001234")
        assert resp.status_code == 409

    def test_cancel_already_cancelled_returns_409(self, authed_client):
        cap = ProgressCapture()
        cap.status = "cancelled"
        jobs["ab001234"] = cap

        resp = authed_client.post("/api/cancel/ab001234")
        assert resp.status_code == 409

    def test_cancel_sets_cancel_requested(self, authed_client):
        """Cancel endpoint sets cancel_requested; the pipeline poll loop
        propagates cancellation to whichever GPU region is active."""
        cap = ProgressCapture()
        cap._original_stdout = io.StringIO()
        cap.status = "running"
        cap.video_job_id = "vj_test_abc"
        jobs["ab001234"] = cap

        resp = authed_client.post("/api/cancel/ab001234")

        assert resp.status_code == 200
        assert cap.cancel_requested is True
