"""LangGraph pipeline builder for the CR8 3-agent workflow.

Constructs and compiles a :class:`~langgraph.graph.StateGraph` with
three sequential nodes: **Ingest** -> **Research** -> **Generate**.
"""

from __future__ import annotations

import logging
from typing import Any

from langgraph.graph import StateGraph, START, END

from backend.pipeline.state import PipelineState
from backend.pipeline.agent_ingest import ingest_node
from backend.pipeline.agent_research import research_node
from backend.pipeline.agent_generate import generate_node

logger = logging.getLogger(__name__)


def build_pipeline() -> Any:
    """Build and compile the 3-agent LangGraph pipeline.

    The pipeline flows linearly:

    1. **ingest** -- parse files, extract topics, embed into ChromaDB.
    2. **research** -- web-search each topic, perform gap analysis.
    3. **generate** -- produce PDF, PPT, scripts, and/or videos.

    Returns:
        A compiled LangGraph ``CompiledGraph`` ready to be invoked with a ``PipelineState`` dict.
    """
    graph = StateGraph(PipelineState)

    graph.add_node("ingest", ingest_node)
    graph.add_node("research", research_node)
    graph.add_node("generate", generate_node)

    graph.add_edge(START, "ingest")
    graph.add_edge("ingest", "research")
    graph.add_edge("research", "generate")
    graph.add_edge("generate", END)

    compiled = graph.compile()
    logger.info("Pipeline compiled: START → ingest → research → generate → END")
    return compiled
