"""Pipeline state definition for the CR8 3-agent LangGraph pipeline.

Defines the :class:`PipelineState` TypedDict that flows through the
Ingest -> Research -> Generate pipeline graph.
"""

from typing import TypedDict


class PipelineState(TypedDict):
    """Shared state dict passed between pipeline agents.

    Each agent reads the fields populated by prior stages and writes
    its own output fields.  The TypedDict is used by LangGraph's
    ``StateGraph`` to validate inter-node data flow.

    Attributes:
        job_id: Unique identifier for this pipeline run.
        file_paths: Absolute paths to uploaded curriculum files (PDF/PPTX).
        topics: Extracted topic dicts with name, description, key_techniques,
            and domain_context.  Populated by the Ingest agent.
        raw_text: Concatenated extracted text from all input files.
        curriculum_scope: One-sentence description of the curriculum's
            domain boundaries, used to ground research queries.
        gap_summary: Per-topic gap analysis results with gaps and
            enrichments.  Populated by the Research agent.
        pdf_path: Path to the generated PDF learning guide.
        ppt_path: Path to the generated Gap Analysis PowerPoint.
        video_dir: Directory containing per-topic video files.
        current_stage: Label tracking which pipeline stage last completed.
    """

    # Input
    job_id: str
    file_paths: list[str]

    # After Agent 1 (Ingest)
    topics: list[dict]  # [{"name": "...", "description": "...", "key_techniques": [...], "domain_context": "..."}, ...]
    raw_text: str  # concatenated extracted text
    curriculum_scope: str  # one-sentence description of the curriculum's domain boundaries

    # After Agent 2 (Research)
    gap_summary: list[dict]  # [{"topic": "...", "gaps": [...], "enrichments": [...]}, ...]

    # After Agent 3 (Generate)
    pdf_path: str
    ppt_path: str  # path to generated Gap Analysis PowerPoint
    video_dir: str  # directory containing per-topic video files (when --format video/both)

    # Runtime config (passed via state to avoid mutating global settings)
    output_formats: str  # comma-separated, e.g. "pdf,ppt,script"

    # Tracking
    current_stage: str
