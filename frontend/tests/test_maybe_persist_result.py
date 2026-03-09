"""Tests for _maybe_persist_result in frontend/job_routes.py.

Covers the four guard conditions:
1. Does nothing when capture.status != 'complete'
2. Does nothing when capture._db_persisted is True
3. Does nothing when no DB pool or no authenticated user
4. Persists when complete + pool + user available (first time only)

The function uses lazy imports inside its body:
    from backend.services.db_client import get_job_by_short_id, update_job_result

So we patch at the source module: ``backend.services.db_client``.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Minimal ProgressCapture stand-in
# ---------------------------------------------------------------------------


class _FakeCapture:
    """Minimal stand-in for ProgressCapture. Only fields used by _maybe_persist_result."""

    def __init__(
        self,
        *,
        status: str = "running",
        db_persisted: bool = False,
        result: dict | None = None,
    ):
        self.status = status
        self._db_persisted = db_persisted
        self.result = result or {}


# ---------------------------------------------------------------------------
# Request stub builder
# ---------------------------------------------------------------------------


def _make_request(*, pool=None, user=None) -> MagicMock:
    """Build a mock FastAPI Request with configurable app.state and state."""
    request = MagicMock()

    # Simulate getattr(request.app.state, 'db_pool', None)
    if pool is None:
        # Use spec=[] so that getattr falls through to None
        app_state = MagicMock(spec=[])
    else:
        app_state = MagicMock()
        app_state.db_pool = pool
    request.app.state = app_state

    # Simulate getattr(request.state, 'user', None)
    request_state = MagicMock()
    request_state.user = user
    request.state = request_state

    return request


class TestMaybePersistResultStatusGuard:

    @pytest.mark.asyncio
    async def test_does_nothing_when_status_is_running(self):
        """Must return early without any DB call when status is 'running'."""
        from frontend.job_routes import _maybe_persist_result

        capture = _FakeCapture(status="running")
        request = _make_request(pool=AsyncMock(), user={"user_id": "u1"})

        with patch(
            "backend.services.db_client.get_job_by_short_id", new_callable=AsyncMock
        ) as mock_get:
            await _maybe_persist_result(request, "job001", capture)
            mock_get.assert_not_called()

    @pytest.mark.asyncio
    async def test_does_nothing_when_status_is_error(self):
        """Must return early without any DB call when status is 'error'."""
        from frontend.job_routes import _maybe_persist_result

        capture = _FakeCapture(status="error")
        request = _make_request(pool=AsyncMock(), user={"user_id": "u1"})

        with patch(
            "backend.services.db_client.get_job_by_short_id", new_callable=AsyncMock
        ) as mock_get:
            await _maybe_persist_result(request, "job001", capture)
            mock_get.assert_not_called()

    @pytest.mark.asyncio
    async def test_does_nothing_when_status_is_cancelled(self):
        """Must return early without any DB call when status is 'cancelled'."""
        from frontend.job_routes import _maybe_persist_result

        capture = _FakeCapture(status="cancelled")
        request = _make_request(pool=AsyncMock(), user={"user_id": "u1"})

        with patch(
            "backend.services.db_client.get_job_by_short_id", new_callable=AsyncMock
        ) as mock_get:
            await _maybe_persist_result(request, "job001", capture)
            mock_get.assert_not_called()


class TestMaybePersistResultAlreadyPersistedGuard:

    @pytest.mark.asyncio
    async def test_does_nothing_when_already_persisted(self):
        """Must return early without any DB call when _db_persisted is True."""
        from frontend.job_routes import _maybe_persist_result

        capture = _FakeCapture(status="complete", db_persisted=True)
        request = _make_request(pool=AsyncMock(), user={"user_id": "u1"})

        with patch(
            "backend.services.db_client.get_job_by_short_id", new_callable=AsyncMock
        ) as mock_get:
            await _maybe_persist_result(request, "job001", capture)
            mock_get.assert_not_called()

    @pytest.mark.asyncio
    async def test_db_persisted_flag_prevents_double_write(self):
        """Calling twice for the same completed job must only write to DB once."""
        from frontend.job_routes import _maybe_persist_result

        capture = _FakeCapture(status="complete", db_persisted=False)
        pool = AsyncMock()
        user = {"id": "u1", "user_id": "u1"}
        request = _make_request(pool=pool, user=user)

        fake_job = {"id": "job-uuid-123"}

        with (
            patch(
                "backend.services.db_client.get_job_by_short_id", new_callable=AsyncMock
            ) as mock_get,
            patch(
                "backend.services.db_client.update_job_result", new_callable=AsyncMock
            ) as mock_update,
        ):
            mock_get.return_value = fake_job

            # First call — should persist
            await _maybe_persist_result(request, "job001", capture)
            # Second call — _db_persisted is now True, should skip
            await _maybe_persist_result(request, "job001", capture)

        assert mock_update.call_count == 1


# ---------------------------------------------------------------------------
# Guard: no pool or no user
# ---------------------------------------------------------------------------


class TestMaybePersistResultPoolUserGuard:

    @pytest.mark.asyncio
    async def test_does_nothing_when_no_db_pool(self):
        """Must return early when the app has no DB pool configured."""
        from frontend.job_routes import _maybe_persist_result

        capture = _FakeCapture(status="complete")
        # No pool — app_state has no db_pool attribute
        request = _make_request(pool=None, user={"user_id": "u1"})

        with patch(
            "backend.services.db_client.get_job_by_short_id", new_callable=AsyncMock
        ) as mock_get:
            await _maybe_persist_result(request, "job001", capture)
            mock_get.assert_not_called()

    @pytest.mark.asyncio
    async def test_does_nothing_when_no_authenticated_user(self):
        """Must return early when request.state.user is None (unauthenticated)."""
        from frontend.job_routes import _maybe_persist_result

        capture = _FakeCapture(status="complete")
        request = _make_request(pool=AsyncMock(), user=None)

        with patch(
            "backend.services.db_client.get_job_by_short_id", new_callable=AsyncMock
        ) as mock_get:
            await _maybe_persist_result(request, "job001", capture)
            mock_get.assert_not_called()

    @pytest.mark.asyncio
    async def test_does_nothing_when_job_not_found_in_db(self):
        """Must return early without calling update_job_result when job is not in DB."""
        from frontend.job_routes import _maybe_persist_result

        capture = _FakeCapture(status="complete")
        pool = AsyncMock()
        user = {"id": "u1", "user_id": "u1"}
        request = _make_request(pool=pool, user=user)

        with (
            patch(
                "backend.services.db_client.get_job_by_short_id", new_callable=AsyncMock
            ) as mock_get,
            patch(
                "backend.services.db_client.update_job_result", new_callable=AsyncMock
            ) as mock_update,
        ):
            mock_get.return_value = None  # job not found in DB

            await _maybe_persist_result(request, "job001", capture)

        mock_update.assert_not_called()


# ---------------------------------------------------------------------------
# Happy path: persists when all conditions are met
# ---------------------------------------------------------------------------


class TestMaybePersistResultHappyPath:

    @pytest.mark.asyncio
    async def test_calls_update_job_result_on_first_completion(self):
        """Must call update_job_result when status=complete, pool+user present, not persisted."""
        from frontend.job_routes import _maybe_persist_result

        capture = _FakeCapture(
            status="complete",
            db_persisted=False,
            result={
                "result_meta": {"files": 2},
                "topics": [{"name": "Transformers"}],
                "gap_summary": [{"concept": "deployment"}],
                "modules_md": ["# Module 1"],
                "curriculum_scope": "NLP",
            },
        )
        pool = AsyncMock()
        user = {"id": "u1", "user_id": "u1"}
        request = _make_request(pool=pool, user=user)

        fake_job = {"id": "job-uuid-456"}

        with (
            patch(
                "backend.services.db_client.get_job_by_short_id", new_callable=AsyncMock
            ) as mock_get,
            patch(
                "backend.services.db_client.update_job_result", new_callable=AsyncMock
            ) as mock_update,
        ):
            mock_get.return_value = fake_job

            await _maybe_persist_result(request, "job001", capture)

        mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_sets_db_persisted_flag_after_persist(self):
        """After persisting, capture._db_persisted must be True."""
        from frontend.job_routes import _maybe_persist_result

        capture = _FakeCapture(status="complete", db_persisted=False)
        pool = AsyncMock()
        user = {"id": "u1", "user_id": "u1"}
        request = _make_request(pool=pool, user=user)

        fake_job = {"id": "job-uuid-789"}

        with (
            patch(
                "backend.services.db_client.get_job_by_short_id", new_callable=AsyncMock
            ) as mock_get,
            patch("backend.services.db_client.update_job_result", new_callable=AsyncMock),
        ):
            mock_get.return_value = fake_job
            await _maybe_persist_result(request, "job001", capture)

        assert capture._db_persisted is True

    @pytest.mark.asyncio
    async def test_passes_pipeline_data_to_update_job_result(self):
        """update_job_result must receive a pipeline_data kwarg containing topics + gap_summary."""
        from frontend.job_routes import _maybe_persist_result

        topics = [{"name": "Transformers"}]
        gap_summary = [{"concept": "fine-tuning", "topic": "Transformers"}]
        modules_md = ["# Module content"]
        curriculum_scope = "NLP"

        capture = _FakeCapture(
            status="complete",
            db_persisted=False,
            result={
                "topics": topics,
                "gap_summary": gap_summary,
                "modules_md": modules_md,
                "curriculum_scope": curriculum_scope,
            },
        )
        pool = AsyncMock()
        user = {"id": "u1", "user_id": "u1"}
        request = _make_request(pool=pool, user=user)

        fake_job = {"id": "job-uuid-999"}

        with (
            patch(
                "backend.services.db_client.get_job_by_short_id", new_callable=AsyncMock
            ) as mock_get,
            patch(
                "backend.services.db_client.update_job_result", new_callable=AsyncMock
            ) as mock_update,
        ):
            mock_get.return_value = fake_job
            await _maybe_persist_result(request, "job001", capture)

        _, kwargs = mock_update.call_args
        pd = kwargs.get("pipeline_data", {})
        assert pd.get("topics") == topics
        assert pd.get("gap_summary") == gap_summary
        assert pd.get("modules_md") == modules_md
        assert pd.get("curriculum_scope") == curriculum_scope

    @pytest.mark.asyncio
    async def test_passes_status_complete_to_update_job_result(self):
        """update_job_result must be called with status='complete'."""
        from frontend.job_routes import _maybe_persist_result

        capture = _FakeCapture(status="complete", db_persisted=False)
        pool = AsyncMock()
        user = {"id": "u1", "user_id": "u1"}
        request = _make_request(pool=pool, user=user)

        fake_job = {"id": "job-uuid-abc"}

        with (
            patch(
                "backend.services.db_client.get_job_by_short_id", new_callable=AsyncMock
            ) as mock_get,
            patch(
                "backend.services.db_client.update_job_result", new_callable=AsyncMock
            ) as mock_update,
        ):
            mock_get.return_value = fake_job
            await _maybe_persist_result(request, "job001", capture)

        positional_args = mock_update.call_args[0]
        assert positional_args[2] == "complete"
