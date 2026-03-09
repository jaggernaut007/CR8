"""Tests for _validate_job_for_quiz in frontend/quiz_routes.py.

Covers the four validation cases:
1. Job not found → 404
2. Job ownership mismatch → 404
3. Job status != 'complete' → 400
4. Job has no topics → 400
5. Valid job returns (job_dict, None)

The function uses a lazy import inside its body:
    from backend.services.db_client import get_job

So we patch at the source module: ``backend.services.db_client``.
"""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest

_USER_ID = str(uuid.uuid4())
_OTHER_USER_ID = str(uuid.uuid4())
_JOB_ID = str(uuid.uuid4())


def _make_user(user_id: str = _USER_ID) -> dict:
    return {"id": user_id, "email": "test@test.com", "role": "user"}


def _make_complete_job(user_id: str = _USER_ID, topics: list | None = None) -> dict:
    return {
        "id": _JOB_ID,
        "user_id": user_id,
        "status": "complete",
        "topics": topics if topics is not None else [{"name": "Transformers"}],
        "gap_summary": [],
        "modules_md": [],
        "curriculum_scope": "NLP",
    }


# ---------------------------------------------------------------------------
# Job not found
# ---------------------------------------------------------------------------


class TestValidateJobForQuizNotFound:

    @pytest.mark.asyncio
    async def test_returns_none_job_when_get_job_returns_none(self):
        """When get_job returns None, must return (None, JSONResponse 404)."""
        from frontend.quiz_routes import _validate_job_for_quiz

        pool = AsyncMock()
        user = _make_user()

        with patch("backend.services.db_client.get_job", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            job, err = await _validate_job_for_quiz(pool, _JOB_ID, user)

        assert job is None
        assert err is not None

    @pytest.mark.asyncio
    async def test_returns_404_when_get_job_returns_none(self):
        """404 status must be returned when job does not exist."""
        from frontend.quiz_routes import _validate_job_for_quiz

        pool = AsyncMock()
        user = _make_user()

        with patch("backend.services.db_client.get_job", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            _, err = await _validate_job_for_quiz(pool, _JOB_ID, user)

        assert err.status_code == 404

    @pytest.mark.asyncio
    async def test_error_body_is_json_when_not_found(self):
        """The 404 error response body must be valid JSON with an 'error' key."""
        from frontend.quiz_routes import _validate_job_for_quiz

        pool = AsyncMock()
        user = _make_user()

        with patch("backend.services.db_client.get_job", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None

            _, err = await _validate_job_for_quiz(pool, _JOB_ID, user)

        body = json.loads(err.body)
        assert "error" in body


# ---------------------------------------------------------------------------
# Ownership mismatch
# ---------------------------------------------------------------------------


class TestValidateJobForQuizOwnershipMismatch:

    @pytest.mark.asyncio
    async def test_returns_none_job_when_different_owner(self):
        """A job owned by a different user must return None for job."""
        from frontend.quiz_routes import _validate_job_for_quiz

        pool = AsyncMock()
        user = _make_user(_USER_ID)
        job = _make_complete_job(user_id=_OTHER_USER_ID)

        with patch("backend.services.db_client.get_job", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = job

            result_job, err = await _validate_job_for_quiz(pool, _JOB_ID, user)

        assert result_job is None
        assert err is not None

    @pytest.mark.asyncio
    async def test_returns_404_not_403_for_ownership_mismatch(self):
        """Ownership mismatch must return 404 (not 403) to hide existence of other users' jobs."""
        from frontend.quiz_routes import _validate_job_for_quiz

        pool = AsyncMock()
        user = _make_user(_USER_ID)
        job = _make_complete_job(user_id=_OTHER_USER_ID)

        with patch("backend.services.db_client.get_job", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = job

            _, err = await _validate_job_for_quiz(pool, _JOB_ID, user)

        assert err.status_code == 404
        assert err.status_code != 403


# ---------------------------------------------------------------------------
# Incomplete job
# ---------------------------------------------------------------------------


class TestValidateJobForQuizIncompleteStatus:

    @pytest.mark.asyncio
    async def test_returns_400_when_job_is_running(self):
        """A job with status='running' must return 400."""
        from frontend.quiz_routes import _validate_job_for_quiz

        pool = AsyncMock()
        user = _make_user()
        job = _make_complete_job()
        job["status"] = "running"

        with patch("backend.services.db_client.get_job", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = job

            result_job, err = await _validate_job_for_quiz(pool, _JOB_ID, user)

        assert result_job is None
        assert err is not None
        assert err.status_code == 400

    @pytest.mark.asyncio
    async def test_returns_400_when_job_is_error(self):
        """A job with status='error' must return 400."""
        from frontend.quiz_routes import _validate_job_for_quiz

        pool = AsyncMock()
        user = _make_user()
        job = _make_complete_job()
        job["status"] = "error"

        with patch("backend.services.db_client.get_job", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = job

            _, err = await _validate_job_for_quiz(pool, _JOB_ID, user)

        assert err.status_code == 400

    @pytest.mark.asyncio
    async def test_returns_400_when_job_is_pending(self):
        """A job with status='pending' must return 400."""
        from frontend.quiz_routes import _validate_job_for_quiz

        pool = AsyncMock()
        user = _make_user()
        job = _make_complete_job()
        job["status"] = "pending"

        with patch("backend.services.db_client.get_job", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = job

            _, err = await _validate_job_for_quiz(pool, _JOB_ID, user)

        assert err.status_code == 400

    @pytest.mark.asyncio
    async def test_incomplete_error_message_mentions_complete(self):
        """The 400 error body must mention the word 'complete'."""
        from frontend.quiz_routes import _validate_job_for_quiz

        pool = AsyncMock()
        user = _make_user()
        job = _make_complete_job()
        job["status"] = "running"

        with patch("backend.services.db_client.get_job", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = job

            _, err = await _validate_job_for_quiz(pool, _JOB_ID, user)

        body = json.loads(err.body)
        assert "complete" in body["error"].lower()


# ---------------------------------------------------------------------------
# No topics
# ---------------------------------------------------------------------------


class TestValidateJobForQuizNoTopics:

    @pytest.mark.asyncio
    async def test_returns_400_when_topics_is_empty_list(self):
        """A complete job with an empty topics list must return 400."""
        from frontend.quiz_routes import _validate_job_for_quiz

        pool = AsyncMock()
        user = _make_user()
        job = _make_complete_job(topics=[])

        with patch("backend.services.db_client.get_job", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = job

            result_job, err = await _validate_job_for_quiz(pool, _JOB_ID, user)

        assert result_job is None
        assert err is not None
        assert err.status_code == 400

    @pytest.mark.asyncio
    async def test_returns_400_when_topics_is_none(self):
        """A complete job with topics=None must return 400."""
        from frontend.quiz_routes import _validate_job_for_quiz

        pool = AsyncMock()
        user = _make_user()
        job = _make_complete_job()
        job["topics"] = None

        with patch("backend.services.db_client.get_job", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = job

            _, err = await _validate_job_for_quiz(pool, _JOB_ID, user)

        assert err.status_code == 400

    @pytest.mark.asyncio
    async def test_no_topics_error_message_mentions_topic(self):
        """The 400 error body must mention 'topic'."""
        from frontend.quiz_routes import _validate_job_for_quiz

        pool = AsyncMock()
        user = _make_user()
        job = _make_complete_job(topics=[])

        with patch("backend.services.db_client.get_job", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = job

            _, err = await _validate_job_for_quiz(pool, _JOB_ID, user)

        body = json.loads(err.body)
        assert "topic" in body["error"].lower()


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestValidateJobForQuizHappyPath:

    @pytest.mark.asyncio
    async def test_returns_job_and_none_error_for_valid_job(self):
        """A complete job with matching owner and non-empty topics must return (job, None)."""
        from frontend.quiz_routes import _validate_job_for_quiz

        pool = AsyncMock()
        user = _make_user()
        job = _make_complete_job()

        with patch("backend.services.db_client.get_job", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = job

            result_job, err = await _validate_job_for_quiz(pool, _JOB_ID, user)

        assert err is None
        assert result_job is not None
        assert result_job["id"] == _JOB_ID

    @pytest.mark.asyncio
    async def test_returned_job_contains_topics(self):
        """The returned job dict must include the topics list."""
        from frontend.quiz_routes import _validate_job_for_quiz

        pool = AsyncMock()
        user = _make_user()
        topics = [{"name": "Transformers"}, {"name": "BERT"}]
        job = _make_complete_job(topics=topics)

        with patch("backend.services.db_client.get_job", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = job

            result_job, _ = await _validate_job_for_quiz(pool, _JOB_ID, user)

        assert result_job["topics"] == topics

    @pytest.mark.asyncio
    async def test_ownership_check_uses_string_comparison(self):
        """Ownership check must work when user_id is stored as a plain string UUID."""
        from frontend.quiz_routes import _validate_job_for_quiz

        pool = AsyncMock()
        user = {"id": str(_USER_ID), "email": "test@test.com"}
        job = _make_complete_job(user_id=str(_USER_ID))

        with patch("backend.services.db_client.get_job", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = job

            result_job, err = await _validate_job_for_quiz(pool, _JOB_ID, user)

        assert err is None
        assert result_job is not None

    @pytest.mark.asyncio
    async def test_single_topic_is_enough(self):
        """A single topic in the topics list must be sufficient to pass validation."""
        from frontend.quiz_routes import _validate_job_for_quiz

        pool = AsyncMock()
        user = _make_user()
        job = _make_complete_job(topics=[{"name": "Single Topic"}])

        with patch("backend.services.db_client.get_job", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = job

            result_job, err = await _validate_job_for_quiz(pool, _JOB_ID, user)

        assert err is None
        assert result_job is not None
