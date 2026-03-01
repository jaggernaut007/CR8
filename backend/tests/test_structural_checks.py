"""Tests for all three Layer 1 structural check modules.

Covers pure functions in:
  - backend.evals.structural.module_checks
  - backend.evals.structural.script_checks
  - backend.evals.structural.ppt_checks
  - backend.pipeline.agent_ingest._sanitize (property-based)
"""

from __future__ import annotations

import json

import pytest
from hypothesis import given, settings as hyp_settings
from hypothesis import strategies as st


# ===========================================================================
# Module Checks
# ===========================================================================


class TestModuleChecks:
    """Tests for module_checks.run_all() and individual checks."""

    def test_valid_module_passes_all(self, valid_module_md):
        from backend.evals.structural.module_checks import run_all

        results = run_all(valid_module_md)
        failed = {k: v for k, v in results.items() if not v}
        assert failed == {}, f"Expected all checks to pass, but these failed: {failed}"

    def test_missing_section_fails_has_all_sections(self, valid_module_md):
        from backend.evals.structural.module_checks import has_all_sections

        broken = valid_module_md.replace("## Reflection", "## Refection_TYPO")
        assert not has_all_sections(broken)

    def test_wrong_order_fails_sections_in_order(self, valid_module_md):
        from backend.evals.structural.module_checks import sections_in_order

        # Swap Core Content and Key Takeaways to break ordering
        swapped = valid_module_md.replace(
            "## Key Takeaways", "##PLACEHOLDER##"
        ).replace(
            "## Core Content", "## Key Takeaways"
        ).replace(
            "##PLACEHOLDER##", "## Core Content"
        )
        assert not sections_in_order(swapped)

    def test_short_module_fails_min_length(self):
        from backend.evals.structural.module_checks import min_length

        short = "a" * 1999
        assert not min_length(short)

    def test_exactly_at_min_length_passes(self):
        from backend.evals.structural.module_checks import min_length

        assert min_length("a" * 2000)

    def test_blooms_verb_detected(self):
        from backend.evals.structural.module_checks import has_blooms_verbs

        md = "## Learning Objectives\n- Explain how attention works\n"
        assert has_blooms_verbs(md)

    def test_missing_blooms_fails(self):
        from backend.evals.structural.module_checks import has_blooms_verbs

        md = "## Learning Objectives\n- Overview of attention mechanisms\n"
        assert not has_blooms_verbs(md)

    def test_curriculum_gap_tags_detected(self):
        from backend.evals.structural.module_checks import has_curriculum_gap_tags

        md = "## Learning Objectives\n- Learn transformers (Curriculum)\n- Apply BERT (Gap)\n"
        assert has_curriculum_gap_tags(md)

    def test_missing_gap_tag_fails(self):
        from backend.evals.structural.module_checks import has_curriculum_gap_tags

        md = "## Learning Objectives\n- Learn transformers (Curriculum)\n"
        assert not has_curriculum_gap_tags(md)

    def test_missing_curriculum_tag_fails(self):
        from backend.evals.structural.module_checks import has_curriculum_gap_tags

        md = "## Learning Objectives\n- Apply BERT (Gap)\n"
        assert not has_curriculum_gap_tags(md)

    def test_answer_prefix_detected(self):
        from backend.evals.structural.module_checks import has_quick_check_answers

        md = "## Practice & Review\nQ: What is attention?\n> Answer: A weighted combination.\n"
        assert has_quick_check_answers(md)

    def test_missing_answer_fails(self):
        from backend.evals.structural.module_checks import has_quick_check_answers

        md = "## Practice & Review\nQ: What is attention?\nSome answer without the prefix.\n"
        assert not has_quick_check_answers(md)

    def test_takeaway_prefixes_detected(self, valid_module_md):
        from backend.evals.structural.module_checks import has_takeaway_prefixes

        assert has_takeaway_prefixes(valid_module_md)

    def test_missing_takeaway_curriculum_prefix_fails(self):
        from backend.evals.structural.module_checks import has_takeaway_prefixes

        md = "## Key Takeaways\ngap: transformers are deployed at scale\n"
        assert not has_takeaway_prefixes(md)

    def test_subheadings_in_core_content(self, valid_module_md):
        from backend.evals.structural.module_checks import core_content_has_subheadings

        assert core_content_has_subheadings(valid_module_md)

    def test_missing_subheadings_fails(self):
        from backend.evals.structural.module_checks import core_content_has_subheadings

        md = "## Core Content\nSome content without any level-3 headings.\n"
        assert not core_content_has_subheadings(md)

    def test_run_all_returns_all_keys(self, valid_module_md):
        from backend.evals.structural.module_checks import run_all

        results = run_all(valid_module_md)
        expected_keys = {
            "has_all_sections",
            "sections_in_order",
            "min_length",
            "has_blooms_verbs",
            "has_curriculum_gap_tags",
            "has_quick_check_answers",
            "has_takeaway_prefixes",
            "core_content_has_subheadings",
        }
        assert set(results.keys()) == expected_keys


class TestModuleChecksPropertyBased:
    """Property-based tests for pure module check functions."""

    @given(st.text(max_size=1999))
    def test_any_string_shorter_than_2000_fails_min_length(self, text):
        from backend.evals.structural.module_checks import min_length

        assert not min_length(text)

    @given(st.text(min_size=2000))
    def test_any_string_2000_or_longer_passes_min_length(self, text):
        from backend.evals.structural.module_checks import min_length

        assert min_length(text)


# ===========================================================================
# Script Checks
# ===========================================================================


class TestScriptChecks:
    """Tests for script_checks.run_all() and individual checks."""

    def test_valid_script_passes_all(self, valid_script):
        from backend.evals.structural.script_checks import run_all

        results = run_all(valid_script)
        failed = {k: v for k, v in results.items() if not v}
        assert failed == {}, f"Expected all checks to pass, but these failed: {failed}"

    def test_too_few_words_fails(self):
        from backend.evals.structural.script_checks import word_count_in_range

        short = "word " * 200
        assert not word_count_in_range(short)

    def test_too_many_words_fails(self):
        from backend.evals.structural.script_checks import word_count_in_range

        long = "word " * 800
        assert not word_count_in_range(long)

    def test_in_range_words_passes(self):
        from backend.evals.structural.script_checks import word_count_in_range

        mid = "word " * 500
        assert word_count_in_range(mid)

    def test_char_limit_exceeded_fails(self):
        from backend.evals.structural.script_checks import char_count_under_limit

        over_limit = "a" * 3801
        assert not char_count_under_limit(over_limit)

    def test_char_limit_exactly_at_boundary_passes(self):
        from backend.evals.structural.script_checks import char_count_under_limit

        at_limit = "a" * 3799
        assert char_count_under_limit(at_limit)

    def test_markdown_header_fails(self):
        from backend.evals.structural.script_checks import no_markdown

        assert not no_markdown("# This is a heading\nSome content here.")

    def test_markdown_bold_fails(self):
        from backend.evals.structural.script_checks import no_markdown

        assert not no_markdown("This is **bold text** in a sentence.")

    def test_markdown_bullet_fails(self):
        from backend.evals.structural.script_checks import no_markdown

        assert not no_markdown("Some text.\n- bullet point\nMore text.")

    def test_markdown_link_fails(self):
        from backend.evals.structural.script_checks import no_markdown

        assert not no_markdown("Check out [this link](https://example.com) for more.")

    def test_plain_prose_passes_no_markdown(self):
        from backend.evals.structural.script_checks import no_markdown

        assert no_markdown("This is plain prose with no formatting at all.")

    def test_section_label_section_fails(self):
        from backend.evals.structural.script_checks import no_section_labels

        assert not no_section_labels("Section 1: Introduction to Transformers")

    def test_section_label_hook_fails(self):
        from backend.evals.structural.script_checks import no_section_labels

        assert not no_section_labels("Hook: Did you know that attention is all you need?")

    def test_section_label_anchor_fails(self):
        from backend.evals.structural.script_checks import no_section_labels

        assert not no_section_labels("Anchor: Let me tell you about self-attention.")

    def test_section_label_takeaway_fails(self):
        from backend.evals.structural.script_checks import no_section_labels

        assert not no_section_labels("Takeaway: Transformers use self-attention.")

    def test_clean_prose_passes_no_section_labels(self):
        from backend.evals.structural.script_checks import no_section_labels

        assert no_section_labels("Today we explore how neural networks process language.")

    def test_question_mark_detected(self):
        from backend.evals.structural.script_checks import has_question_mark

        assert has_question_mark("Have you ever wondered how this works?")

    def test_missing_question_mark_fails(self):
        from backend.evals.structural.script_checks import has_question_mark

        assert not has_question_mark("This script has no questions at all.")

    def test_contractions_ascii_apostrophe(self):
        from backend.evals.structural.script_checks import uses_contractions

        assert uses_contractions("You'll learn a lot in this lecture.")

    def test_contractions_unicode_smart_quote(self):
        from backend.evals.structural.script_checks import uses_contractions

        # U+2019 right single quotation mark — GPT commonly produces this
        assert uses_contractions("You\u2019ll find this fascinating.")

    def test_its_contraction_ascii(self):
        from backend.evals.structural.script_checks import uses_contractions

        assert uses_contractions("It's a remarkable achievement.")

    def test_no_contractions_fails(self):
        from backend.evals.structural.script_checks import uses_contractions

        assert not uses_contractions("The mechanism is very useful for processing sequences.")

    def test_stage_direction_pause_fails(self):
        from backend.evals.structural.script_checks import no_stage_directions

        assert not no_stage_directions("This is interesting [pause] and important.")

    def test_stage_direction_slide_fails(self):
        from backend.evals.structural.script_checks import no_stage_directions

        assert not no_stage_directions("Now let's look at [slide] the next concept.")

    def test_any_bracketed_text_fails(self):
        from backend.evals.structural.script_checks import no_stage_directions

        assert not no_stage_directions("Here we see [cut to animation] something interesting.")

    def test_clean_script_passes_no_stage_directions(self):
        from backend.evals.structural.script_checks import no_stage_directions

        assert no_stage_directions("This is a clean script with no stage directions.")

    def test_run_all_returns_all_keys(self, valid_script):
        from backend.evals.structural.script_checks import run_all

        results = run_all(valid_script)
        expected_keys = {
            "word_count_in_range",
            "char_count_under_limit",
            "no_markdown",
            "no_section_labels",
            "has_question_mark",
            "uses_contractions",
            "no_stage_directions",
        }
        assert set(results.keys()) == expected_keys


# ===========================================================================
# PPT Checks
# ===========================================================================


class TestPptChecks:
    """Tests for ppt_checks.run_all() and individual checks."""

    def test_valid_single_slide_passes(self, valid_ppt_single):
        from backend.evals.structural.ppt_checks import run_all

        results = run_all(valid_ppt_single)
        failed = {k: v for k, v in results.items() if not v}
        assert failed == {}, f"Expected all checks to pass, but these failed: {failed}"

    def test_valid_full_presentation_passes(self, valid_ppt_full):
        from backend.evals.structural.ppt_checks import run_all

        results = run_all(valid_ppt_full)
        failed = {k: v for k, v in results.items() if not v}
        assert failed == {}, f"Expected all checks to pass, but these failed: {failed}"

    def test_invalid_json_fails_all(self):
        from backend.evals.structural.ppt_checks import run_all

        results = run_all("this is not valid JSON {{{")
        assert all(not v for v in results.values())

    def test_missing_topic_name_fails_schema(self):
        from backend.evals.structural.ppt_checks import run_all

        slide = {
            "slide_title": "A title with five or more words here",
            "severity": "critical",
            "gap_concepts": [],
        }
        results = run_all(json.dumps(slide))
        assert not results["schema_complete"]

    def test_missing_gap_concepts_and_concepts_fails_schema(self):
        from backend.evals.structural.ppt_checks import run_all

        slide = {
            "topic_name": "Transformers",
            "slide_title": "A title with five or more words here",
            "severity": "critical",
            # neither gap_concepts nor concepts
        }
        results = run_all(json.dumps(slide))
        assert not results["schema_complete"]

    def test_invalid_severity_fails(self):
        from backend.evals.structural.ppt_checks import run_all

        slide = {
            "topic_name": "Transformers",
            "slide_title": "A title with five or more words here",
            "severity": "catastrophic",  # invalid
            "gap_concepts": [],
        }
        results = run_all(json.dumps(slide))
        assert not results["severity_valid"]

    def test_severity_critical_passes(self):
        from backend.evals.structural.ppt_checks import run_all

        slide = {
            "topic_name": "T",
            "slide_title": "A title with five or more words",
            "severity": "critical",
            "gap_concepts": [],
        }
        assert run_all(json.dumps(slide))["severity_valid"]

    def test_severity_moderate_passes(self):
        from backend.evals.structural.ppt_checks import run_all

        slide = {
            "topic_name": "T",
            "slide_title": "A title with five or more words",
            "severity": "moderate",
            "gap_concepts": [],
        }
        assert run_all(json.dumps(slide))["severity_valid"]

    def test_severity_minor_passes(self):
        from backend.evals.structural.ppt_checks import run_all

        slide = {
            "topic_name": "T",
            "slide_title": "A title with five or more words",
            "severity": "minor",
            "gap_concepts": [],
        }
        assert run_all(json.dumps(slide))["severity_valid"]

    def test_invalid_diagram_type_fails(self):
        from backend.evals.structural.ppt_checks import run_all

        slide = {
            "topic_name": "T",
            "slide_title": "A title with five or more words",
            "severity": "critical",
            "gap_concepts": [
                {
                    "concept": "C",
                    "description": "Desc",
                    "diagram_type": "bar_chart",  # invalid
                }
            ],
        }
        results = run_all(json.dumps(slide))
        assert not results["diagram_data_valid"]

    def test_diagram_node_count_too_low_fails(self):
        from backend.evals.structural.ppt_checks import run_all

        slide = {
            "topic_name": "T",
            "slide_title": "A title with five or more words",
            "severity": "critical",
            "gap_concepts": [
                {
                    "concept": "C",
                    "description": "Desc",
                    "diagram_type": "process_flow",
                    "diagram_data": {"nodes": ["A", "B"]},  # only 2, min is 3
                }
            ],
        }
        results = run_all(json.dumps(slide))
        assert not results["diagram_data_valid"]

    def test_diagram_node_count_too_high_fails(self):
        from backend.evals.structural.ppt_checks import run_all

        slide = {
            "topic_name": "T",
            "slide_title": "A title with five or more words",
            "severity": "critical",
            "gap_concepts": [
                {
                    "concept": "C",
                    "description": "Desc",
                    "diagram_type": "process_flow",
                    "diagram_data": {"nodes": ["A", "B", "C", "D", "E", "F", "G"]},  # 7, max is 6
                }
            ],
        }
        results = run_all(json.dumps(slide))
        assert not results["diagram_data_valid"]

    def test_diagram_node_count_in_range_passes(self):
        from backend.evals.structural.ppt_checks import run_all

        slide = {
            "topic_name": "T",
            "slide_title": "A title with five or more words",
            "severity": "critical",
            "gap_concepts": [
                {
                    "concept": "C",
                    "description": "Desc",
                    "diagram_type": "process_flow",
                    "diagram_data": {"nodes": ["A", "B", "C", "D"]},  # 4, valid
                }
            ],
        }
        results = run_all(json.dumps(slide))
        assert results["diagram_data_valid"]

    def test_short_assertion_title_fails(self):
        from backend.evals.structural.ppt_checks import run_all

        slide = {
            "topic_name": "Transformers",
            "slide_title": "Short title",  # only 2 words, need >= 5
            "severity": "critical",
            "gap_concepts": [],
        }
        results = run_all(json.dumps(slide))
        assert not results["assertion_titles"]

    def test_slide_count_matches_expected(self, valid_ppt_full):
        from backend.evals.structural.ppt_checks import run_all

        results = run_all(valid_ppt_full, expected_topic_count=2)
        assert results.get("slide_count_matches") is True

    def test_slide_count_mismatch_fails(self, valid_ppt_full):
        from backend.evals.structural.ppt_checks import run_all

        results = run_all(valid_ppt_full, expected_topic_count=5)
        assert results.get("slide_count_matches") is False

    def test_slide_count_not_included_for_single_slide(self, valid_ppt_single):
        from backend.evals.structural.ppt_checks import run_all

        # Single-slide format: slide_count_matches should not be in results
        results = run_all(valid_ppt_single, expected_topic_count=1)
        assert "slide_count_matches" not in results

    def test_topic_scores_complete_valid(self, valid_ppt_full):
        from backend.evals.structural.ppt_checks import run_all

        results = run_all(valid_ppt_full)
        assert results.get("topic_scores_complete") is True

    def test_topic_scores_out_of_range_fails(self):
        from backend.evals.structural.ppt_checks import run_all

        data = {
            "presentation_title": "Gap Analysis",
            "executive_summary": {
                "topic_scores": [
                    {"topic": "T", "curriculum_score": 150, "industry_requirement": 90},
                ]
            },
            "topic_slides": [
                {
                    "topic_name": "T",
                    "slide_title": "A title with five or more words here",
                    "severity": "critical",
                    "gap_concepts": [],
                }
            ],
        }
        results = run_all(json.dumps(data))
        assert not results.get("topic_scores_complete")

    def test_backwards_compat_importance_field(self):
        """Slide using 'importance' instead of 'severity' should still pass."""
        from backend.evals.structural.ppt_checks import run_all

        slide = {
            "topic_name": "Transformers",
            "slide_title": "A title with five or more words here",
            "importance": "critical",  # backward-compat field
            "gap_concepts": [],
        }
        results = run_all(json.dumps(slide))
        assert results["severity_valid"]

    def test_backwards_compat_concepts_field(self):
        """Slide using 'concepts' instead of 'gap_concepts' should pass schema check."""
        from backend.evals.structural.ppt_checks import run_all

        slide = {
            "topic_name": "Transformers",
            "slide_title": "A title with five or more words here",
            "severity": "critical",
            "concepts": [],  # backward-compat field
        }
        results = run_all(json.dumps(slide))
        assert results["schema_complete"]


# ===========================================================================
# _sanitize property-based tests
# ===========================================================================


class TestSanitizePropertyBased:
    """Property-based tests for the agent_ingest._sanitize helper."""

    @given(st.text())
    @hyp_settings(max_examples=200)
    def test_sanitize_never_contains_bad_control_chars(self, text):
        from backend.pipeline.agent_ingest import _sanitize

        result = _sanitize(text)
        for char in result:
            cp = ord(char)
            # Allowed: normal chars, \n (0x0a), \t (0x09)
            # Forbidden: \x00-\x08, \x0b, \x0c, \x0e-\x1f, \x7f
            assert not (0x00 <= cp <= 0x08), f"Found forbidden char U+{cp:04X}"
            assert cp != 0x0B, "Found \\x0b (vertical tab)"
            assert cp != 0x0C, "Found \\x0c (form feed)"
            assert not (0x0E <= cp <= 0x1F), f"Found forbidden char U+{cp:04X}"
            assert cp != 0x7F, "Found DEL char"

    @given(st.text())
    @hyp_settings(max_examples=100)
    def test_sanitize_preserves_newlines_and_tabs(self, text):
        from backend.pipeline.agent_ingest import _sanitize

        # Count newlines and tabs in input
        nl_in = text.count("\n")
        tab_in = text.count("\t")
        result = _sanitize(text[:500_000])  # truncate before sanitize to stay within limit
        nl_out = result.count("\n")
        tab_out = result.count("\t")
        # Sanitize should not remove \n or \t
        assert nl_out == nl_in or len(text) > 500_000  # truncation can affect counts too
        assert tab_out == tab_in or len(text) > 500_000

    def test_sanitize_truncates_over_500k(self):
        from backend.pipeline.agent_ingest import _sanitize

        long_text = "a" * 600_000
        result = _sanitize(long_text)
        assert len(result) <= 500_000

    def test_sanitize_clean_text_unchanged(self):
        from backend.pipeline.agent_ingest import _sanitize

        clean = "Hello world! This is normal text with\nnewlines and\ttabs."
        result = _sanitize(clean)
        assert result == clean

    def test_sanitize_strips_null_bytes(self):
        from backend.pipeline.agent_ingest import _sanitize

        text_with_nulls = "Hello\x00World\x00"
        result = _sanitize(text_with_nulls)
        assert "\x00" not in result
        assert "HelloWorld" in result
