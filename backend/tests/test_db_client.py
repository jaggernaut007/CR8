"""Tests for the async database CRUD client (backend/services/db_client.py).

All tests mock asyncpg.Pool — no real database connection is needed.
"""

from __future__ import annotations

import sys
import types
import uuid
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# Ensure asyncpg is importable even without the real package installed.
# We stub just enough for the import of db_client to succeed.
# ---------------------------------------------------------------------------
_real_asyncpg = sys.modules.get("asyncpg")
if _real_asyncpg is None:
    _asyncpg_stub = types.ModuleType("asyncpg")
    _asyncpg_stub.Pool = MagicMock()  # type: ignore[attr-defined]
    sys.modules["asyncpg"] = _asyncpg_stub

from backend.services import db_client  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_record(data: dict) -> MagicMock:
    """Create a mock asyncpg Record that supports dict() and key access."""
    record = MagicMock()
    record.__getitem__ = lambda self, key: data[key]
    record.keys.return_value = data.keys()
    record.values.return_value = data.values()
    record.items.return_value = data.items()
    # Make dict(record) work via __iter__ + __len__
    record.__iter__ = lambda self: iter(data)
    record.__len__ = lambda self: len(data)
    return record


def _make_pool() -> AsyncMock:
    """Create a mock asyncpg.Pool with async methods."""
    pool = AsyncMock()
    pool.fetchrow = AsyncMock()
    pool.fetch = AsyncMock()
    pool.execute = AsyncMock()
    return pool


_NOW = datetime(2026, 3, 6, 12, 0, 0, tzinfo=UTC)
_USER_ID = str(uuid.uuid4())
_JOB_ID = str(uuid.uuid4())
_QUIZ_ID = str(uuid.uuid4())


# ---------------------------------------------------------------------------
# User CRUD tests
# ---------------------------------------------------------------------------


class TestCreateUser:
    @pytest.mark.asyncio
    async def test_create_user_returns_dict(self):
        pool = _make_pool()
        row_data = {
            "id": _USER_ID,
            "email": "alice@example.com",
            "password_hash": "$2b$12$hash",
            "role": "user",
            "created_at": _NOW,
            "updated_at": _NOW,
        }
        pool.fetchrow.return_value = _make_record(row_data)

        result = await db_client.create_user(pool, "alice@example.com", "$2b$12$hash")

        assert result["email"] == "alice@example.com"
        assert result["id"] == _USER_ID
        pool.fetchrow.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_user_passes_params(self):
        pool = _make_pool()
        pool.fetchrow.return_value = _make_record({"id": _USER_ID, "email": "b@b.com"})

        await db_client.create_user(pool, "b@b.com", "hash123")

        args = pool.fetchrow.call_args
        assert "b@b.com" in args[0]
        assert "hash123" in args[0]


class TestGetUserByEmail:
    @pytest.mark.asyncio
    async def test_found(self):
        pool = _make_pool()
        pool.fetchrow.return_value = _make_record({"id": _USER_ID, "email": "a@a.com"})

        result = await db_client.get_user_by_email(pool, "a@a.com")

        assert result is not None
        assert result["email"] == "a@a.com"

    @pytest.mark.asyncio
    async def test_not_found(self):
        pool = _make_pool()
        pool.fetchrow.return_value = None

        result = await db_client.get_user_by_email(pool, "nobody@x.com")

        assert result is None


class TestGetUserById:
    @pytest.mark.asyncio
    async def test_found(self):
        pool = _make_pool()
        pool.fetchrow.return_value = _make_record({"id": _USER_ID, "email": "u@u.com"})

        result = await db_client.get_user_by_id(pool, _USER_ID)

        assert result is not None
        assert result["id"] == _USER_ID

    @pytest.mark.asyncio
    async def test_not_found(self):
        pool = _make_pool()
        pool.fetchrow.return_value = None

        result = await db_client.get_user_by_id(pool, "nonexistent")

        assert result is None


# ---------------------------------------------------------------------------
# Job CRUD tests
# ---------------------------------------------------------------------------


class TestCreateJob:
    @pytest.mark.asyncio
    async def test_create_job_returns_dict(self):
        pool = _make_pool()
        row_data = {
            "id": _JOB_ID,
            "user_id": _USER_ID,
            "short_id": "ab12cd34",
            "status": "pending",
            "file_names": ["lecture.pdf"],
            "output_formats": "pdf",
        }
        pool.fetchrow.return_value = _make_record(row_data)

        result = await db_client.create_job(
            pool, _USER_ID, "ab12cd34", ["lecture.pdf"], "pdf"
        )

        assert result["short_id"] == "ab12cd34"
        assert result["status"] == "pending"


class TestUpdateJobProgress:
    @pytest.mark.asyncio
    async def test_calls_execute(self):
        pool = _make_pool()
        pool.execute.return_value = "UPDATE 1"

        await db_client.update_job_progress(pool, _JOB_ID, 50, "research")

        pool.execute.assert_awaited_once()
        args = pool.execute.call_args[0]
        assert 50 in args
        assert "research" in args


class TestUpdateJobResult:
    @pytest.mark.asyncio
    async def test_calls_execute(self):
        pool = _make_pool()
        pool.execute.return_value = "UPDATE 1"
        meta = {"topics": 5, "path": "/out/guide.pdf"}

        await db_client.update_job_result(pool, _JOB_ID, "completed", meta)

        pool.execute.assert_awaited_once()
        args = pool.execute.call_args[0]
        assert "completed" in args


class TestGetJob:
    @pytest.mark.asyncio
    async def test_found(self):
        pool = _make_pool()
        pool.fetchrow.return_value = _make_record(
            {"id": _JOB_ID, "status": "running"}
        )

        result = await db_client.get_job(pool, _JOB_ID)

        assert result is not None
        assert result["status"] == "running"

    @pytest.mark.asyncio
    async def test_not_found(self):
        pool = _make_pool()
        pool.fetchrow.return_value = None

        result = await db_client.get_job(pool, "missing-id")

        assert result is None


class TestGetJobByShortId:
    @pytest.mark.asyncio
    async def test_found(self):
        pool = _make_pool()
        pool.fetchrow.return_value = _make_record(
            {"id": _JOB_ID, "short_id": "aabb1122"}
        )

        result = await db_client.get_job_by_short_id(pool, "aabb1122")

        assert result is not None
        assert result["short_id"] == "aabb1122"


class TestListJobs:
    @pytest.mark.asyncio
    async def test_returns_list(self):
        pool = _make_pool()
        pool.fetch.return_value = [
            _make_record({"id": "j1", "status": "completed"}),
            _make_record({"id": "j2", "status": "pending"}),
        ]

        result = await db_client.list_jobs(pool, _USER_ID)

        assert len(result) == 2
        assert result[0]["id"] == "j1"

    @pytest.mark.asyncio
    async def test_empty_list(self):
        pool = _make_pool()
        pool.fetch.return_value = []

        result = await db_client.list_jobs(pool, _USER_ID, limit=10, offset=5)

        assert result == []


class TestMarkStaleJobs:
    @pytest.mark.asyncio
    async def test_returns_count(self):
        pool = _make_pool()
        pool.execute.return_value = "UPDATE 3"

        count = await db_client.mark_stale_jobs_as_error(pool)

        assert count == 3

    @pytest.mark.asyncio
    async def test_zero_stale(self):
        pool = _make_pool()
        pool.execute.return_value = "UPDATE 0"

        count = await db_client.mark_stale_jobs_as_error(pool)

        assert count == 0


# ---------------------------------------------------------------------------
# Quiz stub tests
# ---------------------------------------------------------------------------


class TestCreateQuiz:
    @pytest.mark.asyncio
    async def test_create_quiz_returns_dict(self):
        pool = _make_pool()
        pool.fetchrow.return_value = _make_record(
            {"id": _QUIZ_ID, "job_id": _JOB_ID, "title": "Week 1 Quiz"}
        )

        result = await db_client.create_quiz(pool, _JOB_ID, "Week 1 Quiz")

        assert result["title"] == "Week 1 Quiz"
        assert result["id"] == _QUIZ_ID


class TestGetQuizzesForJob:
    @pytest.mark.asyncio
    async def test_returns_list(self):
        pool = _make_pool()
        pool.fetch.return_value = [
            _make_record({"id": "q1", "title": "Quiz 1"}),
        ]

        result = await db_client.get_quizzes_for_job(pool, _JOB_ID)

        assert len(result) == 1
        assert result[0]["title"] == "Quiz 1"

    @pytest.mark.asyncio
    async def test_empty(self):
        pool = _make_pool()
        pool.fetch.return_value = []

        result = await db_client.get_quizzes_for_job(pool, _JOB_ID)

        assert result == []
