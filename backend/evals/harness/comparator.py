"""A/B comparison of prompt variants with statistical testing."""

from __future__ import annotations

from collections import defaultdict

from backend.evals.config import eval_settings
from backend.evals.datasets.schema import ComparisonResult, EvalResult


def compare(results_a: list[EvalResult], results_b: list[EvalResult]) -> ComparisonResult:
    """Compare two sets of eval results (variant A vs variant B).

    Both sets must cover the same cases and output types.
    """
    variant_a = results_a[0].prompt_variant if results_a else "a"
    variant_b = results_b[0].prompt_variant if results_b else "b"

    # Build lookup: (case_id, output_type) -> result
    lookup_a = {(r.case_id, r.output_type): r for r in results_a}
    lookup_b = {(r.case_id, r.output_type): r for r in results_b}

    common_keys = set(lookup_a.keys()) & set(lookup_b.keys())
    if not common_keys:
        return ComparisonResult(variant_a=variant_a, variant_b=variant_b)

    # Per-case comparison
    cases = []
    scores_a_list = []
    scores_b_list = []
    per_criterion_a = defaultdict(list)
    per_criterion_b = defaultdict(list)

    for key in sorted(common_keys):
        ra = lookup_a[key]
        rb = lookup_b[key]
        delta = rb.weighted_total - ra.weighted_total
        cases.append({
            "case_id": ra.case_id,
            "output_type": ra.output_type.value,
            "score_a": ra.weighted_total,
            "score_b": rb.weighted_total,
            "delta": delta,
        })
        scores_a_list.append(ra.weighted_total)
        scores_b_list.append(rb.weighted_total)

        # Per-criterion tracking
        criteria_a = {s.criterion_name: s.score for s in ra.criterion_scores}
        criteria_b = {s.criterion_name: s.score for s in rb.criterion_scores}
        for crit in set(criteria_a.keys()) | set(criteria_b.keys()):
            if crit in criteria_a:
                per_criterion_a[crit].append(criteria_a[crit])
            if crit in criteria_b:
                per_criterion_b[crit].append(criteria_b[crit])

    # Aggregates
    n = len(scores_a_list)
    agg_a = sum(scores_a_list) / n if n else 0.0
    agg_b = sum(scores_b_list) / n if n else 0.0

    # Per-criterion deltas
    per_criterion_deltas = {}
    regressions = []
    for crit in set(per_criterion_a.keys()) | set(per_criterion_b.keys()):
        scores_a = per_criterion_a.get(crit, [])
        scores_b = per_criterion_b.get(crit, [])
        mean_a = sum(scores_a) / len(scores_a) if scores_a else 0.0
        mean_b = sum(scores_b) / len(scores_b) if scores_b else 0.0
        delta = mean_b - mean_a
        per_criterion_deltas[crit] = round(delta, 3)
        if delta < -eval_settings.regression_threshold:
            regressions.append(crit)

    # Statistical significance (paired t-test)
    p_value = None
    if n >= 3:
        try:
            from scipy.stats import ttest_rel
            _, p_value = ttest_rel(scores_a_list, scores_b_list)
        except ImportError:
            pass

    # Winner
    if (p_value is not None and p_value < 0.05) or abs(agg_b - agg_a) > 0.3:
        winner = "b" if agg_b > agg_a else "a"
    else:
        winner = "tie"

    return ComparisonResult(
        variant_a=variant_a,
        variant_b=variant_b,
        cases=cases,
        aggregate_a=round(agg_a, 3),
        aggregate_b=round(agg_b, 3),
        per_criterion_deltas=per_criterion_deltas,
        p_value=round(p_value, 4) if p_value is not None else None,
        winner=winner,
        regressions=regressions,
    )
