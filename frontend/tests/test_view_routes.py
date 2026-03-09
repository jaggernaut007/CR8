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
import frontend.view_routes as view_routes_mod

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


@pytest.fixture(autouse=True)
def _patch_outputs_dir(tmp_path, monkeypatch):
    """Point _OUTPUTS_DIR at tmp_path so _safe_path allows test files."""
    monkeypatch.setattr(view_routes_mod, "_OUTPUTS_DIR", str(tmp_path))


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

    def test_slide_image_invalid_job_id(self, authed_client):
        """Individual slide endpoint also validates job_id format."""
        resp = authed_client.get("/api/view/BADID!!!/slide/1")
        assert resp.status_code == 400

    def test_videos_list_invalid_job_id(self, authed_client):
        """Video list endpoint also validates job_id format."""
        resp = authed_client.get("/api/view/ZZZZZZZZ/videos")
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

    def test_video_job_not_found(self, authed_client):
        """Video list returns 404 for unknown job IDs."""
        resp = authed_client.get("/api/view/deadbeef/videos")
        assert resp.status_code == 404

    def test_video_stream_job_not_found(self, authed_client):
        """Video stream returns 404 for unknown job IDs."""
        resp = authed_client.get("/api/view/deadbeef/video/0")
        assert resp.status_code == 404

    def test_slide_job_not_found(self, authed_client):
        """Individual slide returns 404 for unknown job IDs."""
        resp = authed_client.get("/api/view/deadbeef/slide/1")
        assert resp.status_code == 404

    def test_complete_job_with_null_result(self, authed_client):
        """Status is complete but result is None — treated as not complete."""
        job_id = "aabbccdd"
        capture = ProgressCapture()
        capture.status = "complete"
        capture.result = None
        jobs[job_id] = capture
        resp = authed_client.get(f"/api/view/{job_id}/pdf")
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

    def test_pdf_path_key_present_but_file_missing(self, authed_client):
        """pdf_path key in result but file does not exist on disk."""
        job_id = "11223344"
        capture = ProgressCapture()
        capture.status = "complete"
        capture.result = {"pdf_path": "/nonexistent/path/output.pdf"}
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

    def test_slides_urls_contain_job_id(self, authed_client, completed_job):
        """Each slide URL must include the job_id so the client can route correctly."""
        resp = authed_client.get(f"/api/view/{completed_job}/slides")
        data = resp.json()
        for url in data["slides"]:
            assert completed_job in url

    def test_slides_stale_paths_excluded(self, authed_client):
        """slide_images in result point to files that no longer exist on disk."""
        job_id = "55667788"
        capture = ProgressCapture()
        capture.status = "complete"
        capture.result = {
            "slide_images": [
                "/nonexistent/slide_01.png",
                "/nonexistent/slide_02.png",
            ],
        }
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

    def test_slide_last_index_valid(self, authed_client, completed_job):
        """Index equal to total (3) is the last valid slide."""
        resp = authed_client.get(f"/api/view/{completed_job}/slide/3")
        assert resp.status_code == 200

    def test_slide_when_all_paths_stale(self, authed_client):
        """All slide_images paths no longer exist — any index should 404."""
        job_id = "aa11bb22"
        capture = ProgressCapture()
        capture.status = "complete"
        capture.result = {"slide_images": ["/nonexistent/slide_01.png"]}
        jobs[job_id] = capture
        resp = authed_client.get(f"/api/view/{job_id}/slide/1")
        assert resp.status_code == 404


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

    def test_videos_video_dir_nonexistent(self, authed_client):
        """video_dir key present but directory does not exist on disk."""
        job_id = "ff001122"
        capture = ProgressCapture()
        capture.status = "complete"
        capture.result = {"video_dir": "/nonexistent/video/dir"}
        jobs[job_id] = capture
        resp = authed_client.get(f"/api/view/{job_id}/videos")
        data = resp.json()
        assert data["videos"] == []

    def test_videos_urls_contain_job_id(self, authed_client, completed_job):
        """Each video URL must include the job_id for correct routing."""
        resp = authed_client.get(f"/api/view/{completed_job}/videos")
        data = resp.json()
        for video in data["videos"]:
            assert completed_job in video["url"]

    def test_videos_sorted_by_filename(self, authed_client, completed_job):
        """Videos are returned sorted — alphabetical order by filename."""
        resp = authed_client.get(f"/api/view/{completed_job}/videos")
        data = resp.json()
        names = [v["name"] for v in data["videos"]]
        # "Advanced Topics" sorts before "Introduction" alphabetically
        assert names.index("Advanced Topics") < names.index("Introduction")

    def test_videos_non_mp4_files_excluded(self, authed_client, tmp_path):
        """Files with extensions other than .mp4 are not listed."""
        job_id = "cc334455"
        video_dir = tmp_path / "mixed_videos"
        video_dir.mkdir()
        (video_dir / "clip.mp4").write_bytes(b"\x00\x00\x00 ftyp")
        (video_dir / "thumbnail.jpg").write_bytes(b"\xff\xd8\xff fake jpg")
        (video_dir / "notes.txt").write_bytes(b"text content")
        capture = ProgressCapture()
        capture.status = "complete"
        capture.result = {"video_dir": str(video_dir)}
        jobs[job_id] = capture
        resp = authed_client.get(f"/api/view/{job_id}/videos")
        data = resp.json()
        assert len(data["videos"]) == 1
        assert data["videos"][0]["name"] == "clip"


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

    def test_video_stream_nonexistent_video_dir(self, authed_client):
        """video_dir present in result but directory missing — index 0 is out of range."""
        job_id = "dd556677"
        capture = ProgressCapture()
        capture.status = "complete"
        capture.result = {"video_dir": "/nonexistent/videos"}
        jobs[job_id] = capture
        resp = authed_client.get(f"/api/view/{job_id}/video/0")
        assert resp.status_code == 404


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


# ---------------------------------------------------------------------------
# Path traversal protection
# ---------------------------------------------------------------------------

class TestPathTraversal:
    """_safe_path blocks file access outside the outputs directory."""

    def test_pdf_path_traversal_blocked(self, authed_client):
        """Pipeline path pointing outside outputs/ is blocked."""
        job_id = "ff112233"
        capture = ProgressCapture()
        capture.status = "complete"
        capture.result = {"pdf_path": "/etc/passwd"}
        jobs[job_id] = capture
        resp = authed_client.get(f"/api/view/{job_id}/pdf")
        assert resp.status_code == 404

    def test_slide_path_traversal_blocked(self, authed_client, tmp_path):
        """Slide images outside outputs/ are blocked."""
        job_id = "ee223344"
        capture = ProgressCapture()
        capture.status = "complete"
        evil_path = "/etc/shadow"
        capture.result = {"slide_images": [evil_path]}
        jobs[job_id] = capture
        resp = authed_client.get(f"/api/view/{job_id}/slide/1")
        assert resp.status_code == 404

    def test_video_path_traversal_blocked(self, authed_client, tmp_path):
        """Video dir outside outputs/ is blocked even if files exist."""
        # Create a video outside the outputs dir
        evil_dir = tmp_path / ".." / "evil_videos"
        evil_dir.mkdir(parents=True, exist_ok=True)
        (evil_dir / "steal.mp4").write_bytes(b"fake mp4")
        job_id = "dd445566"
        capture = ProgressCapture()
        capture.status = "complete"
        capture.result = {"video_dir": str(evil_dir)}
        jobs[job_id] = capture
        resp = authed_client.get(f"/api/view/{job_id}/video/0")
        assert resp.status_code == 404
