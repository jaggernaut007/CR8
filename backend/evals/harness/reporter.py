"""Generate eval reports in JSON and Markdown formats."""

from __future__ import annotations

import json
import os
from datetime import datetime

from backend.evals.datasets.schema import EvalResult, ComparisonResult


def results_to_json(results: list[EvalResult], output_path: str | None = None) -> str:
    """Serialize eval results to JSON."""
    data = [r.model_dump() for r in results]
    json_str = json.dumps(data, indent=2, default=str)
    if output_path:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w") as f:
            f.write(json_str)
    return json_str


def results_to_markdown(results: list[EvalResult]) -> str:
    """Generate a Markdown eval report."""
    lines = [
        "# Eval Report",
        f"**Generated**: {datetime.now().isoformat()}",
        f"**Cases evaluated**: {len(results)}",
        "",
    ]

    # Group by output type
    by_type: dict[str, list[EvalResult]] = {}
    for r in results:
        key = r.output_type.value
        by_type.setdefault(key, []).append(r)

    for output_type, type_results in by_type.items():
        lines.append(f"## {output_type.upper()}")
        lines.append("")

        for r in type_results:
            lines.append(f"### {r.case_id} (variant: {r.prompt_variant})")
            lines.append(f"**Weighted score**: {r.weighted_total:.2f}/5.00")
            lines.append("")

            # Structural checks
            if r.structural_checks:
                passed = sum(1 for v in r.structural_checks.values() if v)
                total = len(r.structural_checks)
                lines.append(f"**Structural checks**: {passed}/{total} passed")
                for name, ok in sorted(r.structural_checks.items()):
                    icon = "PASS" if ok else "FAIL"
                    lines.append(f"  - [{icon}] {name}")
                lines.append("")

            # Criterion scores
            if r.criterion_scores:
                lines.append("**Criterion scores**:")
                lines.append("")
                lines.append("| Criterion | Score | Weight | Rationale |")
                lines.append("|-----------|-------|--------|-----------|")
                for s in r.criterion_scores:
                    rationale = s.rationale[:80] + "..." if len(s.rationale) > 80 else s.rationale
                    lines.append(
                        f"| {s.criterion_name} | {s.score}/5 | {s.weight:.0%} | {rationale} |"
                    )
                lines.append("")

        # Type-level summary
        if type_results:
            avg = sum(r.weighted_total for r in type_results) / len(type_results)
            lines.append(f"**Average {output_type} score**: {avg:.2f}/5.00")
            lines.append("")

    # Overall summary
    if results:
        overall = sum(r.weighted_total for r in results) / len(results)
        lines.append("---")
        lines.append(f"**Overall average**: {overall:.2f}/5.00")

    return "\n".join(lines)


def comparison_to_markdown(comp: ComparisonResult) -> str:
    """Generate a Markdown comparison report."""
    lines = [
        "# A/B Comparison Report",
        f"**Variant A**: {comp.variant_a} (score: {comp.aggregate_a:.2f})",
        f"**Variant B**: {comp.variant_b} (score: {comp.aggregate_b:.2f})",
        f"**Winner**: {comp.winner}",
    ]
    if comp.p_value is not None:
        lines.append(f"**p-value**: {comp.p_value:.4f}")
    lines.append("")

    if comp.regressions:
        lines.append("**REGRESSIONS detected** (criteria that got worse):")
        for r in comp.regressions:
            lines.append(f"  - {r}: {comp.per_criterion_deltas.get(r, 0):+.2f}")
        lines.append("")

    # Per-criterion deltas
    if comp.per_criterion_deltas:
        lines.append("## Per-Criterion Deltas (B - A)")
        lines.append("")
        lines.append("| Criterion | Delta | Direction |")
        lines.append("|-----------|-------|-----------|")
        for crit, delta in sorted(comp.per_criterion_deltas.items(), key=lambda x: x[1]):
            direction = "improved" if delta > 0 else "regressed" if delta < 0 else "unchanged"
            lines.append(f"| {crit} | {delta:+.2f} | {direction} |")
        lines.append("")

    # Per-case results
    if comp.cases:
        lines.append("## Per-Case Scores")
        lines.append("")
        lines.append("| Case | Type | Score A | Score B | Delta |")
        lines.append("|------|------|---------|---------|-------|")
        for c in comp.cases:
            lines.append(
                f"| {c['case_id']} | {c['output_type']} | {c['score_a']:.2f} | {c['score_b']:.2f} | {c['delta']:+.2f} |"
            )

    return "\n".join(lines)
