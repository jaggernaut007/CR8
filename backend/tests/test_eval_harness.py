"""Tests for the eval harness: comparator winner/regression logic and scorer L1-only mode.

All tests use run_judge=False or fully mocked judges — zero real API calls.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from hypothesis import given, settings as hyp_settings
from hypothesis import strategies as st


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_result(scores_by_criterion: dict, variant: str, case_id: str = "c1",
                 output_type=None):
    from backend.evals.datasets.schema import CriterionScore, EvalResult, OutputType

    if output_type is None:
        output_type = OutputType.MODULE
    criterion_scores = [
        CriterionScore(criterion_name=k, score=v, weight=1.0, rationale="")
        for k, v in scores_by_criterion.items()
    ]
    total_weight = sum(s.weight for s in criterion_scores) or 1e-9
    weighted = sum(s.score * s.weight for s in criterion_scores) / total_weight
    return EvalResult(
        case_id=case_id,
        output_type=output_type,
        prompt_variant=variant,
        structural_checks={},
        criterion_scores=criterion_scores,
        weighted_total=weighted,
        raw_output="",
    )


# ===========================================================================
# Comparator winner logic
# ===========================================================================


class TestComparatorWinnerLogic:
    """Test the winner determination logic in comparator.compare()."""

    def test_b_wins_when_aggregate_higher_by_large_margin(self):
        from backend.evals.harness.comparator import compare

        # B is 1.0 point higher, well above 0.3 threshold
        ra = _make_result({"depth": 3}, "v1")
        rb = _make_result({"depth": 4}, "v2")
        # weighted_total for ra=3.0, rb=4.0 — delta=+1.0 > 0.3 → winner="b"
        result = compare([ra], [rb])
        assert result.winner == "b"

    def test_a_wins_when_aggregate_higher_by_large_margin(self):
        from backend.evals.harness.comparator import compare

        ra = _make_result({"depth": 5}, "v1")
        rb = _make_result({"depth": 3}, "v2")
        # delta = 3.0 - 5.0 = -2.0 → winner="a"
        result = compare([ra], [rb])
        assert result.winner == "a"

    def test_tie_when_delta_too_small(self):
        from backend.evals.harness.comparator import compare

        ra = _make_result({"depth": 3}, "v1")
        rb = _make_result({"depth": 3}, "v2")
        result = compare([ra], [rb])
        assert result.winner == "tie"

    def test_tie_when_delta_under_threshold(self):
        """Delta of 0.1 is below the 0.3 threshold → tie."""
        from backend.evals.harness.comparator import compare
        from backend.evals.datasets.schema import CriterionScore, EvalResult, OutputType

        # Craft results where weighted_total differs by ~0.1
        ra = EvalResult(
            case_id="c1", output_type=OutputType.MODULE, prompt_variant="v1",
            structural_checks={}, criterion_scores=[],
            weighted_total=3.0, raw_output=""
        )
        rb = EvalResult(
            case_id="c1", output_type=OutputType.MODULE, prompt_variant="v2",
            structural_checks={}, criterion_scores=[],
            weighted_total=3.1, raw_output=""
        )
        result = compare([ra], [rb])
        assert result.winner == "tie"

    def test_regression_detected_when_criterion_drops(self):
        from backend.evals.harness.comparator import compare

        # "depth" drops by 2.0 — exceeds default regression_threshold of 0.5
        ra = _make_result({"depth": 4}, "v1")
        rb = _make_result({"depth": 2}, "v2")
        result = compare([ra], [rb])
        assert "depth" in result.regressions

    def test_no_regressions_when_scores_stable(self):
        from backend.evals.harness.comparator import compare

        ra = _make_result({"depth": 3, "clarity": 4}, "v1")
        rb = _make_result({"depth": 3, "clarity": 4}, "v2")
        result = compare([ra], [rb])
        assert result.regressions == []

    def test_disjoint_cases_produce_no_common_comparisons(self):
        from backend.evals.harness.comparator import compare

        ra = _make_result({"depth": 3}, "v1", case_id="case_a")
        rb = _make_result({"depth": 4}, "v2", case_id="case_b")
        result = compare([ra], [rb])
        # No common keys → empty result, no crash
        assert result.cases == []
        assert result.winner == "tie"

    def test_fewer_than_3_cases_skips_pvalue(self):
        from backend.evals.harness.comparator import compare

        ra = _make_result({"depth": 3}, "v1")
        rb = _make_result({"depth": 4}, "v2")
        result = compare([ra], [rb])
        # n=1, so scipy t-test is skipped
        assert result.p_value is None

    def test_aggregate_scores_calculated_correctly(self):
        from backend.evals.harness.comparator import compare

        ra1 = _make_result({"depth": 2}, "v1", case_id="c1")
        ra2 = _make_result({"depth": 4}, "v1", case_id="c2")
        rb1 = _make_result({"depth": 4}, "v2", case_id="c1")
        rb2 = _make_result({"depth": 4}, "v2", case_id="c2")
        result = compare([ra1, ra2], [rb1, rb2])
        assert result.aggregate_a == pytest.approx(3.0, abs=0.01)
        assert result.aggregate_b == pytest.approx(4.0, abs=0.01)

    def test_empty_inputs_return_default_result(self):
        from backend.evals.harness.comparator import compare

        result = compare([], [])
        assert result.winner == "tie"
        assert result.cases == []


# ===========================================================================
# Scorer L1-only (run_judge=False)
# ===========================================================================


class TestScorerL1Only:
    """Verify scorer functions with run_judge=False make no LLM calls."""

    def test_score_module_l1_only_returns_structural_checks(self, valid_module_md):
        from backend.evals.harness.scorer import score_module

        result = score_module(
            module_md=valid_module_md,
            topic_name="Transformers",
            curriculum_scope="NLP",
            gap_summary={},
            prompt_variant="v1",
            run_judge=False,
        )
        assert isinstance(result.structural_checks, dict)
        assert len(result.structural_checks) > 0

    def test_score_module_l1_no_criterion_scores(self, valid_module_md):
        from backend.evals.harness.scorer import score_module

        result = score_module(
            module_md=valid_module_md,
            topic_name="Transformers",
            curriculum_scope="NLP",
            gap_summary={},
            prompt_variant="v1",
            run_judge=False,
        )
        assert result.criterion_scores == []
        assert result.weighted_total == 0.0

    def test_score_module_l1_no_llm_call(self, valid_module_md):
        from backend.evals.harness.scorer import score_module

        with patch("backend.evals.harness.scorer.ModuleJudge") as MockJudge:
            score_module(
                module_md=valid_module_md,
                topic_name="Transformers",
                curriculum_scope="NLP",
                gap_summary={},
                prompt_variant="v1",
                run_judge=False,
            )
            MockJudge.assert_not_called()

    def test_score_script_l1_only(self, valid_script):
        from backend.evals.harness.scorer import score_script

        result = score_script(
            script=valid_script,
            topic_name="Transformers",
            curriculum_scope="NLP",
            gap_summary={},
            prompt_variant="v1",
            run_judge=False,
        )
        assert isinstance(result.structural_checks, dict)
        assert result.criterion_scores == []

    def test_score_ppt_l1_only(self, valid_ppt_single):
        from backend.evals.harness.scorer import score_ppt

        result = score_ppt(
            ppt_json=valid_ppt_single,
            topic_name="Transformers",
            curriculum_scope="NLP",
            gap_summary={},
            prompt_variant="v1",
            run_judge=False,
        )
        assert isinstance(result.structural_checks, dict)
        assert result.criterion_scores == []

    def test_valid_module_passes_all_structural_checks(self, valid_module_md):
        from backend.evals.harness.scorer import score_module

        result = score_module(
            module_md=valid_module_md,
            topic_name="Transformers",
            curriculum_scope="NLP",
            gap_summary={},
            prompt_variant="v1",
            run_judge=False,
        )
        failed = {k: v for k, v in result.structural_checks.items() if not v}
        assert failed == {}, f"Structural checks failed: {failed}"

    def test_short_module_fails_structural_check(self):
        from backend.evals.harness.scorer import score_module

        short_md = "## Module Overview\nBrief content.\n"
        result = score_module(
            module_md=short_md,
            topic_name="Test",
            curriculum_scope="NLP",
            gap_summary={},
            prompt_variant="v1",
            run_judge=False,
        )
        assert result.structural_checks.get("min_length") is False

    def test_case_id_derived_from_topic_name(self):
        from backend.evals.harness.scorer import score_module

        result = score_module(
            module_md="## Module Overview\nContent.\n",
            topic_name="Word Vectors",
            curriculum_scope="NLP",
            gap_summary={},
            prompt_variant="v1",
            run_judge=False,
        )
        assert result.case_id == "word_vectors"

    def test_output_type_is_correct_for_module(self, valid_module_md):
        from backend.evals.harness.scorer import score_module
        from backend.evals.datasets.schema import OutputType

        result = score_module(
            module_md=valid_module_md,
            topic_name="Transformers",
            curriculum_scope="NLP",
            gap_summary={},
            prompt_variant="v1",
            run_judge=False,
        )
        assert result.output_type == OutputType.MODULE

    def test_output_type_is_correct_for_script(self, valid_script):
        from backend.evals.harness.scorer import score_script
        from backend.evals.datasets.schema import OutputType

        result = score_script(
            script=valid_script,
            topic_name="Transformers",
            curriculum_scope="NLP",
            gap_summary={},
            prompt_variant="v1",
            run_judge=False,
        )
        assert result.output_type == OutputType.SCRIPT

    def test_output_type_is_correct_for_ppt(self, valid_ppt_single):
        from backend.evals.harness.scorer import score_ppt
        from backend.evals.datasets.schema import OutputType

        result = score_ppt(
            ppt_json=valid_ppt_single,
            topic_name="Transformers",
            curriculum_scope="NLP",
            gap_summary={},
            prompt_variant="v1",
            run_judge=False,
        )
        assert result.output_type == OutputType.PPT


# ===========================================================================
# compute_weighted_total property-based tests
# ===========================================================================


class TestPropertyBasedScoring:
    """Hypothesis tests for the compute_weighted_total function."""

    @given(
        st.lists(
            st.fixed_dictionaries({
                "score": st.integers(min_value=1, max_value=5),
                "weight": st.floats(min_value=0.01, max_value=1.0),
            }),
            max_size=10,
        )
    )
    @hyp_settings(max_examples=200)
    def test_compute_weighted_total_always_between_0_and_5(self, score_defs):
        from backend.evals.datasets.schema import CriterionScore
        from backend.evals.harness.scorer import compute_weighted_total

        scores = [
            CriterionScore(
                criterion_name="test",
                score=d["score"],
                weight=d["weight"],
                rationale="",
            )
            for d in score_defs
        ]
        result = compute_weighted_total(scores)
        # Allow a tiny floating-point tolerance above 5.0
        assert 0.0 <= result <= 5.0 + 1e-9, f"Expected in [0, 5], got {result}"

    def test_compute_weighted_total_empty_is_zero(self):
        from backend.evals.harness.scorer import compute_weighted_total

        assert compute_weighted_total([]) == 0.0

    def test_compute_weighted_total_all_same_weight(self):
        from backend.evals.datasets.schema import CriterionScore
        from backend.evals.harness.scorer import compute_weighted_total

        scores = [
            CriterionScore(criterion_name="a", score=3, weight=1.0, rationale=""),
            CriterionScore(criterion_name="b", score=5, weight=1.0, rationale=""),
        ]
        result = compute_weighted_total(scores)
        assert result == pytest.approx(4.0, abs=0.001)

    def test_compute_weighted_total_higher_weight_dominates(self):
        from backend.evals.datasets.schema import CriterionScore
        from backend.evals.harness.scorer import compute_weighted_total

        scores = [
            CriterionScore(criterion_name="a", score=5, weight=0.9, rationale=""),
            CriterionScore(criterion_name="b", score=1, weight=0.1, rationale=""),
        ]
        result = compute_weighted_total(scores)
        # Weighted avg should be closer to 5 than to 1
        assert result > 4.0


# ===========================================================================
# Snapshot tests for EvalResult / ComparisonResult structure
# ===========================================================================


class TestEvalResultSnapshot:
    """Snapshot tests using syrupy to detect structural regressions on schema fields."""

    def test_eval_result_fields_stable(self, snapshot):
        from backend.evals.datasets.schema import EvalResult, OutputType

        # Access model_fields from the class (not instance) to avoid Pydantic deprecation
        field_names = sorted(EvalResult.model_fields.keys())
        assert field_names == snapshot

    def test_comparison_result_fields_stable(self, snapshot):
        from backend.evals.datasets.schema import ComparisonResult

        field_names = sorted(ComparisonResult.model_fields.keys())
        assert field_names == snapshot
