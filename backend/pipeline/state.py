from typing import TypedDict


class PipelineState(TypedDict):
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
    video_dir: str  # directory containing per-topic video files (when --format video/both)

    # Tracking
    current_stage: str
