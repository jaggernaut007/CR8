"""Quiz routes for CR8 — stub for Phase 4.

All endpoints return 501 Not Implemented until the quiz feature is built.
"""

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/quiz", tags=["quiz"])

_NOT_IMPLEMENTED = {"error": "Quiz feature not yet implemented"}


@router.get("/")
async def list_quizzes():
    """List quizzes — not yet implemented."""
    return JSONResponse(_NOT_IMPLEMENTED, status_code=501)


@router.get("/{quiz_id}")
async def get_quiz(quiz_id: str):
    """Get a quiz — not yet implemented."""
    return JSONResponse(_NOT_IMPLEMENTED, status_code=501)


@router.post("/{quiz_id}/start")
async def start_quiz(quiz_id: str):
    """Start a quiz attempt — not yet implemented."""
    return JSONResponse(_NOT_IMPLEMENTED, status_code=501)


@router.post("/{quiz_id}/submit")
async def submit_quiz(quiz_id: str):
    """Submit quiz answers — not yet implemented."""
    return JSONResponse(_NOT_IMPLEMENTED, status_code=501)
