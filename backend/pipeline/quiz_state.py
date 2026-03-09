"""Quiz agent state definition for the CR8 on-demand quiz workflow.

Defines the :class:`QuizState` TypedDict used by the standalone
quiz generation LangGraph graph (separate from the main pipeline).
"""

from typing import NotRequired, TypedDict


class QuizState(TypedDict):
    """State dict for the quiz generation workflow.

    Input fields are populated from a completed pipeline job's
    database record. Output fields are written by the quiz agent.

    Attributes:
        job_id: ID of the completed pipeline job.
        user_id: ID of the user requesting quiz generation.
        topics: Topic dicts from the pipeline (name, description, etc.).
        modules_md: Raw markdown for each generated learning module.
        gap_summary: Per-topic gap analysis from the Research agent.
        curriculum_scope: Domain boundary description.
        question_count: Total number of questions to generate (default 20).
        questions: Output — validated question dicts ready for DB storage.
    """

    # Input (from completed job)
    job_id: str
    user_id: str
    topics: list[dict]
    modules_md: list[str]
    gap_summary: list[dict]
    curriculum_scope: str

    # Config
    question_count: NotRequired[int]

    # Output
    questions: NotRequired[list[dict]]
