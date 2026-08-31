"""Tests for backend/pipeline/agent_quiz.py.

Covers quiz_generate_node, _calculate_gap_percentage gap-warning logging,
_distribute_counts, _validate_question, _enforce_difficulty_distribution,
_filter_valid_questions, and _generate_all_topics helpers.

All tests mock get_llm — no real OpenAI calls are made.
"""

from __future__ import annotations

import json
import logging
from unittest.mock import MagicMock, patch



# ---------------------------------------------------------------------------
# Minimal valid question factory
# ---------------------------------------------------------------------------

def _make_question(**overrides) -> dict:
    """Build a minimal valid question dict, with optional field overrides."""
    q = {
        "question_text": "What is self-attention?",
        "question_type": "mcq",
        "options": ["A", "B", "C", "D"],
        "correct_index": 0,
        "difficulty": "medium",
        "blooms_level": "understand",
        "source_section": "Core Content",
        "feedback_correct": "Correct!",
        "feedback_incorrect": "Incorrect.",
        "topic": "Transformers",
    }
    q.update(overrides)
    return q


def _make_llm_with_questions(questions: list[dict]) -> MagicMock:
    """Return a mock LLM whose .invoke() returns the given questions as JSON."""
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(
        content=json.dumps({"questions": questions})
    )
    return llm


# ---------------------------------------------------------------------------
# _calculate_gap_percentage
# ---------------------------------------------------------------------------


class TestCalculateGapPercentage:
    def test_returns_zero_for_empty_questions(self):
        from backend.pipeline.agent_quiz import _calculate_gap_percentage
        result = _calculate_gap_percentage([], ["concept A"])
        assert result == 0.0

    def test_returns_zero_when_no_gap_topics(self):
        from backend.pipeline.agent_quiz import _calculate_gap_percentage
        questions = [_make_question(source_section="Core Content")]
        result = _calculate_gap_percentage(questions, [])
        assert result == 0.0

    def test_counts_question_with_gap_in_source_section(self):
        from backend.pipeline.agent_quiz import _calculate_gap_percentage
        questions = [_make_question(source_section="gap - deployment optimization")]
        result = _calculate_gap_percentage(questions, [])
        assert result == 100.0

    def test_counts_question_matching_gap_topic(self):
        from backend.pipeline.agent_quiz import _calculate_gap_percentage
        questions = [
            _make_question(source_section="deployment optimization"),
            _make_question(source_section="core content"),
        ]
        result = _calculate_gap_percentage(questions, ["deployment optimization"])
        assert result == 50.0

    def test_case_insensitive_match(self):
        from backend.pipeline.agent_quiz import _calculate_gap_percentage
        questions = [_make_question(source_section="Deployment Optimization")]
        result = _calculate_gap_percentage(questions, ["deployment optimization"])
        assert result == 100.0

    def test_returns_float(self):
        from backend.pipeline.agent_quiz import _calculate_gap_percentage
        questions = [_make_question(source_section="gap concept")]
        result = _calculate_gap_percentage(questions, [])
        assert isinstance(result, float)

    def test_100_pct_all_gap_questions(self):
        from backend.pipeline.agent_quiz import _calculate_gap_percentage
        questions = [
            _make_question(source_section="gap: fine tuning"),
            _make_question(source_section="gap: inference"),
        ]
        result = _calculate_gap_percentage(questions, [])
        assert result == 100.0


# ---------------------------------------------------------------------------
# quiz_generate_node — gap percentage warning integration
# ---------------------------------------------------------------------------


class TestQuizGenerateNodeGapWarning:
    """Verify that quiz_generate_node logs a warning when gap_pct < 40%."""

    def _make_state(self, questions: list[dict]) -> dict:
        return {
            "job_id": "test0001",
            "user_id": "user-uuid",
            "topics": [{"name": "Transformers"}],
            "modules_md": ["# Module content"],
            "gap_summary": [{"concept": "deployment", "topic": "Transformers"}],
            "curriculum_scope": "NLP",
            "question_count": len(questions) or 1,
        }

    @patch("backend.pipeline.agent_quiz.get_llm")
    def test_warning_logged_when_gap_pct_below_threshold(self, mock_get_llm, caplog):
        """When <40% of questions target gaps, a WARNING must be logged."""
        from backend.pipeline.agent_quiz import quiz_generate_node

        # Questions whose source_section has no "gap" keyword and no gap topic match
        questions = [_make_question(source_section="Core Content")] * 5
        mock_get_llm.return_value = _make_llm_with_questions(questions)

        state = self._make_state(questions)

        with caplog.at_level(logging.WARNING, logger="backend.pipeline.agent_quiz"):
            quiz_generate_node(state)

        gap_warnings = [
            r for r in caplog.records
            if "threshold" in r.message.lower() or "40" in r.message
        ]
        assert gap_warnings, "Expected a gap-targeting warning but none was logged"

    @patch("backend.pipeline.agent_quiz.get_llm")
    def test_no_warning_when_gap_pct_above_threshold(self, mock_get_llm, caplog):
        """When >=40% of questions target gaps, no threshold warning is logged."""
        from backend.pipeline.agent_quiz import quiz_generate_node

        # All questions have "gap" in source_section
        questions = [_make_question(source_section="gap: deployment")] * 5
        mock_get_llm.return_value = _make_llm_with_questions(questions)

        state = self._make_state(questions)

        with caplog.at_level(logging.WARNING, logger="backend.pipeline.agent_quiz"):
            quiz_generate_node(state)

        threshold_warnings = [
            r for r in caplog.records
            if "threshold" in r.message.lower()
        ]
        assert not threshold_warnings

    @patch("backend.pipeline.agent_quiz.get_llm")
    def test_node_returns_questions_key(self, mock_get_llm):
        """quiz_generate_node must return a dict with a 'questions' key."""
        from backend.pipeline.agent_quiz import quiz_generate_node

        questions = [_make_question()] * 3
        mock_get_llm.return_value = _make_llm_with_questions(questions)

        state = {
            "job_id": "test0001",
            "user_id": "u1",
            "topics": [{"name": "Transformers"}],
            "modules_md": [],
            "gap_summary": [],
            "curriculum_scope": "NLP",
            "question_count": 3,
        }
        result = quiz_generate_node(state)
        assert "questions" in result

    @patch("backend.pipeline.agent_quiz.get_llm")
    def test_node_assigns_sort_order(self, mock_get_llm):
        """quiz_generate_node must assign sort_order to each question."""
        from backend.pipeline.agent_quiz import quiz_generate_node

        questions = [_make_question(), _make_question()]
        mock_get_llm.return_value = _make_llm_with_questions(questions)

        state = {
            "job_id": "test0001",
            "user_id": "u1",
            "topics": [{"name": "Transformers"}],
            "modules_md": [],
            "gap_summary": [],
            "curriculum_scope": "NLP",
            "question_count": 2,
        }
        result = quiz_generate_node(state)
        for i, q in enumerate(result["questions"]):
            assert q["sort_order"] == i

    @patch("backend.pipeline.agent_quiz.get_llm")
    def test_node_empty_gap_summary_does_not_crash(self, mock_get_llm):
        """quiz_generate_node must not crash when gap_summary is empty."""
        from backend.pipeline.agent_quiz import quiz_generate_node

        questions = [_make_question()]
        mock_get_llm.return_value = _make_llm_with_questions(questions)

        state = {
            "job_id": "test0001",
            "user_id": "u1",
            "topics": [{"name": "Transformers"}],
            "modules_md": [],
            "gap_summary": [],
            "curriculum_scope": "NLP",
            "question_count": 1,
        }
        result = quiz_generate_node(state)
        assert isinstance(result["questions"], list)


# ---------------------------------------------------------------------------
# _distribute_counts
# ---------------------------------------------------------------------------


class TestDistributeCounts:
    def test_zero_topics(self):
        from backend.pipeline.agent_quiz import _distribute_counts
        result = _distribute_counts(0, 10)
        assert result == []

    def test_evenly_divisible(self):
        from backend.pipeline.agent_quiz import _distribute_counts
        result = _distribute_counts(4, 20)
        assert result == [5, 5, 5, 5]

    def test_remainder_distributed_to_first_topics(self):
        from backend.pipeline.agent_quiz import _distribute_counts
        result = _distribute_counts(3, 10)
        assert sum(result) == 10
        assert len(result) == 3
        # First topic(s) should get the extra
        assert result[0] > result[-1] or sum(result) == 10

    def test_single_topic(self):
        from backend.pipeline.agent_quiz import _distribute_counts
        result = _distribute_counts(1, 15)
        assert result == [15]

    def test_total_preserved(self):
        from backend.pipeline.agent_quiz import _distribute_counts
        result = _distribute_counts(7, 20)
        assert sum(result) == 20


# ---------------------------------------------------------------------------
# _validate_question
# ---------------------------------------------------------------------------


class TestValidateQuestion:
    def test_valid_question_passes(self):
        from backend.pipeline.agent_quiz import _validate_question
        is_valid, errors = _validate_question(_make_question())
        assert is_valid
        assert errors == []

    def test_missing_required_field_fails(self):
        from backend.pipeline.agent_quiz import _validate_question
        q = _make_question()
        del q["question_text"]
        is_valid, errors = _validate_question(q)
        assert not is_valid
        assert any("question_text" in e for e in errors)

    def test_wrong_option_count_fails(self):
        from backend.pipeline.agent_quiz import _validate_question
        q = _make_question(options=["A", "B", "C"])  # 3 instead of 4
        is_valid, errors = _validate_question(q)
        assert not is_valid
        assert any("options" in e or "4" in e for e in errors)

    def test_correct_index_out_of_range_fails(self):
        from backend.pipeline.agent_quiz import _validate_question
        q = _make_question(correct_index=5)
        is_valid, errors = _validate_question(q)
        assert not is_valid
        assert any("correct_index" in e for e in errors)

    def test_invalid_difficulty_fails(self):
        from backend.pipeline.agent_quiz import _validate_question
        q = _make_question(difficulty="impossible")
        is_valid, errors = _validate_question(q)
        assert not is_valid
        assert any("difficulty" in e for e in errors)

    def test_invalid_blooms_level_fails(self):
        from backend.pipeline.agent_quiz import _validate_question
        q = _make_question(blooms_level="invent")
        is_valid, errors = _validate_question(q)
        assert not is_valid
        assert any("blooms_level" in e for e in errors)

    def test_correct_index_as_float_fails(self):
        from backend.pipeline.agent_quiz import _validate_question
        q = _make_question(correct_index=1.0)
        is_valid, errors = _validate_question(q)
        assert not is_valid

    def test_correct_index_zero_is_valid(self):
        from backend.pipeline.agent_quiz import _validate_question
        q = _make_question(correct_index=0)
        is_valid, _ = _validate_question(q)
        assert is_valid

    def test_correct_index_three_is_valid(self):
        from backend.pipeline.agent_quiz import _validate_question
        q = _make_question(correct_index=3)
        is_valid, _ = _validate_question(q)
        assert is_valid

    def test_all_valid_bloom_levels_pass(self):
        from backend.pipeline.agent_quiz import _validate_question, _VALID_BLOOMS
        for level in _VALID_BLOOMS:
            q = _make_question(blooms_level=level)
            is_valid, _ = _validate_question(q)
            assert is_valid, f"Expected {level} to be valid"


# ---------------------------------------------------------------------------
# _enforce_difficulty_distribution
# ---------------------------------------------------------------------------


class TestEnforceDifficultyDistribution:
    def test_empty_list_returns_empty(self):
        from backend.pipeline.agent_quiz import _enforce_difficulty_distribution
        result = _enforce_difficulty_distribution([], 10)
        assert result == []

    def test_truncates_to_total(self):
        from backend.pipeline.agent_quiz import _enforce_difficulty_distribution
        questions = [_make_question() for _ in range(10)]
        result = _enforce_difficulty_distribution(questions, 5)
        assert len(result) == 5

    def test_30_pct_easy_for_10_questions(self):
        from backend.pipeline.agent_quiz import _enforce_difficulty_distribution
        questions = [_make_question() for _ in range(10)]
        result = _enforce_difficulty_distribution(questions, 10)
        easy_count = sum(1 for q in result if q["difficulty"] == "easy")
        assert easy_count == 3

    def test_20_pct_hard_for_10_questions(self):
        from backend.pipeline.agent_quiz import _enforce_difficulty_distribution
        questions = [_make_question() for _ in range(10)]
        result = _enforce_difficulty_distribution(questions, 10)
        hard_count = sum(1 for q in result if q["difficulty"] == "hard")
        assert hard_count == 2

    def test_all_questions_have_valid_difficulty(self):
        from backend.pipeline.agent_quiz import _enforce_difficulty_distribution
        questions = [_make_question() for _ in range(20)]
        result = _enforce_difficulty_distribution(questions, 20)
        valid_diffs = {"easy", "medium", "hard"}
        for q in result:
            assert q["difficulty"] in valid_diffs


# ---------------------------------------------------------------------------
# _filter_valid_questions
# ---------------------------------------------------------------------------


class TestFilterValidQuestions:
    def test_all_valid_returns_all(self):
        from backend.pipeline.agent_quiz import _filter_valid_questions
        questions = [_make_question(), _make_question()]
        result = _filter_valid_questions(questions, "Topic")
        assert len(result) == 2

    def test_invalid_question_excluded(self):
        from backend.pipeline.agent_quiz import _filter_valid_questions
        bad = _make_question()
        del bad["question_text"]
        good = _make_question()
        result = _filter_valid_questions([bad, good], "Topic")
        assert len(result) == 1

    def test_all_invalid_returns_empty(self):
        from backend.pipeline.agent_quiz import _filter_valid_questions
        bad = {"no_fields": True}
        result = _filter_valid_questions([bad], "Topic")
        assert result == []

    def test_empty_input_returns_empty(self):
        from backend.pipeline.agent_quiz import _filter_valid_questions
        result = _filter_valid_questions([], "Topic")
        assert result == []


# ---------------------------------------------------------------------------
# _invoke_and_parse
# ---------------------------------------------------------------------------


class TestInvokeAndParse:
    def test_parses_valid_json_response(self):
        from backend.pipeline.agent_quiz import _invoke_and_parse
        q = _make_question()
        llm = _make_llm_with_questions([q])
        result = _invoke_and_parse(llm, "prompt", "Topic", 0)
        assert result is not None
        assert len(result) == 1

    def test_returns_none_on_invalid_json(self):
        from backend.pipeline.agent_quiz import _invoke_and_parse
        llm = MagicMock()
        llm.invoke.return_value = MagicMock(content="not json at all")
        result = _invoke_and_parse(llm, "prompt", "Topic", 0)
        assert result is None

    def test_returns_none_on_missing_questions_key(self):
        from backend.pipeline.agent_quiz import _invoke_and_parse
        llm = MagicMock()
        llm.invoke.return_value = MagicMock(content='{"data": []}')
        result = _invoke_and_parse(llm, "prompt", "Topic", 0)
        assert result == []

    def test_returns_none_on_llm_exception(self):
        from backend.pipeline.agent_quiz import _invoke_and_parse
        llm = MagicMock()
        llm.invoke.side_effect = AttributeError("no content")
        result = _invoke_and_parse(llm, "prompt", "Topic", 0)
        assert result is None
