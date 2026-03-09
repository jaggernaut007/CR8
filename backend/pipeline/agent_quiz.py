"""Quiz generation agent for the CR8 on-demand quiz workflow.

Generates structured MCQ questions from completed pipeline output
(modules_md, gap_summary, topics). Called as a LangGraph node via
quiz_graph.py, NOT as part of the main pipeline.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from backend.prompts.quiz import QUIZ_GENERATE_PROMPT
from backend.pipeline.quiz_state import QuizState
from backend.services.llm import get_llm

logger = logging.getLogger(__name__)

_REQUIRED_FIELDS = {
    "question_text", "question_type", "options", "correct_index",
    "difficulty", "blooms_level", "source_section",
    "feedback_correct", "feedback_incorrect", "topic",
}
_VALID_DIFFICULTIES = {"easy", "medium", "hard"}
_VALID_BLOOMS = {"remember", "understand", "apply", "analyze", "evaluate", "create"}
_MAX_RETRIES = 2
_MIN_GAP_PERCENTAGE = 40.0
_OPTIONS_PER_QUESTION = 4
_MAX_CORRECT_INDEX = 3


# ---------------------------------------------------------------------------
# Public node function
# ---------------------------------------------------------------------------


def quiz_generate_node(state: QuizState) -> dict[str, Any]:
    """Generate MCQ questions from pipeline output.

    Args:
        state: QuizState with topics, modules_md, gap_summary, etc.

    Returns:
        Dict with ``questions`` key containing validated question dicts.
    """
    topics = state["topics"]
    modules_md = state.get("modules_md", [])
    gap_summary = state.get("gap_summary", [])
    curriculum_scope = state.get("curriculum_scope", "General")
    total_count = state.get("question_count", 20)

    logger.info(
        "Starting quiz generation: topics=%d, target_questions=%d",
        len(topics), total_count,
    )

    llm = get_llm("mini")
    ctx = {
        "modules_md": modules_md,
        "gap_summary": gap_summary,
        "curriculum_scope": curriculum_scope,
        "llm": llm,
    }
    all_questions = _generate_all_topics(topics, total_count, ctx)

    # Enforce difficulty distribution
    all_questions = _enforce_difficulty_distribution(all_questions, total_count)

    # Verify gap targeting meets 40% threshold
    gap_topics = [g.get("concept", "") for g in gap_summary if isinstance(g, dict)]
    gap_pct = _calculate_gap_percentage(all_questions, gap_topics)
    if gap_pct < _MIN_GAP_PERCENTAGE:
        logger.warning(
            "Gap targeting below 40%% threshold: %.1f%% (%d questions)",
            gap_pct, len(all_questions),
        )

    # Assign sort order
    for i, q in enumerate(all_questions):
        q["sort_order"] = i

    logger.info("Quiz generation complete: %d questions produced", len(all_questions))
    return {"questions": all_questions}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _generate_all_topics(
    topics: list[dict],
    total_count: int,
    ctx: dict[str, Any],
) -> list[dict]:
    """Generate questions across all topics proportionally.

    Args:
        topics: Topic dicts from pipeline state.
        total_count: Total target question count.
        ctx: Context dict with modules_md, gap_summary, curriculum_scope, llm.

    Returns:
        Combined list of validated question dicts.
    """
    modules_md = ctx["modules_md"]
    gap_summary = ctx["gap_summary"]
    per_topic_counts = _distribute_counts(len(topics), total_count)
    gap_map = {g["topic"]: g for g in gap_summary}
    all_questions: list[dict] = []

    for i, topic in enumerate(topics):
        module_md = modules_md[i] if i < len(modules_md) else ""
        gap_data = gap_map.get(topic["name"], {})
        count = per_topic_counts[i]

        questions = _generate_topic_questions(
            topic, module_md, gap_data, ctx,  count,
        )
        all_questions.extend(questions)

    return all_questions[:total_count]


def _distribute_counts(num_topics: int, total: int) -> list[int]:
    """Distribute total question count across topics proportionally.

    Args:
        num_topics: Number of topics.
        total: Total question count.

    Returns:
        List of per-topic counts that sum to total.
    """
    if num_topics == 0:
        return []
    base = total // num_topics
    remainder = total % num_topics
    counts = [base] * num_topics
    for i in range(remainder):
        counts[i] += 1
    return counts


def _generate_topic_questions(
    topic: dict,
    module_md: str,
    gap_data: dict,
    ctx: dict[str, Any],
    count: int,
) -> list[dict]:
    """Generate questions for a single topic with retry on failure.

    Args:
        topic: Topic dict with name, description, etc.
        module_md: Module markdown content.
        gap_data: Gap analysis dict for this topic.
        ctx: Context dict with curriculum_scope and llm.
        count: Number of questions to generate.

    Returns:
        List of validated question dicts.
    """
    topic_name = topic.get("name", "Unknown")
    gap_text = json.dumps(gap_data, indent=2) if gap_data else "No gaps identified."
    logger.info("Generating %d questions for topic: %s", count, topic_name)

    prompt = QUIZ_GENERATE_PROMPT.format(
        topic_name=topic_name,
        module_content=module_md[:4000],
        gap_analysis=gap_text,
        curriculum_scope=ctx["curriculum_scope"],
        question_count=count,
    )

    llm = ctx["llm"]
    for attempt in range(_MAX_RETRIES + 1):
        questions = _invoke_and_parse(llm, prompt, topic_name, attempt)
        if questions is not None:
            validated = _filter_valid_questions(questions, topic_name)
            if validated:
                return validated[:count]

    logger.warning("All retries exhausted for topic: %s", topic_name)
    return []


def _invoke_and_parse(
    llm: Any, prompt: str, topic_name: str, attempt: int,
) -> list[dict] | None:
    """Invoke LLM and parse JSON response.

    Args:
        llm: LLM instance.
        prompt: Formatted prompt string.
        topic_name: For logging context.
        attempt: Current attempt number.

    Returns:
        Parsed question list or None on failure.
    """
    try:
        response = llm.invoke(
            prompt,
            config={"run_name": f"quiz_generate_{topic_name}"},
            response_format={"type": "json_object"},
        )
        data = json.loads(response.content)
        return data.get("questions", [])
    except (json.JSONDecodeError, KeyError, AttributeError):
        logger.warning(
            "JSON parse failed for topic %s (attempt %d/%d)",
            topic_name, attempt + 1, _MAX_RETRIES + 1,
        )
        return None


def _filter_valid_questions(
    questions: list[dict], topic_name: str,
) -> list[dict]:
    """Filter out invalid questions, logging issues.

    Args:
        questions: Raw question dicts from LLM.
        topic_name: For logging context.

    Returns:
        List of valid question dicts only.
    """
    valid = []
    for i, q in enumerate(questions):
        is_valid, errors = _validate_question(q)
        if is_valid:
            valid.append(q)
        else:
            logger.warning(
                "Invalid question %d for %s: %s", i, topic_name, "; ".join(errors),
            )
    return valid


def _validate_question(question: dict) -> tuple[bool, list[str]]:
    """Validate a single question dict has all required fields and valid values.

    Args:
        question: Question dict to validate.

    Returns:
        Tuple of (is_valid, list_of_error_messages).
    """
    errors: list[str] = []

    for field in _REQUIRED_FIELDS:
        if field not in question:
            errors.append(f"Missing required field: {field}")

    if "options" in question and len(question["options"]) != _OPTIONS_PER_QUESTION:
        errors.append(f"Must have exactly 4 options, got {len(question['options'])}")

    if "correct_index" in question:
        idx = question["correct_index"]
        if not isinstance(idx, int) or idx < 0 or idx > _MAX_CORRECT_INDEX:
            errors.append(f"correct_index must be 0-3, got {idx}")

    if "difficulty" in question and question["difficulty"] not in _VALID_DIFFICULTIES:
        errors.append(f"Invalid difficulty: {question['difficulty']}")

    if "blooms_level" in question and question["blooms_level"] not in _VALID_BLOOMS:
        errors.append(f"Invalid blooms_level: {question['blooms_level']}")

    return len(errors) == 0, errors


def _enforce_difficulty_distribution(
    questions: list[dict], total: int,
) -> list[dict]:
    """Enforce 30/50/20 difficulty distribution by reassigning difficulty labels.

    Args:
        questions: Question dicts to adjust.
        total: Target total question count.

    Returns:
        Questions with adjusted difficulty values.
    """
    target_easy = round(total * 0.3)
    target_hard = round(total * 0.2)
    target_medium = total - target_easy - target_hard

    result = list(questions[:total])

    for i, q in enumerate(result):
        if i < target_easy:
            q["difficulty"] = "easy"
        elif i < target_easy + target_medium:
            q["difficulty"] = "medium"
        else:
            q["difficulty"] = "hard"

    return result


def _calculate_gap_percentage(
    questions: list[dict], gap_topics: list[str],
) -> float:
    """Calculate the percentage of questions that target knowledge gaps.

    Args:
        questions: Question dicts with source_section field.
        gap_topics: List of gap topic/concept strings to match against.

    Returns:
        Percentage (0-100) of questions targeting gaps.
    """
    if not questions:
        return 0.0

    gap_count = 0
    gap_lower = {g.lower() for g in gap_topics}

    for q in questions:
        source = q.get("source_section", "").lower()
        if "gap" in source or any(g in source for g in gap_lower):
            gap_count += 1

    return (gap_count / len(questions)) * 100.0
