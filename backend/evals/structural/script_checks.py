"""Layer 1 structural checks for video scripts."""

from __future__ import annotations

import re

_MIN_WORDS = 300
_MAX_WORDS = 750
_MAX_CHARS = 3800

_CONTRACTIONS_ASCII = ["you'll", "it's", "here's", "that's", "don't", "won't", "can't", "we'll", "they're"]
# Also check with Unicode smart quotes (U+2019) which GPT often produces
_CONTRACTIONS = _CONTRACTIONS_ASCII + [c.replace("'", "\u2019") for c in _CONTRACTIONS_ASCII]

_MARKDOWN_PATTERNS = [
    r"^#{1,6}\s",       # headings
    r"\*\*[^*]+\*\*",   # bold
    r"^\s*[-*]\s",       # bullet points
    r"\[.+\]\(.+\)",    # markdown links
]

_SECTION_LABELS = [
    r"(?i)\bsection\s*\d",
    r"(?i)\bhook\s*:",
    r"(?i)\banchor\s*:",
    r"(?i)\btakeaway[s]?\s*:",
    r"(?i)\bmisconception\s*:",
    r"(?i)\bretrieval\s*:",
]

_STAGE_DIRECTIONS = [
    r"\[pause\]",
    r"\[slide\]",
    r"\[.*?\]",    # any bracketed stage direction
]


def run_all(script: str) -> dict[str, bool]:
    """Run all structural checks. Returns {check_name: pass/fail}."""
    return {
        "word_count_in_range": word_count_in_range(script),
        "char_count_under_limit": char_count_under_limit(script),
        "no_markdown": no_markdown(script),
        "no_section_labels": no_section_labels(script),
        "has_question_mark": has_question_mark(script),
        "uses_contractions": uses_contractions(script),
        "no_stage_directions": no_stage_directions(script),
    }


def word_count_in_range(script: str) -> bool:
    wc = len(script.split())
    return _MIN_WORDS <= wc <= _MAX_WORDS


def char_count_under_limit(script: str) -> bool:
    return len(script) < _MAX_CHARS


def no_markdown(script: str) -> bool:
    for pattern in _MARKDOWN_PATTERNS:
        if re.search(pattern, script, re.MULTILINE):
            return False
    return True


def no_section_labels(script: str) -> bool:
    for pattern in _SECTION_LABELS:
        if re.search(pattern, script):
            return False
    return True


def has_question_mark(script: str) -> bool:
    return "?" in script


def uses_contractions(script: str) -> bool:
    lower = script.lower()
    return any(c in lower for c in _CONTRACTIONS)


def no_stage_directions(script: str) -> bool:
    for pattern in _STAGE_DIRECTIONS:
        if re.search(pattern, script, re.IGNORECASE):
            return False
    return True
