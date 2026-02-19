from typing import TypedDict


class PipelineState(TypedDict):
    # Input
    job_id: str
    file_paths: list[str]

    # After Agent 1 (Ingest)
    topics: list[dict]  # [{"name": "...", "description": "..."}, ...]
    raw_text: str  # concatenated extracted text

    # After Agent 2 (Research)
    gap_summary: list[dict]  # [{"topic": "...", "gaps": [...], "enrichments": [...]}, ...]

    # After Agent 3 (Generate)
    pdf_path: str

    # Tracking
    current_stage: str
