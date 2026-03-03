"""Full A/B comparison workflow: regenerate v2, eval both, compare.

Usage:
    python -m backend.evals.run_ab_comparison --dataset cs224n --topics 5
"""

from __future__ import annotations

import argparse
import json
import os
import time

from backend.evals.config import eval_settings
from backend.evals.regenerate_v2 import regenerate
from backend.evals.harness.runner import EvalRunner
from backend.evals.harness.comparator import compare
from backend.evals.harness.reporter import (
    results_to_json,
    comparison_to_markdown,
)


def run_ab(dataset_id: str, max_topics: int = 5, skip_regen: bool = False):
    """Full A/B comparison workflow."""
    dataset_dir = os.path.join(eval_settings.datasets_dir, dataset_id)
    v2_state_path = os.path.join(dataset_dir, "cached_state", "pipeline_state_v2.json")

    # --- Step 1: Regenerate v2 outputs (if not already done) ---
    if skip_regen and os.path.isfile(v2_state_path):
        print(f"[A/B] Skipping regeneration, using existing v2 state: {v2_state_path}")
    else:
        print("=" * 60)
        print("STEP 1: Regenerating outputs with v2 prompts")
        print("=" * 60)
        start = time.time()
        regenerate(dataset_dir, max_topics=max_topics)
        print(f"[A/B] Regeneration took {time.time() - start:.1f}s")

    # Load v2 state to get the topic list
    with open(v2_state_path) as f:
        v2_state = json.load(f)
    v2_topics = [t["name"] for t in v2_state["topics"]]
    v2_case_ids = [n.lower().replace(" ", "_") for n in v2_topics]
    print(f"\n[A/B] Comparing {len(v2_topics)} topics: {v2_topics}")

    # --- Step 2: Evaluate v1 outputs ---
    print("\n" + "=" * 60)
    print("STEP 2: Evaluating v1 outputs (cached)")
    print("=" * 60)
    start = time.time()
    runner_v1 = EvalRunner(dataset_dir, prompt_variant="v1")
    results_v1 = runner_v1.run(cases=v2_case_ids, run_judge=True)
    print(f"[A/B] v1 eval took {time.time() - start:.1f}s — {len(results_v1)} results")

    # --- Step 3: Evaluate v2 outputs ---
    print("\n" + "=" * 60)
    print("STEP 3: Evaluating v2 outputs (regenerated)")
    print("=" * 60)
    start = time.time()
    runner_v2 = EvalRunner(dataset_dir, prompt_variant="v2", state_file=v2_state_path)
    results_v2 = runner_v2.run(run_judge=True)
    print(f"[A/B] v2 eval took {time.time() - start:.1f}s — {len(results_v2)} results")

    # --- Step 4: Compare ---
    print("\n" + "=" * 60)
    print("STEP 4: A/B Comparison")
    print("=" * 60)
    comparison = compare(results_v1, results_v2)
    report = comparison_to_markdown(comparison)
    print(report)

    # --- Save reports ---
    os.makedirs(eval_settings.reports_dir, exist_ok=True)

    v1_json = os.path.join(eval_settings.reports_dir, f"{dataset_id}_v1_full.json")
    results_to_json(results_v1, v1_json)

    v2_json = os.path.join(eval_settings.reports_dir, f"{dataset_id}_v2_full.json")
    results_to_json(results_v2, v2_json)

    comp_json = os.path.join(eval_settings.reports_dir, f"{dataset_id}_v1_vs_v2.json")
    with open(comp_json, "w") as f:
        json.dump(comparison.model_dump(), f, indent=2, default=str)

    # Save markdown report
    md_report = os.path.join(eval_settings.reports_dir, f"{dataset_id}_v1_vs_v2.md")
    with open(md_report, "w") as f:
        f.write(report)

    print("\n[A/B] Reports saved:")
    print(f"  v1 results: {v1_json}")
    print(f"  v2 results: {v2_json}")
    print(f"  Comparison: {comp_json}")
    print(f"  Report: {md_report}")

    # --- Summary ---
    print(f"\n{'='*60}")
    print("A/B COMPARISON SUMMARY")
    print(f"{'='*60}")
    print(f"  v1 aggregate: {comparison.aggregate_a:.2f}/5.00")
    print(f"  v2 aggregate: {comparison.aggregate_b:.2f}/5.00")
    delta = comparison.aggregate_b - comparison.aggregate_a
    direction = "IMPROVED" if delta > 0 else "REGRESSED" if delta < 0 else "UNCHANGED"
    print(f"  Delta: {delta:+.2f} ({direction})")
    if comparison.p_value is not None:
        sig = "YES" if comparison.p_value < 0.05 else "NO"
        print(f"  Statistical significance (p<0.05): {sig} (p={comparison.p_value:.4f})")
    print(f"  Winner: {comparison.winner}")
    if comparison.regressions:
        print(f"  REGRESSIONS: {', '.join(comparison.regressions)}")
    print(f"{'='*60}")

    return comparison


def main():
    parser = argparse.ArgumentParser(description="Run full A/B comparison")
    parser.add_argument("--dataset", required=True, help="Dataset ID")
    parser.add_argument("--topics", type=int, default=5, help="Max topics to compare")
    parser.add_argument("--skip-regen", action="store_true", help="Skip regeneration if v2 state exists")
    args = parser.parse_args()
    run_ab(args.dataset, max_topics=args.topics, skip_regen=args.skip_regen)


if __name__ == "__main__":
    main()
