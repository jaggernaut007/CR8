"""Tests for the quiz agent, graph, and prompt (backend/pipeline/agent_quiz.py).

All tests mock the LLM — no real API calls. Tests follow TDD: written before
implementation, expected to fail (RED) until agent_quiz.py is implemented.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from backend.prompts.quiz import QUIZ_GENERATE_PROMPT
from backend.pipeline.quiz_state import QuizState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SAMPLE_QUESTION = {
    "question_text": "What is the primary purpose of attention mechanisms?",
    "question_type": "mcq",
    "options": [
        "To reduce training time",
        "To allow the model to focus on relevant parts of the input",
        "To increase the number of parameters",
        "To replace convolutional layers entirely",
    ],
    "correct_index": 1,
    "difficulty": "medium",
    "blooms_level": "understand",
    "source_section": "Module Overview",
    "feedback_correct": "Attention mechanisms enable selective focus on relevant input parts.",
    "feedback_incorrect": "Attention mechanisms help models focus on relevant input, not just reduce time.",
    "topic": "Attention Mechanisms",
}


def _make_questions(
    count: int = 10,
    *,
    difficulties: list[str] | None = None,
    gap_count: int = 4,
) -> list[dict]:
    """Generate a list of mock question dicts with configurable difficulty mix."""
    if difficulties is None:
        # Default: 30% easy, 50% medium, 20% hard
        difficulties = (
            ["easy"] * 3 + ["medium"] * 5 + ["hard"] * 2
            if count == 10
            else ["medium"] * count
        )

    questions = []
    for i in range(count):
        q = dict(_SAMPLE_QUESTION)
        q["question_text"] = f"Question {i + 1}: concept test"
        q["difficulty"] = difficulties[i] if i < len(difficulties) else "medium"
        q["sort_order"] = i
        # Mark some as gap-sourced
        if i < gap_count:
            q["source_section"] = "Gap: Industry skill"
        else:
            q["source_section"] = "Module: Core concept"
        questions.append(q)
    return questions


def _make_llm_response(questions: list[dict]) -> MagicMock:
    """Create a mock LLM response with JSON content."""
    mock_resp = MagicMock()
    mock_resp.content = json.dumps({"questions": questions})
    return mock_resp


def _make_state(**overrides) -> QuizState:
    """Create a minimal QuizState for testing."""
    state: dict = {
        "job_id": "test-job-123",
        "user_id": "user-456",
        "topics": [
            {
                "name": "Attention Mechanisms",
                "description": "Self-attention in transformers",
                "key_techniques": ["scaled dot-product", "multi-head"],
                "domain_context": "NLP",
            }
        ],
        "modules_md": ["# Attention Mechanisms\n\nThis module covers..."],
        "gap_summary": [
            {
                "topic": "Attention Mechanisms",
                "gaps": ["Flash attention optimization", "KV cache strategies"],
                "enrichments": ["Production deployment patterns"],
            }
        ],
        "curriculum_scope": "Natural Language Processing (CS224N)",
        "question_count": 10,
    }
    state.update(overrides)
    return state  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Prompt tests
# ---------------------------------------------------------------------------


class TestQuizPrompt:
    """Verify the prompt template has required structure."""

    def test_has_topic_name_placeholder(self):
        assert "{topic_name}" in QUIZ_GENERATE_PROMPT

    def test_has_module_content_placeholder(self):
        assert "{module_content}" in QUIZ_GENERATE_PROMPT

    def test_has_gap_analysis_placeholder(self):
        assert "{gap_analysis}" in QUIZ_GENERATE_PROMPT

    def test_has_curriculum_scope_placeholder(self):
        assert "{curriculum_scope}" in QUIZ_GENERATE_PROMPT

    def test_has_question_count_placeholder(self):
        assert "{question_count}" in QUIZ_GENERATE_PROMPT

    def test_mentions_gap_targeting_percentage(self):
        assert "40%" in QUIZ_GENERATE_PROMPT

    def test_mentions_difficulty_distribution(self):
        assert "30%" in QUIZ_GENERATE_PROMPT
        assert "50%" in QUIZ_GENERATE_PROMPT
        assert "20%" in QUIZ_GENERATE_PROMPT

    def test_mentions_blooms_taxonomy(self):
        assert "Bloom" in QUIZ_GENERATE_PROMPT


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------


class TestValidateQuestion:
    """Test the question validation helper."""

    def test_valid_question_passes(self):
        from backend.pipeline.agent_quiz import _validate_question

        valid, errors = _validate_question(_SAMPLE_QUESTION)
        assert valid is True
        assert errors == []

    def test_missing_question_text_fails(self):
        from backend.pipeline.agent_quiz import _validate_question

        q = dict(_SAMPLE_QUESTION)
        del q["question_text"]
        valid, errors = _validate_question(q)
        assert valid is False
        assert any("question_text" in e for e in errors)

    def test_wrong_option_count_fails(self):
        from backend.pipeline.agent_quiz import _validate_question

        q = dict(_SAMPLE_QUESTION)
        q["options"] = ["A", "B", "C"]
        valid, errors = _validate_question(q)
        assert valid is False
        assert any("4 options" in e for e in errors)

    def test_invalid_correct_index_fails(self):
        from backend.pipeline.agent_quiz import _validate_question

        q = dict(_SAMPLE_QUESTION)
        q["correct_index"] = 5
        valid, errors = _validate_question(q)
        assert valid is False
        assert any("correct_index" in e for e in errors)

    def test_negative_correct_index_fails(self):
        from backend.pipeline.agent_quiz import _validate_question

        q = dict(_SAMPLE_QUESTION)
        q["correct_index"] = -1
        valid, _errors = _validate_question(q)
        assert valid is False

    def test_invalid_difficulty_fails(self):
        from backend.pipeline.agent_quiz import _validate_question

        q = dict(_SAMPLE_QUESTION)
        q["difficulty"] = "impossible"
        valid, errors = _validate_question(q)
        assert valid is False
        assert any("difficulty" in e for e in errors)

    def test_missing_feedback_fails(self):
        from backend.pipeline.agent_quiz import _validate_question

        q = dict(_SAMPLE_QUESTION)
        del q["feedback_correct"]
        valid, _errors = _validate_question(q)
        assert valid is False


# ---------------------------------------------------------------------------
# Difficulty distribution tests
# ---------------------------------------------------------------------------


class TestEnforceDifficultyDistribution:
    """Test difficulty distribution enforcement."""

    def test_correct_distribution_for_10(self):
        from backend.pipeline.agent_quiz import _enforce_difficulty_distribution

        questions = _make_questions(10, difficulties=["medium"] * 10)
        result = _enforce_difficulty_distribution(questions, 10)

        counts = {"easy": 0, "medium": 0, "hard": 0}
        for q in result:
            counts[q["difficulty"]] += 1

        assert counts["easy"] == 3
        assert counts["medium"] == 5
        assert counts["hard"] == 2

    def test_correct_distribution_for_20(self):
        from backend.pipeline.agent_quiz import _enforce_difficulty_distribution

        questions = _make_questions(20, difficulties=["medium"] * 20)
        result = _enforce_difficulty_distribution(questions, 20)

        counts = {"easy": 0, "medium": 0, "hard": 0}
        for q in result:
            counts[q["difficulty"]] += 1

        assert counts["easy"] == 6
        assert counts["medium"] == 10
        assert counts["hard"] == 4

    def test_preserves_question_content(self):
        from backend.pipeline.agent_quiz import _enforce_difficulty_distribution

        questions = _make_questions(5, difficulties=["medium"] * 5)
        result = _enforce_difficulty_distribution(questions, 5)

        for q in result:
            assert "question_text" in q
            assert "options" in q


# ---------------------------------------------------------------------------
# Gap percentage tests
# ---------------------------------------------------------------------------


class TestCalculateGapPercentage:
    """Test gap targeting percentage calculation."""

    def test_all_gap_questions(self):
        from backend.pipeline.agent_quiz import _calculate_gap_percentage

        gap_topics = ["Flash attention optimization", "KV cache strategies"]
        questions = _make_questions(5, gap_count=5)
        pct = _calculate_gap_percentage(questions, gap_topics)
        assert pct == 100.0

    def test_no_gap_questions(self):
        from backend.pipeline.agent_quiz import _calculate_gap_percentage

        gap_topics = ["Flash attention optimization"]
        questions = _make_questions(5, gap_count=0)
        pct = _calculate_gap_percentage(questions, gap_topics)
        assert pct == 0.0

    def test_mixed_gap_questions(self):
        from backend.pipeline.agent_quiz import _calculate_gap_percentage

        gap_topics = ["Industry skill"]
        questions = _make_questions(10, gap_count=4)
        pct = _calculate_gap_percentage(questions, gap_topics)
        assert pct == pytest.approx(40.0)


# ---------------------------------------------------------------------------
# Quiz generate node tests
# ---------------------------------------------------------------------------


class TestQuizGenerateNode:
    """Test the main quiz generation node with mocked LLM."""

    @patch("backend.pipeline.agent_quiz.get_llm")
    def test_returns_questions_key(self, mock_get_llm):
        from backend.pipeline.agent_quiz import quiz_generate_node

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _make_llm_response(_make_questions(10))
        mock_get_llm.return_value = mock_llm

        state = _make_state()
        result = quiz_generate_node(state)

        assert "questions" in result
        assert isinstance(result["questions"], list)

    @patch("backend.pipeline.agent_quiz.get_llm")
    def test_question_count_matches_request(self, mock_get_llm):
        from backend.pipeline.agent_quiz import quiz_generate_node

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _make_llm_response(_make_questions(10))
        mock_get_llm.return_value = mock_llm

        state = _make_state(question_count=10)
        result = quiz_generate_node(state)

        assert len(result["questions"]) == 10

    @patch("backend.pipeline.agent_quiz.get_llm")
    def test_questions_have_required_fields(self, mock_get_llm):
        from backend.pipeline.agent_quiz import quiz_generate_node

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _make_llm_response(_make_questions(5))
        mock_get_llm.return_value = mock_llm

        state = _make_state(question_count=5)
        result = quiz_generate_node(state)

        required = {
            "question_text", "question_type", "options", "correct_index",
            "difficulty", "blooms_level", "source_section",
            "feedback_correct", "feedback_incorrect", "topic",
        }
        for q in result["questions"]:
            assert required.issubset(q.keys()), f"Missing fields: {required - set(q.keys())}"

    @patch("backend.pipeline.agent_quiz.get_llm")
    def test_uses_mini_model(self, mock_get_llm):
        from backend.pipeline.agent_quiz import quiz_generate_node

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _make_llm_response(_make_questions(5))
        mock_get_llm.return_value = mock_llm

        state = _make_state(question_count=5)
        quiz_generate_node(state)

        mock_get_llm.assert_called_with("mini")

    @patch("backend.pipeline.agent_quiz.get_llm")
    def test_handles_multiple_topics(self, mock_get_llm):
        from backend.pipeline.agent_quiz import quiz_generate_node

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _make_llm_response(_make_questions(5))
        mock_get_llm.return_value = mock_llm

        state = _make_state(
            topics=[
                {"name": "Topic A", "description": "Desc A", "key_techniques": [], "domain_context": "NLP"},
                {"name": "Topic B", "description": "Desc B", "key_techniques": [], "domain_context": "NLP"},
            ],
            modules_md=["# Topic A\n\nContent A", "# Topic B\n\nContent B"],
            gap_summary=[
                {"topic": "Topic A", "gaps": ["gap1"], "enrichments": []},
                {"topic": "Topic B", "gaps": ["gap2"], "enrichments": []},
            ],
            question_count=10,
        )
        result = quiz_generate_node(state)

        assert len(result["questions"]) == 10

    @patch("backend.pipeline.agent_quiz.get_llm")
    def test_handles_llm_json_parse_error(self, mock_get_llm):
        from backend.pipeline.agent_quiz import quiz_generate_node

        mock_llm = MagicMock()
        # First call returns invalid JSON, second returns valid
        bad_resp = MagicMock()
        bad_resp.content = "not valid json {{"
        good_resp = _make_llm_response(_make_questions(5))
        mock_llm.invoke.side_effect = [bad_resp, good_resp]
        mock_get_llm.return_value = mock_llm

        state = _make_state(question_count=5)
        result = quiz_generate_node(state)

        assert "questions" in result
        assert len(result["questions"]) > 0

    @patch("backend.pipeline.agent_quiz.get_llm")
    def test_single_topic(self, mock_get_llm):
        from backend.pipeline.agent_quiz import quiz_generate_node

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _make_llm_response(_make_questions(5))
        mock_get_llm.return_value = mock_llm

        state = _make_state(question_count=5)
        result = quiz_generate_node(state)

        assert len(result["questions"]) == 5


# ---------------------------------------------------------------------------
# Quiz graph tests
# ---------------------------------------------------------------------------


class TestQuizGraph:
    """Test the LangGraph quiz workflow."""

    def test_graph_compiles(self):
        from backend.pipeline.quiz_graph import build_quiz_graph

        graph = build_quiz_graph()
        assert graph is not None

    @patch("backend.pipeline.agent_quiz.get_llm")
    def test_graph_invocation_returns_questions(self, mock_get_llm):
        from backend.pipeline.quiz_graph import build_quiz_graph

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _make_llm_response(_make_questions(5))
        mock_get_llm.return_value = mock_llm

        graph = build_quiz_graph()
        state = _make_state(question_count=5)
        result = graph.invoke(state)

        assert "questions" in result
        assert len(result["questions"]) == 5
