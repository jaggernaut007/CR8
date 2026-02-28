"""Layer 1 structural checks for PPT slide structure JSON.

Handles both formats:
  - Full presentation: {"presentation_title", "executive_summary", "topic_slides"}
  - Single topic slide: {"topic_name", "slide_title", "severity", "gap_concepts"}

Accepts both old field names (severity, gap_concepts) and new field names
(importance, concepts) for backwards compatibility.
"""

from __future__ import annotations

import json

_VALID_SEVERITIES = {"critical", "moderate", "minor"}
_VALID_DIAGRAM_TYPES = {"process_flow", "comparison", "concept_map", "none"}

_REQUIRED_SLIDE_KEYS = {
    "topic_name", "slide_title",
}


def run_all(ppt_json_str: str, expected_topic_count: int | None = None) -> dict[str, bool]:
    """Run all structural checks. Returns {check_name: pass/fail}."""
    parsed = _try_parse(ppt_json_str)
    if parsed is None:
        return {k: False for k in [
            "valid_json", "schema_complete",
            "severity_valid", "diagram_data_valid", "assertion_titles",
        ]}

    # Detect format: full presentation or single topic slide
    is_full = "topic_slides" in parsed
    slides = parsed.get("topic_slides", [parsed]) if is_full else [parsed]

    results = {
        "valid_json": True,
        "schema_complete": _schema_complete(slides),
        "severity_valid": _severity_valid(slides),
        "diagram_data_valid": _diagram_data_valid(slides),
        "assertion_titles": _assertion_titles(slides),
    }
    if expected_topic_count is not None and is_full:
        results["slide_count_matches"] = len(slides) == expected_topic_count
    if is_full:
        results["topic_scores_complete"] = _topic_scores_complete(parsed)
    return results


def _try_parse(ppt_json_str: str) -> dict | None:
    try:
        return json.loads(ppt_json_str) if isinstance(ppt_json_str, str) else ppt_json_str
    except (json.JSONDecodeError, TypeError):
        return None


def _schema_complete(slides: list[dict]) -> bool:
    for slide in slides:
        if not _REQUIRED_SLIDE_KEYS.issubset(slide.keys()):
            return False
        # Must have either gap_concepts or concepts
        if "gap_concepts" not in slide and "concepts" not in slide:
            return False
        # Must have either severity or importance
        if "severity" not in slide and "importance" not in slide:
            return False
    return True


def _severity_valid(slides: list[dict]) -> bool:
    for slide in slides:
        sev = slide.get("severity", slide.get("importance", ""))
        if sev not in _VALID_SEVERITIES:
            return False
    return True


def _diagram_data_valid(slides: list[dict]) -> bool:
    for slide in slides:
        concepts = slide.get("gap_concepts", slide.get("concepts", []))
        for concept in concepts:
            dtype = concept.get("diagram_type", "none")
            if dtype not in _VALID_DIAGRAM_TYPES:
                return False
            if dtype != "none":
                nodes = concept.get("diagram_data", {}).get("nodes", [])
                if not (3 <= len(nodes) <= 6):
                    return False
    return True


def _assertion_titles(slides: list[dict]) -> bool:
    """Heuristic: assertion titles should contain >= 5 words."""
    for slide in slides:
        title = slide.get("slide_title", "")
        words = title.split()
        if len(words) < 5:
            return False
    return True


def _topic_scores_complete(data: dict) -> bool:
    scores = data.get("executive_summary", {}).get("topic_scores", [])
    if not scores:
        return False
    for entry in scores:
        cs = entry.get("curriculum_score")
        ir = entry.get("industry_requirement")
        if not isinstance(cs, (int, float)) or not isinstance(ir, (int, float)):
            return False
        if not (0 <= cs <= 100) or not (0 <= ir <= 100):
            return False
    return True
