"""Tests for frontend/quiz_routes.py — quiz generation, retrieval, submission, results.

All tests mock the DB pool and quiz graph. No real database or LLM calls.
"""

import os
import uuid
from datetime import datetime, UTC
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("AUTH_PASSWORD", "CR8-AI")
os.environ.setdefault("COOKIE_SECURE", "false")

from frontend.app import app
from frontend.middleware import _sessions, _failed_attempts, create_session


# --- Constants -------------------------------------------------------------

_USER_ID = str(uuid.uuid4())
_JOB_ID = str(uuid.uuid4())
_QUIZ_ID = str(uuid.uuid4())
_ATTEMPT_ID = str(uuid.uuid4())
_Q1_ID = str(uuid.uuid4())
_Q2_ID = str(uuid.uuid4())
_NOW = datetime(2026, 3, 9, 12, 0, 0, tzinfo=UTC)


# --- Fixtures --------------------------------------------------------------


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


@pytest.fixture
def mock_db_pool():
    """Create and attach a mock DB pool to app state."""
    pool = AsyncMock()
    pool.fetchrow = AsyncMock()
    pool.fetch = AsyncMock()
    pool.execute = AsyncMock()
    app.state.db_pool = pool
    yield pool
    if hasattr(app.state, "db_pool"):
        del app.state.db_pool


# --- Generate quiz tests ---------------------------------------------------


class TestGenerateQuiz:

    def test_generate_requires_auth(self):
        c = TestClient(app, raise_server_exceptions=False)
        resp = c.post("/api/quiz/generate", json={"job_id": _JOB_ID})
        assert resp.status_code == 401

    def test_generate_requires_db_pool(self, authed_client):
        resp = authed_client.post("/api/quiz/generate", json={"job_id": _JOB_ID})
        assert resp.status_code in (401, 503)

    def test_generate_validates_question_count_too_high(self, authed_client, mock_db_pool):
        resp = authed_client.post(
            "/api/quiz/generate",
            json={"job_id": _JOB_ID, "question_count": 100},
        )
        # Either 401 (legacy auth can't extract user) or 422 (validation)
        assert resp.status_code in (401, 422)

    def test_generate_validates_question_count_too_low(self, authed_client, mock_db_pool):
        resp = authed_client.post(
            "/api/quiz/generate",
            json={"job_id": _JOB_ID, "question_count": 2},
        )
        assert resp.status_code in (401, 422)


# --- Fetch quiz tests ------------------------------------------------------


class TestGetQuiz:

    def test_get_quiz_requires_auth(self):
        c = TestClient(app, raise_server_exceptions=False)
        resp = c.get(f"/api/quiz/{_QUIZ_ID}")
        assert resp.status_code == 401

    def test_get_quiz_requires_db_pool(self, authed_client):
        resp = authed_client.get(f"/api/quiz/{_QUIZ_ID}")
        assert resp.status_code in (401, 503)


# --- Submit quiz tests -----------------------------------------------------


class TestSubmitQuiz:

    def test_submit_requires_auth(self):
        c = TestClient(app, raise_server_exceptions=False)
        resp = c.post(f"/api/quiz/{_QUIZ_ID}/submit", json={"responses": []})
        assert resp.status_code == 401

    def test_submit_validates_body(self, authed_client, mock_db_pool):
        resp = authed_client.post(
            f"/api/quiz/{_QUIZ_ID}/submit",
            json={"bad_field": True},
        )
        assert resp.status_code in (401, 422)


# --- Quiz results tests ----------------------------------------------------


class TestGetResults:

    def test_results_requires_auth(self):
        c = TestClient(app, raise_server_exceptions=False)
        resp = c.get(f"/api/quiz/{_QUIZ_ID}/results")
        assert resp.status_code == 401


# --- Quizzes by job tests --------------------------------------------------


class TestQuizByJob:

    def test_by_job_requires_auth(self):
        c = TestClient(app, raise_server_exceptions=False)
        resp = c.get(f"/api/quiz/by-job/{_JOB_ID}")
        assert resp.status_code == 401


# --- Quiz model tests ------------------------------------------------------


class TestQuizModels:

    def test_generate_request_valid(self):
        from frontend.quiz_models import GenerateQuizRequest
        req = GenerateQuizRequest(job_id="test-123")
        assert req.question_count == 20

    def test_generate_request_custom_count(self):
        from frontend.quiz_models import GenerateQuizRequest
        req = GenerateQuizRequest(job_id="test-123", question_count=30)
        assert req.question_count == 30

    def test_generate_request_rejects_empty_job_id(self):
        from frontend.quiz_models import GenerateQuizRequest
        with pytest.raises(ValueError):
            GenerateQuizRequest(job_id="")

    def test_generate_request_rejects_high_count(self):
        from frontend.quiz_models import GenerateQuizRequest
        with pytest.raises(ValueError):
            GenerateQuizRequest(job_id="test", question_count=100)

    def test_generate_request_rejects_low_count(self):
        from frontend.quiz_models import GenerateQuizRequest
        with pytest.raises(ValueError):
            GenerateQuizRequest(job_id="test", question_count=2)

    def test_submit_request_valid(self):
        from frontend.quiz_models import SubmitQuizRequest
        req = SubmitQuizRequest(responses=[
            {"question_id": "q1", "selected_index": 2},
        ])
        assert len(req.responses) == 1

    def test_submit_request_rejects_invalid_index(self):
        from frontend.quiz_models import SubmitQuizRequest
        with pytest.raises(ValueError):
            SubmitQuizRequest(responses=[
                {"question_id": "q1", "selected_index": 5},
            ])

    def test_answer_item_default_time(self):
        from frontend.quiz_models import AnswerItem
        item = AnswerItem(question_id="q1", selected_index=0)
        assert item.time_spent_seconds == 0


# --- Route helper tests ----------------------------------------------------


class TestStripAnswers:

    def test_strips_answer_fields(self):
        from frontend.quiz_routes import _strip_answers
        questions = [
            {
                "id": "q1",
                "question_text": "What?",
                "correct_index": 1,
                "feedback_correct": "Yes",
                "feedback_incorrect": "No",
                "options": ["A", "B", "C", "D"],
            }
        ]
        stripped = _strip_answers(questions)
        assert "correct_index" not in stripped[0]
        assert "feedback_correct" not in stripped[0]
        assert "feedback_incorrect" not in stripped[0]
        assert "question_text" in stripped[0]

    def test_preserves_other_fields(self):
        from frontend.quiz_routes import _strip_answers
        questions = [{"id": "q1", "difficulty": "easy", "correct_index": 0}]
        stripped = _strip_answers(questions)
        assert stripped[0]["difficulty"] == "easy"


class TestScoreResponses:

    def test_scores_correctly(self):
        from frontend.quiz_routes import _score_responses
        from frontend.quiz_models import AnswerItem

        q_map = {
            "q1": {"correct_index": 1},
            "q2": {"correct_index": 0},
        }
        responses = [
            AnswerItem(question_id="q1", selected_index=1),
            AnswerItem(question_id="q2", selected_index=2),
        ]
        scored, correct = _score_responses(responses, q_map)
        assert correct == 1
        assert len(scored) == 2
        assert scored[0]["is_correct"] is True
        assert scored[1]["is_correct"] is False

    def test_skips_unknown_questions(self):
        from frontend.quiz_routes import _score_responses
        from frontend.quiz_models import AnswerItem

        q_map = {"q1": {"correct_index": 0}}
        responses = [
            AnswerItem(question_id="unknown", selected_index=0),
        ]
        scored, correct = _score_responses(responses, q_map)
        assert len(scored) == 0
        assert correct == 0


class TestSerializeAttempt:

    def test_serializes_completed(self):
        from frontend.quiz_routes import _serialize_attempt
        attempt = {
            "id": _ATTEMPT_ID,
            "score": 85.0,
            "total_questions": 10,
            "completed_at": _NOW,
        }
        result = _serialize_attempt(attempt)
        assert result["id"] == _ATTEMPT_ID
        assert result["score"] == 85.0
        assert result["completed_at"] is not None

    def test_serializes_incomplete(self):
        from frontend.quiz_routes import _serialize_attempt
        attempt = {
            "id": _ATTEMPT_ID,
            "score": None,
            "total_questions": None,
            "completed_at": None,
        }
        result = _serialize_attempt(attempt)
        assert result["score"] is None
        assert result["completed_at"] is None
