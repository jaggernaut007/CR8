"""LangGraph workflow for on-demand quiz generation.

Builds a standalone quiz graph separate from the main pipeline.
Triggered via POST /api/quiz/generate after a pipeline job completes.
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import StateGraph, START, END

from backend.pipeline.quiz_state import QuizState
from backend.pipeline.agent_quiz import quiz_generate_node

logger = logging.getLogger(__name__)


def build_quiz_graph() -> Any:
    """Build and compile the quiz generation LangGraph workflow.

    Single-node graph for now. Future extensions may add
    validation or difficulty-calibration nodes.

    Returns:
        A compiled LangGraph ``CompiledGraph`` ready to be invoked
        with a ``QuizState`` dict.
    """
    graph = StateGraph(QuizState)

    graph.add_node("generate_questions", quiz_generate_node)

    graph.add_edge(START, "generate_questions")
    graph.add_edge("generate_questions", END)

    compiled = graph.compile()
    logger.info("Quiz graph compiled: START → generate_questions → END")
    return compiled
