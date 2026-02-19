from langgraph.graph import StateGraph, START, END

from backend.pipeline.state import PipelineState
from backend.pipeline.agent_ingest import ingest_node
from backend.pipeline.agent_research import research_node
from backend.pipeline.agent_generate import generate_node


def build_pipeline():
    """Build the 3-agent LangGraph pipeline: ingest -> research -> generate."""
    graph = StateGraph(PipelineState)

    graph.add_node("ingest", ingest_node)
    graph.add_node("research", research_node)
    graph.add_node("generate", generate_node)

    graph.add_edge(START, "ingest")
    graph.add_edge("ingest", "research")
    graph.add_edge("research", "generate")
    graph.add_edge("generate", END)

    return graph.compile()
