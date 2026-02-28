"""Orchestrates Layer 1 (structural) and Layer 2 (LLM judge) scoring."""

from __future__ import annotations

import json

from backend.evals.datasets.schema import CriterionScore, EvalResult, OutputType
from backend.evals.structural import module_checks, ppt_checks, script_checks
from backend.evals.judges.module_judge import ModuleJudge
from backend.evals.judges.ppt_judge import PPTJudge
from backend.evals.judges.script_judge import ScriptJudge
from backend.evals.judges.consistency_judge import ConsistencyJudge


def compute_weighted_total(scores: list[CriterionScore]) -> float:
    """Compute weighted average score (0-5 scale)."""
    if not scores:
        return 0.0
    total_weight = sum(s.weight for s in scores)
    if total_weight == 0:
        return 0.0
    return sum(s.score * s.weight for s in scores) / total_weight


def score_module(
    module_md: str,
    topic_name: str,
    curriculum_scope: str,
    gap_summary: dict,
    prompt_variant: str,
    run_judge: bool = True,
) -> EvalResult:
    """Score a learning module with L1 structural checks and optional L2 judge."""
    structural = module_checks.run_all(module_md)

    criterion_scores = []
    if run_judge:
        judge = ModuleJudge()
        criterion_scores = judge.evaluate(module_md, topic_name, curriculum_scope, gap_summary)

    weighted = compute_weighted_total(criterion_scores)
    case_id = topic_name.lower().replace(" ", "_")

    return EvalResult(
        case_id=case_id,
        output_type=OutputType.MODULE,
        prompt_variant=prompt_variant,
        structural_checks=structural,
        criterion_scores=criterion_scores,
        weighted_total=weighted,
        raw_output=module_md,
    )


def score_ppt(
    ppt_json: str | dict,
    topic_name: str,
    curriculum_scope: str,
    gap_summary: dict,
    prompt_variant: str,
    expected_topic_count: int | None = None,
    run_judge: bool = True,
) -> EvalResult:
    """Score a PPT slide structure with L1 and optional L2."""
    ppt_str = ppt_json if isinstance(ppt_json, str) else json.dumps(ppt_json, indent=2)
    structural = ppt_checks.run_all(ppt_str, expected_topic_count)

    criterion_scores = []
    if run_judge:
        judge = PPTJudge()
        criterion_scores = judge.evaluate(ppt_json, topic_name, curriculum_scope, gap_summary)

    weighted = compute_weighted_total(criterion_scores)
    case_id = topic_name.lower().replace(" ", "_")

    return EvalResult(
        case_id=case_id,
        output_type=OutputType.PPT,
        prompt_variant=prompt_variant,
        structural_checks=structural,
        criterion_scores=criterion_scores,
        weighted_total=weighted,
        raw_output=ppt_str,
    )


def score_script(
    script: str,
    topic_name: str,
    curriculum_scope: str,
    gap_summary: dict,
    prompt_variant: str,
    run_judge: bool = True,
) -> EvalResult:
    """Score a video script with L1 and optional L2."""
    structural = script_checks.run_all(script)

    criterion_scores = []
    if run_judge:
        judge = ScriptJudge()
        criterion_scores = judge.evaluate(script, topic_name, curriculum_scope, gap_summary)

    weighted = compute_weighted_total(criterion_scores)
    case_id = topic_name.lower().replace(" ", "_")

    return EvalResult(
        case_id=case_id,
        output_type=OutputType.SCRIPT,
        prompt_variant=prompt_variant,
        structural_checks=structural,
        criterion_scores=criterion_scores,
        weighted_total=weighted,
        raw_output=script,
    )


def score_consistency(
    module_md: str,
    ppt_json: str | dict,
    script: str,
    topic_name: str,
    gap_summary: dict,
) -> list[CriterionScore]:
    """Score cross-output consistency (L2 only)."""
    judge = ConsistencyJudge()
    return judge.evaluate(module_md, ppt_json, script, topic_name, gap_summary)
