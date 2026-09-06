"""Thin async CRUD wrapper for CR8 PostgreSQL tables.

All functions take an ``asyncpg.Pool`` as the first argument and use
parameterized queries (``$1``, ``$2``, ...) for safety.  Results are
returned as plain dicts converted from asyncpg ``Record`` objects.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import asyncpg

logger = logging.getLogger(__name__)


def _sanitize_for_pg(val: Any) -> Any:
    """Sanitize a value for Postgres insertion.

    Strips null bytes (0x00) that Postgres rejects in TEXT/JSONB,
    strips leading/trailing whitespace, and normalizes control characters.
    Handles strings, lists, and dicts recursively.

    Args:
        val: Value to sanitize (str, list, dict, or passthrough).

    Returns:
        Sanitized value of the same type.
    """
    if isinstance(val, str):
        return val.replace("\x00", "").strip()
    if isinstance(val, list):
        return [_sanitize_for_pg(item) for item in val]
    if isinstance(val, dict):
        return {k: _sanitize_for_pg(v) for k, v in val.items()}
    return val


# ---------------------------------------------------------------------------
# User CRUD
# ---------------------------------------------------------------------------


async def create_user(
    pool: asyncpg.Pool,
    email: str,
    password_hash: str,
) -> dict[str, Any]:
    """Insert a new user and return the created row.

    Args:
        pool: asyncpg connection pool.
        email: User email (must be unique).
        password_hash: Bcrypt hash of the password.

    Returns:
        Dict with all columns of the new user row.
    """
    logger.info("Creating user: email=%s", email)
    row = await pool.fetchrow(
        "INSERT INTO users (email, password_hash) "
        "VALUES ($1, $2) RETURNING *",
        email,
        password_hash,
    )
    logger.info("User created: id=%s", row["id"])
    return dict(row)


async def get_user_by_email(
    pool: asyncpg.Pool,
    email: str,
) -> dict[str, Any] | None:
    """Fetch a single user by email address.

    Args:
        pool: asyncpg connection pool.
        email: Email to look up.

    Returns:
        User dict or None if not found.
    """
    logger.info("Looking up user by email: %s", email)
    row = await pool.fetchrow(
        "SELECT * FROM users WHERE email = $1",
        email,
    )
    if row is None:
        logger.info("No user found for email: %s", email)
        return None
    logger.info("Found user: id=%s", row["id"])
    return dict(row)


async def get_user_by_id(
    pool: asyncpg.Pool,
    user_id: str,
) -> dict[str, Any] | None:
    """Fetch a single user by primary key.

    Args:
        pool: asyncpg connection pool.
        user_id: UUID string of the user.

    Returns:
        User dict or None if not found.
    """
    logger.info("Looking up user by id: %s", user_id)
    row = await pool.fetchrow(
        "SELECT * FROM users WHERE id = $1",
        user_id,
    )
    if row is None:
        logger.info("No user found for id: %s", user_id)
        return None
    logger.info("Found user: id=%s", row["id"])
    return dict(row)


async def upsert_password_reset_token(
    pool: asyncpg.Pool,
    user_id: str,
    token_hash: str,
    expires_at: Any,
) -> None:
    """Replace any existing password-reset token for a user with a new one.

    At most one active reset token exists per user at a time; issuing a new
    token invalidates the previous one.

    Args:
        pool: asyncpg connection pool.
        user_id: UUID string of the user.
        token_hash: SHA-256 hex digest of the raw reset token.
        expires_at: Timezone-aware datetime when the token expires.
    """
    logger.info("Upserting password reset token for user_id=%s", user_id)
    await pool.execute(
        "DELETE FROM password_reset_tokens WHERE user_id = $1", user_id
    )
    await pool.execute(
        "INSERT INTO password_reset_tokens (user_id, token_hash, expires_at) "
        "VALUES ($1, $2, $3)",
        user_id,
        token_hash,
        expires_at,
    )
    logger.info("Password reset token stored for user_id=%s", user_id)


async def get_password_reset_token_by_hash(
    pool: asyncpg.Pool,
    token_hash: str,
) -> dict[str, Any] | None:
    """Fetch a password-reset token record by its SHA-256 hash.

    Args:
        pool: asyncpg connection pool.
        token_hash: SHA-256 hex digest of the raw reset token.

    Returns:
        Token record dict or None if not found.
    """
    logger.info("Looking up password reset token by hash")
    row = await pool.fetchrow(
        "SELECT * FROM password_reset_tokens WHERE token_hash = $1", token_hash
    )
    if row is None:
        logger.info("No password reset token found for hash")
        return None
    return dict(row)


async def delete_password_reset_tokens(pool: asyncpg.Pool, user_id: str) -> None:
    """Delete all password-reset tokens for a user (invalidates pending links).

    Args:
        pool: asyncpg connection pool.
        user_id: UUID string of the user.
    """
    logger.info("Deleting password reset tokens for user_id=%s", user_id)
    await pool.execute(
        "DELETE FROM password_reset_tokens WHERE user_id = $1", user_id
    )


async def update_user_password(
    pool: asyncpg.Pool,
    user_id: str,
    password_hash: str,
) -> None:
    """Update a user's password hash.

    Args:
        pool: asyncpg connection pool.
        user_id: UUID string of the user.
        password_hash: New bcrypt hash of the password.
    """
    logger.info("Updating password for user_id=%s", user_id)
    await pool.execute(
        "UPDATE users SET password_hash = $1, updated_at = now() WHERE id = $2",
        password_hash,
        user_id,
    )
    logger.info("Password updated for user_id=%s", user_id)


# ---------------------------------------------------------------------------
# Job CRUD
# ---------------------------------------------------------------------------


async def create_job(
    pool: asyncpg.Pool,
    user_id: str,
    short_id: str,
    file_names: list[str],
    output_formats: str,
) -> dict[str, Any]:
    """Insert a new pipeline job and return the created row.

    Args:
        pool: asyncpg connection pool.
        user_id: UUID of the owning user.
        short_id: 8-char hex identifier for URLs.
        file_names: List of uploaded file names.
        output_formats: Comma-separated output formats string.

    Returns:
        Dict with all columns of the new job row.
    """
    logger.info("Creating job: user_id=%s, short_id=%s", user_id, short_id)
    row = await pool.fetchrow(
        "INSERT INTO jobs (user_id, short_id, file_names, output_formats) "
        "VALUES ($1, $2, $3, $4) RETURNING *",
        user_id,
        short_id,
        file_names,
        output_formats,
    )
    logger.info("Job created: id=%s, short_id=%s", row["id"], short_id)
    return dict(row)


async def update_job_progress(
    pool: asyncpg.Pool,
    job_id: str,
    progress_pct: int,
    current_stage: str,
) -> None:
    """Update the progress percentage and current stage of a job.

    Args:
        pool: asyncpg connection pool.
        job_id: UUID of the job.
        progress_pct: Progress percentage (0-100).
        current_stage: Human-readable stage name.
    """
    logger.info(
        "Updating job progress: job_id=%s, pct=%d, stage=%s",
        job_id,
        progress_pct,
        current_stage,
    )
    await pool.execute(
        "UPDATE jobs SET progress_pct = $1, current_stage = $2, "
        "updated_at = now() WHERE id = $3",
        progress_pct,
        current_stage,
        job_id,
    )
    logger.info("Job progress updated: job_id=%s", job_id)


async def update_job_result(
    pool: asyncpg.Pool,
    job_id: str,
    status: str,
    result_meta: dict[str, Any] | None,
    pipeline_data: dict[str, Any] | None = None,
) -> None:
    """Update the final status, result metadata, and pipeline data of a job.

    Args:
        pool: asyncpg connection pool.
        job_id: UUID of the job.
        status: Final status (complete, error, cancelled).
        result_meta: JSON-serializable metadata dict or None.
        pipeline_data: Optional dict with keys topics, gap_summary,
            modules_md, curriculum_scope to persist from pipeline output.
    """
    logger.info("Updating job result: job_id=%s, status=%s", job_id, status)
    pd = pipeline_data or {}
    topics = pd.get("topics")
    gap_summary = pd.get("gap_summary")
    modules_md = pd.get("modules_md")
    curriculum_scope = pd.get("curriculum_scope")
    await pool.execute(
        "UPDATE jobs SET status = $1, result_meta = $2, "
        "topics = $3, gap_summary = $4, modules_md = $5, "
        "curriculum_scope = $6, "
        "progress_pct = 100, updated_at = now(), completed_at = now() "
        "WHERE id = $7",
        status,
        (
            json.dumps(result_meta)
            if result_meta and isinstance(result_meta, (dict, list))
            else result_meta
        ),
        (
            json.dumps(topics)
            if topics and isinstance(topics, (list, dict))
            else topics
        ),
        (
            json.dumps(gap_summary)
            if gap_summary and isinstance(gap_summary, (list, dict))
            else gap_summary
        ),
        (
            json.dumps(modules_md)
            if modules_md and isinstance(modules_md, (list, dict))
            else modules_md
        ),
        curriculum_scope,
        job_id,
    )
    logger.info("Job result updated: job_id=%s", job_id)


async def get_job(
    pool: asyncpg.Pool,
    job_id: str,
) -> dict[str, Any] | None:
    """Fetch a single job by primary key.

    Args:
        pool: asyncpg connection pool.
        job_id: UUID string of the job.

    Returns:
        Job dict or None if not found.
    """
    logger.info("Fetching job: id=%s", job_id)
    row = await pool.fetchrow(
        "SELECT * FROM jobs WHERE id = $1",
        job_id,
    )
    if row is None:
        logger.info("No job found: id=%s", job_id)
        return None
    logger.info("Found job: id=%s, status=%s", row["id"], row["status"])
    return dict(row)


async def get_job_by_short_id(
    pool: asyncpg.Pool,
    short_id: str,
) -> dict[str, Any] | None:
    """Fetch a single job by its short URL identifier.

    Args:
        pool: asyncpg connection pool.
        short_id: 8-char hex identifier.

    Returns:
        Job dict or None if not found.
    """
    logger.info("Fetching job by short_id: %s", short_id)
    row = await pool.fetchrow(
        "SELECT * FROM jobs WHERE short_id = $1",
        short_id,
    )
    if row is None:
        logger.info("No job found for short_id: %s", short_id)
        return None
    logger.info("Found job: id=%s, short_id=%s", row["id"], short_id)
    return dict(row)


async def list_jobs(
    pool: asyncpg.Pool,
    user_id: str,
    limit: int = 20,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """List jobs for a user, newest first.

    Args:
        pool: asyncpg connection pool.
        user_id: UUID of the owning user.
        limit: Maximum number of rows to return.
        offset: Number of rows to skip for pagination.

    Returns:
        List of job dicts ordered by created_at descending.
    """
    logger.info("Listing jobs: user_id=%s, limit=%d, offset=%d", user_id, limit, offset)
    rows = await pool.fetch(
        "SELECT * FROM jobs WHERE user_id = $1 "
        "ORDER BY created_at DESC LIMIT $2 OFFSET $3",
        user_id,
        limit,
        offset,
    )
    logger.info("Listed %d jobs for user_id=%s", len(rows), user_id)
    return [dict(r) for r in rows]


async def mark_stale_jobs_as_error(pool: asyncpg.Pool) -> int:
    """Mark running jobs older than 1 hour as error.

    Args:
        pool: asyncpg connection pool.

    Returns:
        Number of jobs marked as error.
    """
    logger.info("Marking stale running jobs as error")
    result = await pool.execute(
        "UPDATE jobs SET status = 'error', "
        "error_message = 'Job timed out after 1 hour', "
        "updated_at = now() "
        "WHERE status = 'running' "
        "AND created_at < now() - INTERVAL '1 hour'"
    )
    # asyncpg execute returns a status string like "UPDATE 3"
    count = int(result.split()[-1])
    logger.info("Marked %d stale jobs as error", count)
    return count


# ---------------------------------------------------------------------------
# Quiz CRUD
# ---------------------------------------------------------------------------


async def create_quiz(
    pool: asyncpg.Pool,
    job_id: str,
    title: str,
) -> dict[str, Any]:
    """Insert a new quiz linked to a pipeline job.

    Args:
        pool: asyncpg connection pool.
        job_id: UUID of the parent job.
        title: Quiz title.

    Returns:
        Dict with all columns of the new quiz row.
    """
    logger.info("Creating quiz: job_id=%s, title=%s", job_id, title)
    row = await pool.fetchrow(
        "INSERT INTO quizzes (job_id, title) "
        "VALUES ($1, $2) RETURNING *",
        job_id,
        title,
    )
    logger.info("Quiz created: id=%s", row["id"])
    return dict(row)


async def create_quiz_with_user(
    pool: asyncpg.Pool,
    job_id: str,
    user_id: str,
    title: str,
) -> dict[str, Any]:
    """Insert a new quiz linked to a job and user.

    Args:
        pool: asyncpg connection pool.
        job_id: ID of the parent job.
        user_id: UUID of the quiz creator.
        title: Quiz title.

    Returns:
        Dict with all columns of the new quiz row.
    """
    logger.info("Creating quiz: job_id=%s, user_id=%s, title=%s", job_id, user_id, title)
    row = await pool.fetchrow(
        "INSERT INTO quizzes (job_id, user_id, title) "
        "VALUES ($1, $2, $3) RETURNING *",
        job_id,
        user_id,
        title,
    )
    logger.info("Quiz created: id=%s", row["id"])
    return dict(row)


async def create_quiz_questions(
    pool: asyncpg.Pool,
    quiz_id: str,
    questions: list[dict[str, Any]],
) -> int:
    """Bulk-insert quiz questions for a quiz.

    Args:
        pool: asyncpg connection pool.
        quiz_id: UUID of the parent quiz.
        questions: List of question dicts with fields matching quiz_questions table.

    Returns:
        Number of questions inserted.
    """
    logger.info("Inserting %d questions for quiz: %s", len(questions), quiz_id)
    count = 0
    for q in questions:
        sq = _sanitize_for_pg(q)
        options = sq["options"]
        options_json = json.dumps(options) if isinstance(options, list) else options
        await pool.execute(
            "INSERT INTO quiz_questions "
            "(quiz_id, question_text, question_type, options, correct_index, "
            "difficulty, blooms_level, source_section, feedback_correct, "
            "feedback_incorrect, topic, sort_order) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)",
            quiz_id,
            sq["question_text"],
            sq.get("question_type", "mcq"),
            options_json,
            sq["correct_index"],
            sq.get("difficulty", "medium"),
            sq.get("blooms_level"),
            sq.get("source_section"),
            sq.get("feedback_correct"),
            sq.get("feedback_incorrect"),
            sq.get("topic"),
            sq.get("sort_order", 0),
        )
        count += 1
    logger.info("Inserted %d questions for quiz: %s", count, quiz_id)
    return count


async def get_quiz_by_id(
    pool: asyncpg.Pool,
    quiz_id: str,
) -> dict[str, Any] | None:
    """Fetch a single quiz by primary key.

    Args:
        pool: asyncpg connection pool.
        quiz_id: UUID of the quiz.

    Returns:
        Quiz dict or None if not found.
    """
    logger.info("Fetching quiz: id=%s", quiz_id)
    row = await pool.fetchrow(
        "SELECT * FROM quizzes WHERE id = $1",
        quiz_id,
    )
    if row is None:
        logger.info("No quiz found: id=%s", quiz_id)
        return None
    logger.info("Found quiz: id=%s", row["id"])
    return dict(row)


async def get_quiz_questions(
    pool: asyncpg.Pool,
    quiz_id: str,
) -> list[dict[str, Any]]:
    """Fetch all questions for a quiz, ordered by sort_order.

    Args:
        pool: asyncpg connection pool.
        quiz_id: UUID of the quiz.

    Returns:
        List of question dicts ordered by sort_order ascending.
    """
    logger.info("Fetching questions for quiz: %s", quiz_id)
    rows = await pool.fetch(
        "SELECT * FROM quiz_questions WHERE quiz_id = $1 ORDER BY sort_order",
        quiz_id,
    )
    logger.info("Found %d questions for quiz: %s", len(rows), quiz_id)
    return [dict(r) for r in rows]


async def get_quizzes_for_job(
    pool: asyncpg.Pool,
    job_id: str,
) -> list[dict[str, Any]]:
    """Fetch all quizzes for a given job.

    Args:
        pool: asyncpg connection pool.
        job_id: UUID of the parent job.

    Returns:
        List of quiz dicts ordered by created_at ascending.
    """
    logger.info("Fetching quizzes for job: %s", job_id)
    rows = await pool.fetch(
        "SELECT * FROM quizzes WHERE job_id = $1 ORDER BY created_at",
        job_id,
    )
    logger.info("Found %d quizzes for job: %s", len(rows), job_id)
    return [dict(r) for r in rows]


async def create_quiz_attempt(
    pool: asyncpg.Pool,
    quiz_id: str,
    user_id: str,
) -> dict[str, Any]:
    """Create a new quiz attempt for a user.

    Args:
        pool: asyncpg connection pool.
        quiz_id: UUID of the quiz.
        user_id: UUID of the user taking the quiz.

    Returns:
        Dict with all columns of the new attempt row.

    Raises:
        asyncpg.UniqueViolationError: If user already has an attempt for this quiz.
    """
    logger.info("Creating quiz attempt: quiz_id=%s, user_id=%s", quiz_id, user_id)
    row = await pool.fetchrow(
        "INSERT INTO quiz_attempts (quiz_id, user_id) "
        "VALUES ($1, $2) RETURNING *",
        quiz_id,
        user_id,
    )
    logger.info("Quiz attempt created: id=%s", row["id"])
    return dict(row)


async def get_quiz_attempt(
    pool: asyncpg.Pool,
    quiz_id: str,
    user_id: str,
) -> dict[str, Any] | None:
    """Fetch the attempt for a specific quiz and user.

    Args:
        pool: asyncpg connection pool.
        quiz_id: UUID of the quiz.
        user_id: UUID of the user.

    Returns:
        Attempt dict or None if no attempt exists.
    """
    logger.info("Fetching attempt: quiz_id=%s, user_id=%s", quiz_id, user_id)
    row = await pool.fetchrow(
        "SELECT * FROM quiz_attempts WHERE quiz_id = $1 AND user_id = $2",
        quiz_id,
        user_id,
    )
    if row is None:
        logger.info("No attempt found: quiz_id=%s, user_id=%s", quiz_id, user_id)
        return None
    logger.info("Found attempt: id=%s", row["id"])
    return dict(row)


async def complete_quiz_attempt(
    pool: asyncpg.Pool,
    attempt_id: str,
    score: float,
    total_questions: int,
) -> None:
    """Mark a quiz attempt as completed with a score.

    Args:
        pool: asyncpg connection pool.
        attempt_id: UUID of the attempt.
        score: Score as a percentage (0-100).
        total_questions: Total number of questions in the quiz.
    """
    logger.info(
        "Completing attempt: id=%s, score=%.1f, total=%d",
        attempt_id, score, total_questions,
    )
    await pool.execute(
        "UPDATE quiz_attempts SET score = $1, total_questions = $2, "
        "completed_at = now() WHERE id = $3",
        score,
        total_questions,
        attempt_id,
    )
    logger.info("Attempt completed: id=%s", attempt_id)


async def create_quiz_responses(
    pool: asyncpg.Pool,
    attempt_id: str,
    responses: list[dict[str, Any]],
) -> int:
    """Bulk-insert quiz responses for an attempt.

    Args:
        pool: asyncpg connection pool.
        attempt_id: UUID of the parent attempt.
        responses: List of response dicts with question_id, selected_index, is_correct.

    Returns:
        Number of responses inserted.
    """
    logger.info("Inserting %d responses for attempt: %s", len(responses), attempt_id)
    count = 0
    for r in responses:
        await pool.execute(
            "INSERT INTO quiz_responses "
            "(attempt_id, question_id, selected_index, is_correct, time_spent_seconds) "
            "VALUES ($1, $2, $3, $4, $5)",
            attempt_id,
            r["question_id"],
            r["selected_index"],
            r["is_correct"],
            r.get("time_spent_seconds", 0),
        )
        count += 1
    logger.info("Inserted %d responses for attempt: %s", count, attempt_id)
    return count
