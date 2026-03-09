"""Pydantic request/response models for quiz API routes.

Validates incoming quiz generation and submission payloads.
"""

from pydantic import BaseModel, Field


class GenerateQuizRequest(BaseModel):
    """Request body for POST /api/quiz/generate."""

    job_id: str = Field(..., min_length=1)
    question_count: int = Field(default=20, ge=5, le=50)


class AnswerItem(BaseModel):
    """A single answer in a quiz submission."""

    question_id: str
    selected_index: int = Field(..., ge=0, le=3)
    time_spent_seconds: int = Field(default=0, ge=0)


class SubmitQuizRequest(BaseModel):
    """Request body for POST /api/quiz/{quiz_id}/submit."""

    responses: list[AnswerItem]
