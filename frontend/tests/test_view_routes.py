"""Tests for content viewer routes — PDF inline, PPT slides, video streaming.

TDD: tests written before implementation. All view endpoints require auth
and validate job_id format (8-char hex).
"""

import os
import secrets
import time

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("AUTH_PASSWORD", "CR8-AI")

from frontend.app import app, ProgressCapture
from frontend.middleware import _sessions, _failed_attempts

jobs = app.state.jobs


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clean_state():
    """Clear job registry and auth state before each test."""
    jobs.clear()
    _sessions.clear()
    _failed_attempts.clear()
    yield
    jobs.clear()
    _sessions.clear()
    _failed_attempts.clear()


@pytest.fixture
def authed_client():
    """Test client with a pre-seeded valid session cookie."""
    c = TestClient(app, raise_server_exceptions=False)
    token = secrets.token_hex(32)
    _sessions[token] = time.time() + 3600
    c.cookies.set("cr8_session", token)
    yield c
    _sessions.pop(token, None)


@pytest.fixture
def client():
    """Unauthenticated test client."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def completed_job(tmp_path):
    """Set up a completed job with PDF, PPT, slide images, and videos."""
    job_id = "ab12cd34"

    # Create output files
    pdf_path = tmp_path / "output.pdf"
    pdf_path.write_bytes(b"%PDF-1.0 fake pdf content for testing")

    ppt_path = tmp_path / "output.pptx"
    ppt_path.write_bytes(b"PK\x03\x04 fake pptx content for testing")

    # Slide images
    slides_dir = tmp_path / "slides"
    slides_dir.mkdir()
    for i in range(3):
        slide = slides_dir / f"slide_{i + 1:02d}.png"
        slide.write_bytes(b"\x89PNG fake png " + str(i).encode())

    # Video files
    video_dir = tmp_path / "videos"
    video_dir.mkdir()
    (video_dir / "Introduction.mp4").write_bytes(b"\x00\x00\x00 ftyp fake mp4 intro")
    (video_dir / "Advanced_Topics.mp4").write_bytes(b"\x00\x00\x00 ftyp fake mp4 advanced")

    # Set up ProgressCapture with result
    capture = ProgressCapture()
    capture.status = "complete"
    capture.percent = 100
    capture.result = {
        "pdf_path": str(pdf_path),
        "ppt_path": str(ppt_path),
        "slide_images": [
            str(slides_dir / "slide_01.png"),
            str(slides_dir / "slide_02.png"),
            str(slides_dir / "slide_03.png"),
        ],
        "video_dir": str(video_dir),
        "topics": [
            {"name": "Introduction"},
            {"name": "Advanced Topics"},
        ],
    }
    jobs[job_id] = capture
    return job_id


@pytest.fixture
def incomplete_job():
    """Set up a running job (no result yet)."""
    job_id = "99887766"
    capture = ProgressCapture()
    capture.status = "running"
    capture.percent = 50
    jobs[job_id] = capture
    return job_id


# ---------------------------------------------------------------------------
# Auth enforcement
# ---------------------------------------------------------------------------

class TestViewAuth:
    """View endpoints require authentication."""

    def test_pdf_view_requires_auth(self, client):
        resp = client.get("/api/view/ab12cd34/pdf")
        assert resp.status_code == 401

    def test_slides_list_requires_auth(self, client):
        resp = client.get("/api/view/ab12cd34/slides")
        assert resp.status_code == 401

    def test_slide_image_requires_auth(self, client):
        resp = client.get("/api/view/ab12cd34/slide/1")
        assert resp.status_code == 401

    def test_videos_list_requires_auth(self, client):
        resp = client.get("/api/view/ab12cd34/videos")
        assert resp.status_code == 401

    def test_video_stream_requires_auth(self, client):
        resp = client.get("/api/view/ab12cd34/video/0")
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Job ID validation
# ---------------------------------------------------------------------------

class TestViewJobIdValidation:
    """View endpoints reject invalid job IDs."""

    def test_pdf_invalid_job_id(self, authed_client):
        resp = authed_client.get("/api/view/INVALID!/pdf")
        assert resp.status_code == 400

    def test_slides_invalid_job_id(self, authed_client):
        resp = authed_client.get("/api/view/ZZZZZZZZ/slides")
        assert resp.status_code == 400

    def test_video_invalid_job_id(self, authed_client):
        resp = authed_client.get("/api/view/tooshort/video/0")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Job not found / not complete
# ---------------------------------------------------------------------------

class TestViewJobNotFound:
    """View endpoints return 404 for missing or incomplete jobs."""

    def test_pdf_job_not_found(self, authed_client):
        resp = authed_client.get("/api/view/deadbeef/pdf")
        assert resp.status_code == 404

    def test_slides_job_not_found(self, authed_client):
        resp = authed_client.get("/api/view/deadbeef/slides")
        assert resp.status_code == 404

    def test_pdf_job_not_complete(self, authed_client, incomplete_job):
        resp = authed_client.get(f"/api/view/{incomplete_job}/pdf")
        assert resp.status_code == 404

    def test_slides_job_not_complete(self, authed_client, incomplete_job):
        resp = authed_client.get(f"/api/view/{incomplete_job}/slides")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PDF inline view
# ---------------------------------------------------------------------------

class TestPdfView:
    """PDF view serves the file inline for iframe embedding."""

    def test_pdf_returns_200(self, authed_client, completed_job):
        resp = authed_client.get(f"/api/view/{completed_job}/pdf")
        assert resp.status_code == 200

    def test_pdf_content_type(self, authed_client, completed_job):
        resp = authed_client.get(f"/api/view/{completed_job}/pdf")
        assert "application/pdf" in resp.headers["content-type"]

    def test_pdf_inline_disposition(self, authed_client, completed_job):
        resp = authed_client.get(f"/api/view/{completed_job}/pdf")
        disposition = resp.headers.get("content-disposition", "")
        assert "inline" in disposition or disposition == ""

    def test_pdf_no_result_pdf_path(self, authed_client):
        """Job is complete but has no PDF path in result."""
        job_id = "aabb1122"
        capture = ProgressCapture()
        capture.status = "complete"
        capture.result = {}
        jobs[job_id] = capture
        resp = authed_client.get(f"/api/view/{job_id}/pdf")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Slide image listing
# ---------------------------------------------------------------------------

class TestSlidesList:
    """Slide listing returns available slide image metadata."""

    def test_slides_returns_json(self, authed_client, completed_job):
        resp = authed_client.get(f"/api/view/{completed_job}/slides")
        assert resp.status_code == 200
        data = resp.json()
        assert "slides" in data
        assert "total" in data

    def test_slides_count_matches(self, authed_client, completed_job):
        resp = authed_client.get(f"/api/view/{completed_job}/slides")
        data = resp.json()
        assert data["total"] == 3
        assert len(data["slides"]) == 3

    def test_slides_urls_contain_index(self, authed_client, completed_job):
        resp = authed_client.get(f"/api/view/{completed_job}/slides")
        data = resp.json()
        for i, url in enumerate(data["slides"]):
            assert f"/slide/{i + 1}" in url

    def test_slides_no_slide_images(self, authed_client):
        """Job complete but no slide_images in result."""
        job_id = "ccdd5566"
        capture = ProgressCapture()
        capture.status = "complete"
        capture.result = {"pdf_path": "/fake/path.pdf"}
        jobs[job_id] = capture
        resp = authed_client.get(f"/api/view/{job_id}/slides")
        data = resp.json()
        assert data["total"] == 0
        assert data["slides"] == []


# ---------------------------------------------------------------------------
# Individual slide image
# ---------------------------------------------------------------------------

class TestSlideImage:
    """Individual slide endpoint serves PNG images."""

    def test_slide_returns_200(self, authed_client, completed_job):
        resp = authed_client.get(f"/api/view/{completed_job}/slide/1")
        assert resp.status_code == 200

    def test_slide_content_type_png(self, authed_client, completed_job):
        resp = authed_client.get(f"/api/view/{completed_job}/slide/1")
        assert "image/png" in resp.headers["content-type"]

    def test_slide_index_out_of_range(self, authed_client, completed_job):
        resp = authed_client.get(f"/api/view/{completed_job}/slide/99")
        assert resp.status_code == 404

    def test_slide_index_zero(self, authed_client, completed_job):
        """Slide indices are 1-based."""
        resp = authed_client.get(f"/api/view/{completed_job}/slide/0")
        assert resp.status_code == 404

    def test_slide_index_negative(self, authed_client, completed_job):
        resp = authed_client.get(f"/api/view/{completed_job}/slide/-1")
        assert resp.status_code in (400, 404, 422)

    def test_slide_returns_correct_content(self, authed_client, completed_job):
        resp = authed_client.get(f"/api/view/{completed_job}/slide/1")
        assert resp.content.startswith(b"\x89PNG")


# ---------------------------------------------------------------------------
# Video listing
# ---------------------------------------------------------------------------

class TestVideosList:
    """Video listing returns available videos with names and URLs."""

    def test_videos_returns_json(self, authed_client, completed_job):
        resp = authed_client.get(f"/api/view/{completed_job}/videos")
        assert resp.status_code == 200
        data = resp.json()
        assert "videos" in data

    def test_videos_count(self, authed_client, completed_job):
        resp = authed_client.get(f"/api/view/{completed_job}/videos")
        data = resp.json()
        assert len(data["videos"]) == 2

    def test_videos_have_name_and_url(self, authed_client, completed_job):
        resp = authed_client.get(f"/api/view/{completed_job}/videos")
        data = resp.json()
        for video in data["videos"]:
            assert "name" in video
            assert "url" in video
            assert "/video/" in video["url"]

    def test_videos_names_from_filenames(self, authed_client, completed_job):
        resp = authed_client.get(f"/api/view/{completed_job}/videos")
        data = resp.json()
        names = [v["name"] for v in data["videos"]]
        assert "Introduction" in names
        assert "Advanced Topics" in names

    def test_videos_no_video_dir(self, authed_client):
        """Job complete but no video_dir in result."""
        job_id = "eeff7788"
        capture = ProgressCapture()
        capture.status = "complete"
        capture.result = {"pdf_path": "/fake/path.pdf"}
        jobs[job_id] = capture
        resp = authed_client.get(f"/api/view/{job_id}/videos")
        data = resp.json()
        assert data["videos"] == []


# ---------------------------------------------------------------------------
# Video streaming
# ---------------------------------------------------------------------------

class TestVideoStream:
    """Video stream serves MP4 files."""

    def test_video_returns_200(self, authed_client, completed_job):
        resp = authed_client.get(f"/api/view/{completed_job}/video/0")
        assert resp.status_code == 200

    def test_video_content_type_mp4(self, authed_client, completed_job):
        resp = authed_client.get(f"/api/view/{completed_job}/video/0")
        assert "video/mp4" in resp.headers["content-type"]

    def test_video_index_out_of_range(self, authed_client, completed_job):
        resp = authed_client.get(f"/api/view/{completed_job}/video/99")
        assert resp.status_code == 404

    def test_video_second_file(self, authed_client, completed_job):
        resp = authed_client.get(f"/api/view/{completed_job}/video/1")
        assert resp.status_code == 200

    def test_video_negative_index(self, authed_client, completed_job):
        resp = authed_client.get(f"/api/view/{completed_job}/video/-1")
        assert resp.status_code in (400, 404, 422)


# ---------------------------------------------------------------------------
# Security headers (CSP + X-Frame-Options updates)
# ---------------------------------------------------------------------------

class TestSecurityHeaders:
    """Verify updated security headers allow iframe and video playback."""

    def test_x_frame_options_sameorigin(self, authed_client, completed_job):
        resp = authed_client.get(f"/api/view/{completed_job}/pdf")
        assert resp.headers.get("X-Frame-Options") == "SAMEORIGIN"

    def test_csp_includes_media_src(self, authed_client, completed_job):
        resp = authed_client.get(f"/api/view/{completed_job}/pdf")
        csp = resp.headers.get("Content-Security-Policy", "")
        assert "media-src 'self'" in csp

    def test_csp_includes_frame_src(self, authed_client, completed_job):
        resp = authed_client.get(f"/api/view/{completed_job}/pdf")
        csp = resp.headers.get("Content-Security-Policy", "")
        assert "frame-src 'self'" in csp
