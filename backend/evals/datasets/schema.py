from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class OutputType(str, Enum):
    MODULE = "module"
    PPT = "ppt"
    SCRIPT = "script"


class EvalInput(BaseModel):
    """A single evaluation input case."""

    case_id: str
    input_pdfs: list[str] = Field(default_factory=list)
    topic_name: str
    curriculum_scope: str
    gap_summary: dict = Field(default_factory=dict)


class CriterionScore(BaseModel):
    """Score for a single rubric criterion."""

    criterion_name: str
    score: int = Field(ge=1, le=5)
    weight: float = Field(ge=0.0, le=1.0)
    rationale: str


class EvalResult(BaseModel):
    """Complete evaluation result for one output."""

    case_id: str
    output_type: OutputType
    prompt_variant: str
    structural_checks: dict[str, bool] = Field(default_factory=dict)
    criterion_scores: list[CriterionScore] = Field(default_factory=list)
    weighted_total: float = 0.0
    raw_output: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    langsmith_run_id: str | None = None


class ComparisonResult(BaseModel):
    """A/B comparison between two prompt variants."""

    variant_a: str
    variant_b: str
    cases: list[dict] = Field(default_factory=list)
    aggregate_a: float = 0.0
    aggregate_b: float = 0.0
    per_criterion_deltas: dict[str, float] = Field(default_factory=dict)
    p_value: float | None = None
    winner: str = "tie"
    regressions: list[str] = Field(default_factory=list)


class DatasetManifest(BaseModel):
    """Metadata for an eval dataset."""

    dataset_id: str
    description: str
    version: str = "1.0"
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    input_pdfs: list[str] = Field(default_factory=list)
    cached_state_path: str = ""
