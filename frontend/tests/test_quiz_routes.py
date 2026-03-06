"""Tests for frontend/quiz_routes.py — all endpoints return 501 Not Implemented."""

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("AUTH_PASSWORD", "CR8-AI")
os.environ.setdefault("COOKIE_SECURE", "false")

from frontend.app import app
from frontend.middleware import _sessions, _failed_attempts, create_session


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clean_auth_state():
    """Clear rate-limit and session state before and after each test."""
    _sessions.clear()
    _failed_attempts.clear()
    yield
    _sessions.clear()
    _failed_attempts.clear()


@pytest.fixture
def authed_client():
    """TestClient with a pre-seeded valid legacy session cookie."""
    c = TestClient(app, raise_server_exceptions=False)
    token = create_session()
    c.cookies.set("cr8_session", token)
    return c


# ---------------------------------------------------------------------------
# GET /api/quiz/
# ---------------------------------------------------------------------------


class TestListQuizzes:

    def test_list_quizzes_returns_501(self, authed_client):
        resp = authed_client.get("/api/quiz/")
        assert resp.status_code == 501

    def test_list_quizzes_error_key_present(self, authed_client):
        resp = authed_client.get("/api/quiz/")
        assert "error" in resp.json()

    def test_list_quizzes_not_implemented_message(self, authed_client):
        resp = authed_client.get("/api/quiz/")
        assert "not yet implemented" in resp.json()["error"].lower()



# Get quiz endpoint tests


class TestGetQuiz:

    def test_get_quiz_returns_501(self, authed_client):
        resp = authed_client.get("/api/quiz/some-quiz-id")
        assert resp.status_code == 501

    def test_get_quiz_error_key_present(self, authed_client):
        resp = authed_client.get("/api/quiz/some-quiz-id")
        assert "error" in resp.json()

    def test_get_quiz_not_implemented_message(self, authed_client):
        resp = authed_client.get("/api/quiz/some-quiz-id")
        assert "not yet implemented" in resp.json()["error"].lower()



# Start quiz endpoint tests


class TestStartQuiz:

    def test_start_quiz_returns_501(self, authed_client):
        resp = authed_client.post("/api/quiz/some-quiz-id/start")
        assert resp.status_code == 501

    def test_start_quiz_error_key_present(self, authed_client):
        resp = authed_client.post("/api/quiz/some-quiz-id/start")
        assert "error" in resp.json()

    def test_start_quiz_not_implemented_message(self, authed_client):
        resp = authed_client.post("/api/quiz/some-quiz-id/start")
        assert "not yet implemented" in resp.json()["error"].lower()



# Submit quiz endpoint tests


class TestSubmitQuiz:

    def test_submit_quiz_returns_501(self, authed_client):
        resp = authed_client.post("/api/quiz/some-quiz-id/submit")
        assert resp.status_code == 501

    def test_submit_quiz_error_key_present(self, authed_client):
        resp = authed_client.post("/api/quiz/some-quiz-id/submit")
        assert "error" in resp.json()

    def test_submit_quiz_not_implemented_message(self, authed_client):
        resp = authed_client.post("/api/quiz/some-quiz-id/submit")
        assert "not yet implemented" in resp.json()["error"].lower()
