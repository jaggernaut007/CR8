"""Tests for update_job_result with the pipeline_data parameter (v0.5.4).

These tests supplement backend/tests/test_db_client.py which already covers
the backward-compatible (pipeline_data=None) path.  These tests verify that
topics, gap_summary, modules_md, and curriculum_scope are correctly serialised
and passed to the SQL UPDATE statement.

All tests mock asyncpg.Pool — no real database connection is needed.
"""

from __future__ import annotations

import json
import sys
import types
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# asyncpg stub (mirrors the approach in test_db_client.py)
# ---------------------------------------------------------------------------

_real_asyncpg = sys.modules.get("asyncpg")
if _real_asyncpg is None:
    _asyncpg_stub = types.ModuleType("asyncpg")
    _asyncpg_stub.Pool = MagicMock()  # type: ignore[attr-defined]
    sys.modules["asyncpg"] = _asyncpg_stub

from backend.services import db_client  # noqa: E402

_JOB_ID = str(uuid.uuid4())


def _make_pool() -> AsyncMock:
    pool = AsyncMock()
    pool.fetchrow = AsyncMock()
    pool.fetch = AsyncMock()
    pool.execute = AsyncMock()
    return pool


# ---------------------------------------------------------------------------
# update_job_result — pipeline_data parameter
# ---------------------------------------------------------------------------


class TestUpdateJobResultWithPipelineData:
    """Verify that pipeline_data fields are serialised and included in the SQL call."""

    @pytest.mark.asyncio
    async def test_none_pipeline_data_backward_compatible(self):
        """Calling without pipeline_data (default None) must still execute once."""
        pool = _make_pool()
        pool.execute.return_value = "UPDATE 1"

        await db_client.update_job_result(pool, _JOB_ID, "complete", None)

        pool.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_topics_serialised_to_json_string(self):
        """topics list must be JSON-serialised before being passed to execute."""
        pool = _make_pool()
        pool.execute.return_value = "UPDATE 1"
        topics = [{"name": "Transformers"}, {"name": "BERT"}]

        await db_client.update_job_result(
            pool,
            _JOB_ID,
            "complete",
            None,
            pipeline_data={"topics": topics},
        )

        args = pool.execute.call_args[0]
        assert json.dumps(topics) in args

    @pytest.mark.asyncio
    async def test_gap_summary_serialised_to_json_string(self):
        """gap_summary list must be JSON-serialised before being passed to execute."""
        pool = _make_pool()
        pool.execute.return_value = "UPDATE 1"
        gap_summary = [{"topic": "BERT", "concept": "fine-tuning"}]

        await db_client.update_job_result(
            pool,
            _JOB_ID,
            "complete",
            None,
            pipeline_data={"gap_summary": gap_summary},
        )

        args = pool.execute.call_args[0]
        assert json.dumps(gap_summary) in args

    @pytest.mark.asyncio
    async def test_modules_md_serialised_to_json_string(self):
        """modules_md list must be JSON-serialised before being passed to execute."""
        pool = _make_pool()
        pool.execute.return_value = "UPDATE 1"
        modules_md = ["# Module 1 content", "# Module 2 content"]

        await db_client.update_job_result(
            pool,
            _JOB_ID,
            "complete",
            None,
            pipeline_data={"modules_md": modules_md},
        )

        args = pool.execute.call_args[0]
        assert json.dumps(modules_md) in args

    @pytest.mark.asyncio
    async def test_curriculum_scope_passed_as_plain_string(self):
        """curriculum_scope must be passed as a plain string (not JSON-encoded)."""
        pool = _make_pool()
        pool.execute.return_value = "UPDATE 1"

        await db_client.update_job_result(
            pool,
            _JOB_ID,
            "complete",
            None,
            pipeline_data={"curriculum_scope": "NLP and ML"},
        )

        args = pool.execute.call_args[0]
        assert "NLP and ML" in args

    @pytest.mark.asyncio
    async def test_empty_pipeline_data_dict_does_not_raise(self):
        """An empty pipeline_data dict must not raise any exception."""
        pool = _make_pool()
        pool.execute.return_value = "UPDATE 1"

        await db_client.update_job_result(
            pool,
            _JOB_ID,
            "complete",
            None,
            pipeline_data={},
        )

        pool.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_full_pipeline_data_calls_execute_once(self):
        """A full pipeline_data payload must result in exactly one SQL execute call."""
        pool = _make_pool()
        pool.execute.return_value = "UPDATE 1"

        await db_client.update_job_result(
            pool,
            _JOB_ID,
            "complete",
            {"result_meta_key": "value"},
            pipeline_data={
                "topics": [{"name": "T1"}, {"name": "T2"}],
                "gap_summary": [{"concept": "C1", "topic": "T1"}],
                "modules_md": ["# Module content for T1", "# Module content for T2"],
                "curriculum_scope": "Computer Science",
            },
        )

        pool.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_sql_references_topics_column(self):
        """The UPDATE SQL must reference the topics column."""
        pool = _make_pool()
        pool.execute.return_value = "UPDATE 1"

        await db_client.update_job_result(
            pool,
            _JOB_ID,
            "complete",
            None,
            pipeline_data={"topics": [{"name": "T1"}]},
        )

        sql = pool.execute.call_args[0][0]
        assert "topics" in sql

    @pytest.mark.asyncio
    async def test_sql_references_gap_summary_column(self):
        """The UPDATE SQL must reference the gap_summary column."""
        pool = _make_pool()
        pool.execute.return_value = "UPDATE 1"

        await db_client.update_job_result(
            pool,
            _JOB_ID,
            "complete",
            None,
            pipeline_data={"gap_summary": []},
        )

        sql = pool.execute.call_args[0][0]
        assert "gap_summary" in sql

    @pytest.mark.asyncio
    async def test_sql_references_modules_md_column(self):
        """The UPDATE SQL must reference the modules_md column."""
        pool = _make_pool()
        pool.execute.return_value = "UPDATE 1"

        await db_client.update_job_result(pool, _JOB_ID, "complete", None)

        sql = pool.execute.call_args[0][0]
        assert "modules_md" in sql

    @pytest.mark.asyncio
    async def test_sql_references_curriculum_scope_column(self):
        """The UPDATE SQL must reference the curriculum_scope column."""
        pool = _make_pool()
        pool.execute.return_value = "UPDATE 1"

        await db_client.update_job_result(pool, _JOB_ID, "complete", None)

        sql = pool.execute.call_args[0][0]
        assert "curriculum_scope" in sql

    @pytest.mark.asyncio
    async def test_none_topics_passed_as_none_not_empty_string(self):
        """When topics is absent from pipeline_data, None must be passed to SQL (not '[]')."""
        pool = _make_pool()
        pool.execute.return_value = "UPDATE 1"

        await db_client.update_job_result(
            pool,
            _JOB_ID,
            "complete",
            None,
            pipeline_data={},  # no topics key
        )

        args = pool.execute.call_args[0]
        assert args[3] is None  # topics should be None when not supplied
