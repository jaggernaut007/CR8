"""Eval harness runner — runs pipeline and captures outputs for scoring."""

from __future__ import annotations

import json

from backend.evals.datasets.loader import load_cached_state, build_eval_inputs
from backend.evals.datasets.schema import EvalResult, OutputType
from backend.evals.harness.scorer import (
    score_module, score_ppt, score_script, score_consistency, compute_weighted_total,
)
from backend.evals.prompt_registry.registry import PromptRegistry


class EvalRunner:
    """Run evaluation on cached pipeline state with optional prompt variant swaps."""

    def __init__(self, dataset_dir: str, prompt_variant: str = "v1", state_file: str | None = None):
        self.dataset_dir = dataset_dir
        self.prompt_variant = prompt_variant
        self.registry = PromptRegistry()
        if state_file:
            with open(state_file) as f:
                self.state = json.load(f)
        else:
            self.state = load_cached_state(dataset_dir)
        self.eval_inputs = build_eval_inputs(self.state)

    def run(
        self,
        cases: list[str] | None = None,
        run_judge: bool = True,
        output_types: list[str] | None = None,
    ) -> list[EvalResult]:
        """Run evaluation on specified cases (or all).

        Args:
            cases: List of case_ids to evaluate. None = all cases.
            run_judge: If True, run L2 LLM judge. If False, L1 structural only.
            output_types: List of output types to evaluate ("module", "ppt", "script").
                         None = evaluate whatever outputs exist in cached state.
        """
        # Filter to requested cases
        inputs = self.eval_inputs
        if cases:
            inputs = [inp for inp in inputs if inp.case_id in cases]

        if not inputs:
            print("[Eval] No matching cases found.")
            return []

        types = output_types or ["module", "ppt", "script"]
        results = []

        # Get cached outputs
        cached_outputs = self.state.get("cached_outputs", {})

        for inp in inputs:
            topic_name = inp.topic_name
            topic_outputs = cached_outputs.get(topic_name, {})
            print(f"[Eval] Evaluating: {topic_name}")

            # Score each available output type
            if "module" in types and "module_md" in topic_outputs:
                result = score_module(
                    module_md=topic_outputs["module_md"],
                    topic_name=topic_name,
                    curriculum_scope=inp.curriculum_scope,
                    gap_summary=inp.gap_summary,
                    prompt_variant=self.prompt_variant,
                    run_judge=run_judge,
                )
                results.append(result)

            if "ppt" in types and "ppt_json" in topic_outputs:
                result = score_ppt(
                    ppt_json=topic_outputs["ppt_json"],
                    topic_name=topic_name,
                    curriculum_scope=inp.curriculum_scope,
                    gap_summary=inp.gap_summary,
                    prompt_variant=self.prompt_variant,
                    run_judge=run_judge,
                )
                results.append(result)

            if "script" in types and "script" in topic_outputs:
                result = score_script(
                    script=topic_outputs["script"],
                    topic_name=topic_name,
                    curriculum_scope=inp.curriculum_scope,
                    gap_summary=inp.gap_summary,
                    prompt_variant=self.prompt_variant,
                    run_judge=run_judge,
                )
                results.append(result)

            # Cross-output consistency (only if all 3 exist)
            if (
                run_judge
                and all(t in types for t in ["module", "ppt", "script"])
                and all(k in topic_outputs for k in ["module_md", "ppt_json", "script"])
            ):
                consistency_scores = score_consistency(
                    module_md=topic_outputs["module_md"],
                    ppt_json=topic_outputs["ppt_json"],
                    script=topic_outputs["script"],
                    topic_name=topic_name,
                    gap_summary=inp.gap_summary,
                )
                consistency_total = compute_weighted_total(consistency_scores)
                results.append(EvalResult(
                    case_id=inp.case_id,
                    output_type=OutputType.MODULE,  # stored under module for convenience
                    prompt_variant=f"{self.prompt_variant}_consistency",
                    structural_checks={},
                    criterion_scores=consistency_scores,
                    weighted_total=consistency_total,
                    raw_output="",
                ))

        return results

    def run_structural_only(self, cases: list[str] | None = None) -> list[EvalResult]:
        """Run only L1 structural checks (no LLM cost)."""
        return self.run(cases=cases, run_judge=False)
