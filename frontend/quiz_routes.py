"""Quiz routes for CR8 — generate, fetch, submit, and review quizzes.

All endpoints require JWT authentication. Quiz generation invokes the
standalone quiz LangGraph workflow on completed pipeline job data.
"""

import asyncio
import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from frontend.quiz_models import GenerateQuizRequest, SubmitQuizRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/quiz", tags=["quiz"])


# --- Helpers ---------------------------------------------------------------


def _get_user_and_pool(request: Request):
    """Extract authenticated user and DB pool from request.

    Args:
        request: FastAPI request object.

    Returns:
        Tuple of (user_dict, db_pool) or (None, error_response).
    """
    user = getattr(request.state, "user", None)
    if not user:
        return None, JSONResponse({"error": "Authentication required"}, status_code=401)

    pool = getattr(request.app.state, "db_pool", None)
    if not pool:
        return None, JSONResponse({"error": "Database unavailable"}, status_code=503)

    return (user, pool), None


def _strip_answers(questions: list[dict]) -> list[dict]:
    """Remove answer-revealing fields from questions before attempt completion.

    Args:
        questions: List of question dicts from DB.

    Returns:
        Questions with correct_index, feedback_correct, feedback_incorrect removed.
    """
    hidden = {"correct_index", "feedback_correct", "feedback_incorrect"}
    return [{k: v for k, v in q.items() if k not in hidden} for q in questions]


def _serialize_questions(questions: list[dict]) -> list[dict]:
    """Convert DB question rows to JSON-safe dicts.

    Args:
        questions: Raw question dicts from asyncpg with UUID ids.

    Returns:
        Questions with string ids and parsed options.
    """
    result = []
    for q in questions:
        sq = {k: (str(v) if hasattr(v, "hex") else v) for k, v in q.items()}
        if isinstance(sq.get("options"), str):
            sq["options"] = json.loads(sq["options"])
        result.append(sq)
    return result


# --- Generate quiz endpoint ------------------------------------------------


@router.post("/generate")
async def generate_quiz(request: Request):
    """Generate a quiz from a completed pipeline job."""
    auth, err = _get_user_and_pool(request)
    if err:
        return err
    user, pool = auth

    try:
        body = await request.json()
        req = GenerateQuizRequest(**body)
    except Exception:
        return JSONResponse({"error": "Invalid request body"}, status_code=422)

    job, job_err = await _validate_job_for_quiz(pool, req.job_id, user)
    if job_err:
        return job_err

    return await _run_quiz_generation(req, user, pool, job, job.get("topics", []))


async def _validate_job_for_quiz(pool, job_id: str, user: dict):
    """Validate that a job exists, belongs to user, is complete, and has topics.

    Args:
        pool: DB connection pool.
        job_id: Job ID to validate.
        user: Authenticated user dict.

    Returns:
        Tuple of (job_dict, None) on success or (None, JSONResponse) on error.
    """
    from backend.services.db_client import get_job_by_short_id

    job = await get_job_by_short_id(pool, job_id)
    if not job or str(job.get("user_id", "")) != str(user.get("user_id", "")):
        return None, JSONResponse({"error": "Job not found"}, status_code=404)

    if job.get("status") != "complete":
        return None, JSONResponse(
            {"error": "Job must be complete before generating a quiz"},
            status_code=400,
        )

    topics = job.get("topics") or []
    if isinstance(topics, str):
        topics = json.loads(topics)
        job["topics"] = topics
    if not topics:
        return None, JSONResponse(
            {"error": "Job has no topic data for quiz generation"},
            status_code=400,
        )

    return job, None


async def _run_quiz_generation(req, user, pool, job, topics):
    """Invoke quiz graph and persist results.

    Args:
        req: Validated GenerateQuizRequest.
        user: Authenticated user dict.
        pool: DB connection pool.
        job: Job dict from DB.
        topics: Topic list from job.

    Returns:
        JSONResponse with quiz_id and question_count.
    """
    # DB JSONB columns may come back as strings if stored via json.dumps()
    gap_summary = job.get("gap_summary") or []
    if isinstance(gap_summary, str):
        gap_summary = json.loads(gap_summary)
    modules_md = job.get("modules_md") or []
    if isinstance(modules_md, str):
        modules_md = json.loads(modules_md)
    curriculum_scope = job.get("curriculum_scope", "General")

    logger.info("Generating quiz: job_id=%s, questions=%d", req.job_id, req.question_count)

    from backend.pipeline.quiz_graph import build_quiz_graph

    graph = build_quiz_graph()
    graph_input = {
        "job_id": req.job_id,
        "user_id": str(user["user_id"]),
        "topics": topics,
        "modules_md": modules_md,
        "gap_summary": gap_summary,
        "curriculum_scope": curriculum_scope,
        "question_count": req.question_count,
    }
    # Run synchronous LLM graph in a thread to avoid blocking the event loop
    # and causing DB connection timeouts on Neon serverless
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, graph.invoke, graph_input)

    questions = result.get("questions", [])

    from backend.services.db_client import create_quiz_with_user, create_quiz_questions

    title = f"Quiz: {job.get('file_names', ['Untitled'])[0]}"
    # Use the full UUID from the job row, not the short_id from the request
    full_job_id = str(job["id"])
    quiz = await create_quiz_with_user(pool, full_job_id, str(user["user_id"]), title)
    quiz_id = str(quiz["id"])

    await create_quiz_questions(pool, quiz_id, questions)

    return JSONResponse(
        {"quiz_id": quiz_id, "question_count": len(questions)},
        status_code=201,
    )


# --- Fetch quiz endpoint ---------------------------------------------------


@router.get("/{quiz_id}")
async def get_quiz(quiz_id: str, request: Request):
    """Fetch a quiz with questions. Hides answers until attempt is completed."""
    auth, err = _get_user_and_pool(request)
    if err:
        return err
    user, pool = auth

    from backend.services.db_client import (
        get_quiz_by_id, get_quiz_questions, get_quiz_attempt,
    )

    quiz = await get_quiz_by_id(pool, quiz_id)
    if not quiz or str(quiz.get("user_id", "")) != str(user.get("user_id", "")):
        return JSONResponse({"error": "Quiz not found"}, status_code=404)

    questions = _serialize_questions(await get_quiz_questions(pool, quiz_id))
    attempt = await get_quiz_attempt(pool, quiz_id, str(user["user_id"]))

    has_completed = attempt and attempt.get("completed_at") is not None
    if not has_completed:
        questions = _strip_answers(questions)

    return JSONResponse({
        "quiz_id": str(quiz["id"]),
        "title": quiz.get("title", ""),
        "questions": questions,
        "existing_attempt": _serialize_attempt(attempt) if attempt else None,
    })


# --- Submit quiz endpoint --------------------------------------------------


@router.post("/{quiz_id}/submit")
async def submit_quiz(quiz_id: str, request: Request):
    """Submit quiz answers and get scored results."""
    auth, err = _get_user_and_pool(request)
    if err:
        return err
    user, pool = auth

    try:
        body = await request.json()
        req = SubmitQuizRequest(**body)
    except Exception:
        return JSONResponse({"error": "Invalid request body"}, status_code=422)

    from backend.services.db_client import (
        get_quiz_by_id, get_quiz_questions, get_quiz_attempt,
        create_quiz_attempt, complete_quiz_attempt, create_quiz_responses,
    )

    quiz = await get_quiz_by_id(pool, quiz_id)
    if not quiz or str(quiz.get("user_id", "")) != str(user.get("user_id", "")):
        return JSONResponse({"error": "Quiz not found"}, status_code=404)

    user_id = str(user["user_id"])
    existing = await get_quiz_attempt(pool, quiz_id, user_id)
    if existing and existing.get("completed_at"):
        return JSONResponse({"error": "Quiz already submitted"}, status_code=409)

    questions = _serialize_questions(await get_quiz_questions(pool, quiz_id))
    q_map = {q["id"]: q for q in questions}

    responses, correct_count = _score_responses(req.responses, q_map)

    total = len(questions)
    score = (correct_count / total * 100) if total > 0 else 0

    attempt = existing or await create_quiz_attempt(pool, quiz_id, user_id)
    attempt_id = str(attempt["id"])

    await create_quiz_responses(pool, attempt_id, responses)
    await complete_quiz_attempt(pool, attempt_id, score, total)

    results = _build_results(responses, q_map)

    return JSONResponse({
        "attempt_id": attempt_id,
        "score": score,
        "total": total,
        "results": results,
    })


# --- Quiz results endpoint -------------------------------------------------


@router.get("/{quiz_id}/results")
async def get_quiz_results(quiz_id: str, request: Request):
    """Get scored results for a completed quiz attempt."""
    auth, err = _get_user_and_pool(request)
    if err:
        return err
    user, pool = auth

    from backend.services.db_client import (
        get_quiz_by_id, get_quiz_questions, get_quiz_attempt,
    )

    quiz = await get_quiz_by_id(pool, quiz_id)
    if not quiz or str(quiz.get("user_id", "")) != str(user.get("user_id", "")):
        return JSONResponse({"error": "Quiz not found"}, status_code=404)

    attempt = await get_quiz_attempt(pool, quiz_id, str(user["user_id"]))
    if not attempt or not attempt.get("completed_at"):
        return JSONResponse({"error": "No completed attempt found"}, status_code=404)

    questions = _serialize_questions(await get_quiz_questions(pool, quiz_id))

    return JSONResponse({
        "score": float(attempt.get("score", 0)),
        "total": attempt.get("total_questions", 0),
        "percentage": float(attempt.get("score", 0)),
        "per_question_results": _build_per_question_results(questions),
    })


# --- Quizzes by job endpoint -----------------------------------------------


@router.get("/by-job/{job_id}")
async def quizzes_by_job(job_id: str, request: Request):
    """List all quizzes generated for a specific job."""
    auth, err = _get_user_and_pool(request)
    if err:
        return err
    user, pool = auth

    from backend.services.db_client import get_job_by_short_id, get_quizzes_for_job

    job = await get_job_by_short_id(pool, job_id)
    if not job or str(job.get("user_id", "")) != str(user.get("user_id", "")):
        return JSONResponse({"error": "Job not found"}, status_code=404)

    quizzes = await get_quizzes_for_job(pool, str(job["id"]))

    return JSONResponse({
        "quizzes": [
            {
                "id": str(q["id"]),
                "title": q.get("title", ""),
                "created_at": str(q.get("created_at", "")),
            }
            for q in quizzes
        ],
    })


# --- Internal helpers ------------------------------------------------------


def _serialize_attempt(attempt: dict) -> dict:
    """Convert attempt dict to JSON-safe format.

    Args:
        attempt: Attempt dict from DB.

    Returns:
        Serializable dict.
    """
    score = attempt.get("score")
    return {
        "id": str(attempt["id"]),
        "score": float(score) if score is not None else None,
        "total_questions": attempt.get("total_questions"),
        "completed_at": str(attempt["completed_at"]) if attempt.get("completed_at") else None,
    }


def _score_responses(responses, q_map):
    """Score submitted responses against correct answers.

    Args:
        responses: List of AnswerItem from the request.
        q_map: Dict mapping question_id to question dict.

    Returns:
        Tuple of (response_dicts_for_db, correct_count).
    """
    scored = []
    correct_count = 0
    for ans in responses:
        question = q_map.get(ans.question_id)
        if not question:
            continue
        correct_idx = question.get("correct_index", -1)
        is_correct = ans.selected_index == correct_idx
        if is_correct:
            correct_count += 1
        scored.append({
            "question_id": ans.question_id,
            "selected_index": ans.selected_index,
            "is_correct": is_correct,
            "time_spent_seconds": ans.time_spent_seconds,
        })
    return scored, correct_count


def _build_results(responses, q_map):
    """Build per-question result dicts for the submit response.

    Args:
        responses: Scored response dicts.
        q_map: Dict mapping question_id to question dict.

    Returns:
        List of result dicts with feedback.
    """
    results = []
    for r in responses:
        question = q_map.get(r["question_id"], {})
        feedback = (
            question.get("feedback_correct", "")
            if r["is_correct"]
            else question.get("feedback_incorrect", "")
        )
        results.append({
            "question_id": r["question_id"],
            "selected_index": r["selected_index"],
            "correct_index": question.get("correct_index"),
            "is_correct": r["is_correct"],
            "feedback": feedback,
        })
    return results


def _build_per_question_results(questions):
    """Build per-question detail dicts for the results endpoint.

    Args:
        questions: Question dicts from DB with all fields.

    Returns:
        List of question detail dicts.
    """
    return [
        {
            "question_id": str(q["id"]),
            "question_text": q.get("question_text", ""),
            "options": q.get("options", []),
            "correct_index": q.get("correct_index"),
            "difficulty": q.get("difficulty"),
            "blooms_level": q.get("blooms_level"),
            "feedback_correct": q.get("feedback_correct", ""),
            "feedback_incorrect": q.get("feedback_incorrect", ""),
        }
        for q in questions
    ]
