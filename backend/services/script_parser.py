"""Parse video scripts with [SLIDE N] markers into structured segments.

Usage:
    from backend.services.script_parser import parse_script

    segments = parse_script(script_text)
    # [{"slide_num": 1, "text": "Welcome to..."}, {"slide_num": 2, "text": "Next..."}]
"""

import logging
import re

logger = logging.getLogger(__name__)

try:
    from langsmith import traceable
except ImportError:  # pragma: no cover
    def traceable(**kwargs):
        def decorator(func):
            return func
        return decorator

_SLIDE_MARKER = re.compile(r"^\[SLIDE\s+(\d+)\]\s*$", re.MULTILINE)


def distribute_script(script_text: str, num_slides: int) -> list[dict]:
    """Distribute unmarked script text across *num_slides* slides.

    Splits on paragraph boundaries (``\\n\\n``) and groups paragraphs so
    that each slide gets a roughly equal share of the total text by
    character count.

    Args:
        script_text: Continuous script text (no ``[SLIDE N]`` markers).
        num_slides: Number of slides to distribute across.

    Returns:
        List of dicts with ``slide_num`` (1-based) and ``text``.

    Raises:
        ValueError: If *script_text* is empty or whitespace-only.
    """
    if not script_text or not script_text.strip():
        raise ValueError("Script text is empty")

    if num_slides <= 1:
        return [{"slide_num": 1, "text": script_text.strip()}]

    paragraphs = [p.strip() for p in script_text.split("\n\n") if p.strip()]

    if not paragraphs:
        return [{"slide_num": 1, "text": script_text.strip()}]

    if len(paragraphs) <= num_slides:
        # Fewer paragraphs than slides — one paragraph per slide, last slide
        # gets any remainder.
        segments = []
        for i, para in enumerate(paragraphs):
            segments.append({"slide_num": i + 1, "text": para})
        # Fill remaining slides with last paragraph
        for i in range(len(paragraphs), num_slides):
            segments.append({"slide_num": i + 1, "text": paragraphs[-1]})
        return segments

    # Distribute paragraphs proportionally by character count
    total_chars = sum(len(p) for p in paragraphs)
    target_per_slide = total_chars / num_slides

    segments: list[dict] = []
    current_parts: list[str] = []
    current_chars = 0
    slide_idx = 0
    remaining_paras = len(paragraphs)

    for para in paragraphs:
        current_parts.append(para)
        current_chars += len(para)
        remaining_paras -= 1
        remaining_slides = num_slides - slide_idx - 1

        # Flush this slide if we've hit the target and there are enough
        # paragraphs left for the remaining slides.
        if (remaining_slides > 0
                and current_chars >= target_per_slide
                and remaining_paras >= remaining_slides):
            segments.append({
                "slide_num": slide_idx + 1,
                "text": "\n\n".join(current_parts),
            })
            current_parts = []
            current_chars = 0
            slide_idx += 1

    # Flush remaining text
    if current_parts:
        segments.append({
            "slide_num": slide_idx + 1,
            "text": "\n\n".join(current_parts),
        })

    return segments


@traceable(run_type="parser", name="parse_script")
def parse_script(script_text: str, num_slides: int = 0) -> list[dict]:
    """Parse a script with [SLIDE N] markers into segments.

    Args:
        script_text: Full script text with ``[SLIDE N]`` markers separating
            segments.  If no markers are present and *num_slides* > 1, the
            text is distributed across that many slides by paragraph
            boundaries.  Otherwise the entire text is returned as a single
            segment with ``slide_num=1``.
        num_slides: When positive and no markers are found, distribute the
            text across this many slides.  Defaults to 0 (single-segment
            fallback for backward compatibility).

    Returns:
        List of dicts, each with ``slide_num`` (int) and ``text`` (str).
        Empty or whitespace-only segments are skipped.

    Raises:
        ValueError: If *script_text* is empty or whitespace-only.
    """
    if not script_text or not script_text.strip():
        raise ValueError("Script text is empty")

    markers = list(_SLIDE_MARKER.finditer(script_text))

    if not markers:
        if num_slides > 1:
            logger.info("No [SLIDE N] markers — distributing across %d slides", num_slides)
            return distribute_script(script_text, num_slides)
        logger.warning("No [SLIDE N] markers found — treating entire text as slide 1")
        return [{"slide_num": 1, "text": script_text.strip()}]

    segments: list[dict] = []

    # Text before the first marker (if any)
    pre_text = script_text[: markers[0].start()].strip()
    if pre_text:
        segments.append({"slide_num": 1, "text": pre_text})

    for i, match in enumerate(markers):
        slide_num = int(match.group(1))
        start = match.end()
        end = markers[i + 1].start() if i + 1 < len(markers) else len(script_text)
        text = script_text[start:end].strip()
        if text:
            segments.append({"slide_num": slide_num, "text": text})

    logger.info("Parsed %d segments from %d [SLIDE] markers", len(segments), len(markers))
    return segments
