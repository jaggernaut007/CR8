"""Layer 1 structural checks for generated learning modules."""

from __future__ import annotations

import re

_MIN_MODULE_CHARS = 2000

_REQUIRED_SECTIONS = [
    "## Module Overview",
    "## Learning Objectives",
    "## Curriculum Coverage",
    "## Identified Gaps",
    "## Core Content",
    "## Industry Context",
    "## Practice & Review",
    "## Key Takeaways",
    "## Reflection",
]

_BLOOMS_VERBS = [
    "explain", "implement", "compare", "evaluate", "analyze",
    "apply", "create", "describe", "identify", "design", "assess",
]


def run_all(module_md: str) -> dict[str, bool]:
    """Run all structural checks. Returns {check_name: pass/fail}."""
    return {
        "has_all_sections": has_all_sections(module_md),
        "sections_in_order": sections_in_order(module_md),
        "min_length": min_length(module_md),
        "has_blooms_verbs": has_blooms_verbs(module_md),
        "has_curriculum_gap_tags": has_curriculum_gap_tags(module_md),
        "has_quick_check_answers": has_quick_check_answers(module_md),
        "has_takeaway_prefixes": has_takeaway_prefixes(module_md),
        "core_content_has_subheadings": core_content_has_subheadings(module_md),
    }


def has_all_sections(module_md: str) -> bool:
    return all(section in module_md for section in _REQUIRED_SECTIONS)


def sections_in_order(module_md: str) -> bool:
    positions = []
    for section in _REQUIRED_SECTIONS:
        pos = module_md.find(section)
        if pos == -1:
            return False
        positions.append(pos)
    return positions == sorted(positions)


def min_length(module_md: str) -> bool:
    return len(module_md) >= _MIN_MODULE_CHARS


def has_blooms_verbs(module_md: str) -> bool:
    objectives = _extract_section(module_md, "## Learning Objectives")
    if not objectives:
        return False
    lower = objectives.lower()
    return any(verb in lower for verb in _BLOOMS_VERBS)


def has_curriculum_gap_tags(module_md: str) -> bool:
    objectives = _extract_section(module_md, "## Learning Objectives")
    if not objectives:
        return False
    return "(Curriculum)" in objectives and "(Gap)" in objectives


def has_quick_check_answers(module_md: str) -> bool:
    practice = _extract_section(module_md, "## Practice & Review")
    if not practice:
        return False
    return "> Answer:" in practice or "> answer:" in practice.lower()


def has_takeaway_prefixes(module_md: str) -> bool:
    takeaways = _extract_section(module_md, "## Key Takeaways")
    if not takeaways:
        return False
    lower = takeaways.lower()
    return "curriculum:" in lower and "gap:" in lower


def core_content_has_subheadings(module_md: str) -> bool:
    core = _extract_section(module_md, "## Core Content")
    if not core:
        return False
    return "###" in core


def _extract_section(module_md: str, header: str) -> str:
    """Extract text between a ## header and the next ## header."""
    pattern = re.escape(header) + r"\n(.*?)(?=\n## |\Z)"
    match = re.search(pattern, module_md, re.DOTALL)
    return match.group(1) if match else ""
