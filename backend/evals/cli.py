"""CLI entry point for the eval framework.

Usage:
    python -m backend.evals.cli check --dataset cs224n
    python -m backend.evals.cli run --dataset cs224n --variant v1
    python -m backend.evals.cli compare --dataset cs224n --variant-a v1 --variant-b v2
    python -m backend.evals.cli list
"""

from __future__ import annotations

import argparse
import json
import os

from backend.evals.config import eval_settings
from backend.evals.datasets.loader import list_datasets
from backend.evals.harness.runner import EvalRunner
from backend.evals.harness.comparator import compare
from backend.evals.harness.reporter import (
    results_to_json,
    results_to_markdown,
    comparison_to_markdown,
)
from backend.evals.prompt_registry.registry import PromptRegistry


def cmd_check(args):
    """Run structural checks only (no LLM cost)."""
    dataset_dir = os.path.join(eval_settings.datasets_dir, args.dataset)
    runner = EvalRunner(dataset_dir, prompt_variant=args.variant)
    results = runner.run_structural_only(cases=args.cases)

    if not results:
        print("No results. Check that cached_state exists and has cached_outputs.")
        return

    # Print summary
    total_checks = 0
    total_passed = 0
    for r in results:
        checks = r.structural_checks
        passed = sum(1 for v in checks.values() if v)
        total_checks += len(checks)
        total_passed += passed
        status = "PASS" if passed == len(checks) else "FAIL"
        print(f"[{status}] {r.case_id} ({r.output_type.value}): {passed}/{len(checks)} checks passed")
        for name, ok in sorted(checks.items()):
            if not ok:
                print(f"       FAIL: {name}")

    print(f"\nTotal: {total_passed}/{total_checks} checks passed")


def cmd_run(args):
    """Run full eval (structural + LLM judge)."""
    dataset_dir = os.path.join(eval_settings.datasets_dir, args.dataset)
    runner = EvalRunner(dataset_dir, prompt_variant=args.variant)
    results = runner.run(cases=args.cases, run_judge=True, output_types=args.types)

    if not results:
        print("No results. Check that cached_state exists and has cached_outputs.")
        return

    # Generate reports
    report_md = results_to_markdown(results)
    print(report_md)

    # Save JSON report
    os.makedirs(eval_settings.reports_dir, exist_ok=True)
    json_path = os.path.join(eval_settings.reports_dir, f"{args.dataset}_{args.variant}_results.json")
    results_to_json(results, json_path)
    print(f"\nJSON report saved to: {json_path}")


def cmd_compare(args):
    """A/B compare two prompt variants."""
    dataset_dir = os.path.join(eval_settings.datasets_dir, args.dataset)

    # Variant A uses default cached state
    state_a = None
    # Variant B can use an alternate state file (e.g. regenerated v2 outputs)
    state_b = args.state_b if hasattr(args, "state_b") and args.state_b else None

    print(f"Running variant A: {args.variant_a}...")
    runner_a = EvalRunner(dataset_dir, prompt_variant=args.variant_a, state_file=state_a)
    # If variant B has a different state file, limit A to matching cases
    cases_filter = None
    if state_b:
        runner_b_pre = EvalRunner(dataset_dir, prompt_variant=args.variant_b, state_file=state_b)
        cases_filter = [inp.case_id for inp in runner_b_pre.eval_inputs]
    results_a = runner_a.run(run_judge=True, cases=cases_filter)

    print(f"\nRunning variant B: {args.variant_b}...")
    runner_b = EvalRunner(dataset_dir, prompt_variant=args.variant_b, state_file=state_b)
    results_b = runner_b.run(run_judge=True)

    comparison = compare(results_a, results_b)
    report = comparison_to_markdown(comparison)
    print(report)

    # Save comparison
    os.makedirs(eval_settings.reports_dir, exist_ok=True)
    json_path = os.path.join(
        eval_settings.reports_dir,
        f"{args.dataset}_{args.variant_a}_vs_{args.variant_b}.json",
    )
    with open(json_path, "w") as f:
        json.dump(comparison.model_dump(), f, indent=2, default=str)
    print(f"\nComparison saved to: {json_path}")


def cmd_list(args):
    """List available datasets and prompt variants."""
    print("Datasets:")
    datasets = list_datasets(eval_settings.datasets_dir)
    if datasets:
        for d in datasets:
            print(f"  - {d}")
    else:
        print("  (none found)")

    print("\nPrompt variants:")
    registry = PromptRegistry()
    for agent in registry.list_agents():
        variants = registry.list_variants(agent)
        print(f"  {agent}: {', '.join(variants)}")


def main():
    parser = argparse.ArgumentParser(description="CR8 Evaluation Framework")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # check
    p_check = subparsers.add_parser("check", help="Run structural checks only")
    p_check.add_argument("--dataset", required=True, help="Dataset ID")
    p_check.add_argument("--variant", default="v1", help="Prompt variant")
    p_check.add_argument("--cases", nargs="*", help="Specific case IDs to evaluate")

    # run
    p_run = subparsers.add_parser("run", help="Run full eval (structural + LLM judge)")
    p_run.add_argument("--dataset", required=True, help="Dataset ID")
    p_run.add_argument("--variant", default="v1", help="Prompt variant")
    p_run.add_argument("--cases", nargs="*", help="Specific case IDs to evaluate")
    p_run.add_argument("--types", nargs="*", help="Output types to evaluate (module, ppt, script)")

    # compare
    p_compare = subparsers.add_parser("compare", help="A/B compare two variants")
    p_compare.add_argument("--dataset", required=True, help="Dataset ID")
    p_compare.add_argument("--variant-a", required=True, help="Variant A")
    p_compare.add_argument("--variant-b", required=True, help="Variant B")
    p_compare.add_argument("--state-b", default=None, help="Alternate state file for variant B (e.g. pipeline_state_v2.json)")

    # list
    subparsers.add_parser("list", help="List datasets and variants")

    args = parser.parse_args()

    commands = {
        "check": cmd_check,
        "run": cmd_run,
        "compare": cmd_compare,
        "list": cmd_list,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
