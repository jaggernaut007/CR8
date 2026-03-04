"""Tests for the three LangGraph pipeline agents and their helper functions.

All external dependencies (LLM, ChromaDB, web search, file I/O) are mocked.
Zero real API calls.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch



# ===========================================================================
# _sanitize (agent_ingest)
# ===========================================================================


class TestSanitize:
    """Unit tests for the _sanitize helper in agent_ingest."""

    def test_strips_null_bytes(self):
        from backend.pipeline.agent_ingest import _sanitize

        result = _sanitize("Hello\x00World\x00!")
        assert "\x00" not in result
        assert "HelloWorld!" in result

    def test_strips_control_chars(self):
        from backend.pipeline.agent_ingest import _sanitize

        # \x01 through \x08 should all be stripped
        text = "".join(chr(c) for c in range(0x01, 0x09)) + "normal"
        result = _sanitize(text)
        for c in range(0x01, 0x09):
            assert chr(c) not in result
        assert "normal" in result

    def test_strips_vertical_tab_and_form_feed(self):
        from backend.pipeline.agent_ingest import _sanitize

        result = _sanitize("before\x0b\x0cafter")
        assert "\x0b" not in result
        assert "\x0c" not in result
        assert "beforeafter" in result

    def test_preserves_newlines(self):
        from backend.pipeline.agent_ingest import _sanitize

        text = "line one\nline two\nline three"
        assert _sanitize(text) == text

    def test_preserves_tabs(self):
        from backend.pipeline.agent_ingest import _sanitize

        text = "col1\tcol2\tcol3"
        assert _sanitize(text) == text

    def test_truncates_over_500k(self):
        from backend.pipeline.agent_ingest import _sanitize

        long_text = "a" * 600_000
        result = _sanitize(long_text)
        assert len(result) <= 500_000

    def test_clean_text_unchanged(self):
        from backend.pipeline.agent_ingest import _sanitize

        clean = "Hello world! This is normal text with\nnewlines and\ttabs."
        assert _sanitize(clean) == clean

    def test_strips_del_char(self):
        from backend.pipeline.agent_ingest import _sanitize

        result = _sanitize("before\x7fafter")
        assert "\x7f" not in result
        assert "beforeafter" in result


# ===========================================================================
# ingest_node
# ===========================================================================


def _make_valid_topics_json():
    return json.dumps({
        "topics": [
            {
                "name": "Transformers",
                "description": "Attention mechanism for seq-to-seq tasks",
                "key_techniques": ["self-attention", "positional encoding"],
            }
        ],
        "curriculum_scope": "Deep learning and NLP fundamentals",
    })


class TestIngestNode:
    """Tests for ingest_node — all I/O mocked."""

    def _run_ingest(self, tmp_path, topics_json=None, summarize_content=None):
        """Helper: run ingest_node with all deps mocked."""
        from backend.pipeline.agent_ingest import ingest_node

        topics_json = topics_json or _make_valid_topics_json()
        summarize_content = summarize_content or "## slide.pdf\nCurriculum summary text about NLP."

        fake_llm = MagicMock()
        fake_llm.invoke.side_effect = [
            MagicMock(content=summarize_content),
            MagicMock(content=topics_json),
        ]

        fake_store = MagicMock()

        with (
            patch("backend.pipeline.agent_ingest.ChromaStore", return_value=fake_store),
            patch("backend.pipeline.agent_ingest.get_llm", return_value=fake_llm),
            patch(
                "backend.pipeline.agent_ingest.extract_text",
                return_value=[{"source": "slide.pdf", "text": "Content about NLP", "page": 1}],
            ),
        ):
            return ingest_node({"file_paths": [str(tmp_path / "slide.pdf")]})

    def test_happy_path_returns_topics(self, tmp_path):
        result = self._run_ingest(tmp_path)
        assert "topics" in result
        assert len(result["topics"]) >= 1

    def test_topics_have_name_and_description(self, tmp_path):
        result = self._run_ingest(tmp_path)
        for topic in result["topics"]:
            assert "name" in topic
            assert "description" in topic

    def test_curriculum_scope_returned_in_state(self, tmp_path):
        result = self._run_ingest(tmp_path)
        assert "curriculum_scope" in result
        assert result["curriculum_scope"] != ""

    def test_current_stage_set_to_ingested(self, tmp_path):
        result = self._run_ingest(tmp_path)
        assert result["current_stage"] == "ingested"

    def test_raw_text_stored_in_state(self, tmp_path):
        result = self._run_ingest(tmp_path)
        assert "raw_text" in result
        # raw_text comes from joined page texts
        assert isinstance(result["raw_text"], str)

    def test_malformed_json_uses_fallback_topic(self, tmp_path):
        result = self._run_ingest(tmp_path, topics_json="NOT VALID JSON {{{")
        # Should fallback to single-topic result, not raise
        assert len(result["topics"]) >= 1
        assert result["curriculum_scope"] != ""

    def test_store_reset_called(self, tmp_path):
        """ChromaDB collections are reset at the start of each ingest."""
        from backend.pipeline.agent_ingest import ingest_node

        fake_llm = MagicMock()
        fake_llm.invoke.side_effect = [
            MagicMock(content="## f.pdf\nSummary"),
            MagicMock(content=_make_valid_topics_json()),
        ]
        fake_store = MagicMock()

        with (
            patch("backend.pipeline.agent_ingest.ChromaStore", return_value=fake_store),
            patch("backend.pipeline.agent_ingest.get_llm", return_value=fake_llm),
            patch(
                "backend.pipeline.agent_ingest.extract_text",
                return_value=[{"source": "f.pdf", "text": "NLP content", "page": 1}],
            ),
        ):
            ingest_node({"file_paths": [str(tmp_path / "f.pdf")]})

        fake_store.reset_collections.assert_called_once()


# ===========================================================================
# research_node
# ===========================================================================


def _make_gap_analysis(topic_name="Transformers"):
    return {
        "topic": topic_name,
        "gaps": [{"gap": "production deployment", "severity": "critical"}],
        "enrichments": [{"title": "Hugging Face", "why_it_matters": "Industry standard"}],
        "industry_context": "Used in GPT-4 and similar models",
        "severity": "critical",
    }


class TestResearchNode:
    """Tests for research_node — all I/O mocked."""

    def _run_research(self, topics=None, gap_fn=None):
        """Helper: run research_node with all deps mocked."""
        from backend.pipeline.agent_research import research_node

        if topics is None:
            topics = [
                {"name": "Transformers", "description": "Attention mechanism", "key_techniques": []}
            ]

        if gap_fn is None:
            gap_result = _make_gap_analysis("Transformers")
            gap_fn = MagicMock(return_value=gap_result)

        with (
            patch("backend.pipeline.agent_research.ChromaStore"),
            patch("backend.pipeline.agent_research.get_llm"),
            patch("backend.pipeline.agent_research._research_topic", side_effect=gap_fn),
        ):
            state = {
                "topics": topics,
                "curriculum_scope": "NLP deep learning",
            }
            return research_node(state)

    def test_happy_path_returns_gap_summary(self):
        result = self._run_research()
        assert "gap_summary" in result
        assert len(result["gap_summary"]) == 1

    def test_gap_summary_has_expected_keys(self):
        result = self._run_research()
        entry = result["gap_summary"][0]
        assert "topic" in entry or "gaps" in entry  # topic may be nested in dict

    def test_current_stage_set_to_researched(self):
        result = self._run_research()
        assert result["current_stage"] == "researched"

    def test_one_result_per_topic(self):
        topics = [
            {"name": "BERT", "description": "Bidirectional encoder", "key_techniques": []},
            {"name": "GPT", "description": "Autoregressive decoder", "key_techniques": []},
        ]
        call_count = [0]

        def gap_fn(i, topic, total, store, llm, scope):
            call_count[0] += 1
            return _make_gap_analysis(topic["name"])

        result = self._run_research(topics=topics, gap_fn=gap_fn)
        assert len(result["gap_summary"]) == 2

    def test_search_failure_continues(self):
        """If search raises during _research_topic, research_node handles it gracefully."""
        from backend.pipeline.agent_research import research_node

        topics = [{"name": "BERT", "description": "Encoder", "key_techniques": []}]

        def failing_research(i, topic, total, store, llm, scope):
            raise RuntimeError("Network error")

        with (
            patch("backend.pipeline.agent_research.ChromaStore"),
            patch("backend.pipeline.agent_research.get_llm"),
            patch("backend.pipeline.agent_research._research_topic", side_effect=failing_research),
        ):
            result = research_node({"topics": topics, "curriculum_scope": "NLP"})

        # Node should complete with fallback entry for the failed topic
        assert "gap_summary" in result
        assert len(result["gap_summary"]) == 1
        assert result["current_stage"] == "researched"

    def test_empty_topics_returns_empty_gap_summary(self):
        result = self._run_research(topics=[])
        assert result["gap_summary"] == []
        assert result["current_stage"] == "researched"


# ===========================================================================
# _validate_module (agent_generate)
# ===========================================================================


_VALID_MODULE = (
    "## Module Overview\nOverview content here.\n"
    "## Learning Objectives\n- Explain X (Curriculum)\n- Apply Y (Gap)\n"
    "## Core Content\n### Section A\nDetailed content.\n"
    "## Key Takeaways\ncurriculum: X. gap: Y.\n"
    + "Additional padding content to ensure we exceed two thousand characters. " * 30
)


class TestValidateModule:
    """Tests for _validate_module in agent_generate."""

    def test_valid_module_passes(self):
        from backend.pipeline.agent_generate import _validate_module

        is_valid, issues = _validate_module(_VALID_MODULE, "Test Topic")
        assert is_valid
        assert issues == []

    def test_short_module_returns_issues(self):
        from backend.pipeline.agent_generate import _validate_module

        short = "## Module Overview\nBrief.\n## Learning Objectives\nBrief.\n## Core Content\nBrief.\n## Key Takeaways\nBrief."
        is_valid, issues = _validate_module(short, "Test Topic")
        assert not is_valid
        assert any("short" in issue.lower() or "Too short" in issue for issue in issues)

    def test_missing_section_named_in_issues(self):
        from backend.pipeline.agent_generate import _validate_module

        # Remove "## Core Content" from an otherwise valid module
        no_core = _VALID_MODULE.replace("## Core Content", "## MISSING_SECTION")
        is_valid, issues = _validate_module(no_core, "Test Topic")
        assert not is_valid
        assert any("Core Content" in issue for issue in issues)

    def test_all_four_required_sections_needed(self):
        """_validate_module checks exactly 4 sections, not the 9 from module_checks.py."""
        from backend.pipeline.agent_generate import _validate_module

        # A module with all 4 agent-level required sections + enough chars passes
        valid = (
            "## Module Overview\n"
            "## Learning Objectives\n"
            "## Core Content\n### Sub\n"
            "## Key Takeaways\n"
            + "x" * 2000
        )
        is_valid, issues = _validate_module(valid, "Test")
        assert is_valid


# ===========================================================================
# _detect_hook_type (agent_generate)
# ===========================================================================


class TestDetectHookType:
    """Tests for the _detect_hook_type helper in agent_generate."""

    def test_curiosity_hook(self):
        from backend.pipeline.agent_generate import _detect_hook_type

        script = "Did you know that transformers changed everything about NLP?"
        assert _detect_hook_type(script) == "curiosity"

    def test_what_if_curiosity_hook(self):
        from backend.pipeline.agent_generate import _detect_hook_type

        script = "What if you could process entire sequences in parallel?"
        assert _detect_hook_type(script) == "curiosity"

    def test_scenario_hook(self):
        from backend.pipeline.agent_generate import _detect_hook_type

        script = "Imagine you're building a search engine for a billion documents."
        assert _detect_hook_type(script) == "scenario"

    def test_statistic_hook(self):
        from backend.pipeline.agent_generate import _detect_hook_type

        script = "Studies show that 87% of ML engineers use transformers daily."
        assert _detect_hook_type(script) == "statistic"

    def test_percent_statistic_hook(self):
        from backend.pipeline.agent_generate import _detect_hook_type

        script = "Over 90% of modern NLP systems are transformer-based."
        assert _detect_hook_type(script) == "statistic"

    def test_misconception_hook(self):
        from backend.pipeline.agent_generate import _detect_hook_type

        script = "Most students think that RNNs are still the dominant architecture."
        assert _detect_hook_type(script) == "misconception"

    def test_value_promise_hook(self):
        from backend.pipeline.agent_generate import _detect_hook_type

        script = "By the end of this lecture, you'll be able to implement self-attention."
        assert _detect_hook_type(script) == "value_promise"

    def test_in_the_next_value_promise(self):
        from backend.pipeline.agent_generate import _detect_hook_type

        script = "In the next few minutes, we'll cover positional encoding from scratch."
        assert _detect_hook_type(script) == "value_promise"

    def test_unknown_hook_type(self):
        from backend.pipeline.agent_generate import _detect_hook_type

        script = "Today we explore the transformer architecture and its key components."
        assert _detect_hook_type(script) == "unknown"

    def test_only_checks_first_300_chars(self):
        """Hook detection only looks at the first 300 characters."""
        from backend.pipeline.agent_generate import _detect_hook_type

        # Put the keyword far past 300 chars — should not be detected
        padding = "x" * 350
        script = padding + "Did you know that this comes after 300 chars?"
        assert _detect_hook_type(script) == "unknown"


# ===========================================================================
# generate_node
# ===========================================================================


def _make_module_content():
    """Return module content that passes _validate_module."""
    return (
        "## Module Overview\nDetailed overview content.\n"
        "## Learning Objectives\n- Explain transformers (Curriculum)\n- Apply attention (Gap)\n"
        "## Core Content\n### Self-Attention\nDetailed content here.\n"
        "## Key Takeaways\ncurriculum: transformers. gap: deployment.\n"
        + "Additional content padding to exceed the minimum character requirement. " * 30
    )


class TestGenerateNode:
    """Tests for generate_node — all I/O mocked."""

    def _build_state(self, output_formats="pdf", num_topics=1):
        topics = [
            {"name": f"Topic {i}", "description": f"Desc {i}", "key_techniques": []}
            for i in range(num_topics)
        ]
        gap_summary = [
            {"topic": f"Topic {i}", "gaps": [], "enrichments": [], "severity": "moderate"}
            for i in range(num_topics)
        ]
        return {
            "topics": topics,
            "curriculum_scope": "NLP basics",
            "gap_summary": gap_summary,
            "output_formats": output_formats,
            "current_stage": "researched",
        }

    def _run_generate(self, state, tmp_path, monkeypatch):
        from backend.pipeline.agent_generate import generate_node

        monkeypatch.chdir(tmp_path)

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content=_make_module_content())

        fake_store = MagicMock()
        fake_store.query.return_value = {"documents": [[]], "ids": [[]]}

        pdf_path = str(tmp_path / "output.pdf")

        with (
            patch("backend.pipeline.agent_generate.ChromaStore", return_value=fake_store),
            patch("backend.pipeline.agent_generate.get_llm", return_value=mock_llm),
            patch("backend.pipeline.agent_generate.build_pdf", return_value=pdf_path),
            patch("backend.pipeline.agent_generate.build_gap_ppt", return_value=("out.pptx", {})),
            patch("backend.pipeline.agent_generate.build_videos"),
        ):
            return generate_node(state)

    def test_current_stage_set_to_complete(self, tmp_path, monkeypatch):
        state = self._build_state(output_formats="pdf")
        result = self._run_generate(state, tmp_path, monkeypatch)
        assert result["current_stage"] == "complete"

    def test_pdf_format_sets_pdf_path(self, tmp_path, monkeypatch):
        state = self._build_state(output_formats="pdf")
        result = self._run_generate(state, tmp_path, monkeypatch)
        assert "pdf_path" in result
        assert result["pdf_path"] != ""

    def test_no_pdf_when_format_not_requested(self, tmp_path, monkeypatch):
        # Only request ppt, not pdf
        state = self._build_state(output_formats="ppt")
        state["gap_summary"] = [
            {"topic": "Topic 0", "gaps": [{"gap": "x"}], "enrichments": [], "severity": "critical"}
        ]
        result = self._run_generate(state, tmp_path, monkeypatch)
        assert result.get("pdf_path", "") == ""

    def test_one_llm_call_per_topic_for_module_generation(self, tmp_path, monkeypatch):
        """generate_node calls the LLM once per topic for module generation."""
        from backend.pipeline.agent_generate import generate_node

        monkeypatch.chdir(tmp_path)

        state = self._build_state(output_formats="pdf", num_topics=2)

        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content=_make_module_content())

        fake_store = MagicMock()
        fake_store.query.return_value = {"documents": [[]], "ids": [[]]}

        with (
            patch("backend.pipeline.agent_generate.ChromaStore", return_value=fake_store),
            patch("backend.pipeline.agent_generate.get_llm", return_value=mock_llm),
            patch("backend.pipeline.agent_generate.build_pdf", return_value="/tmp/out.pdf"),
            patch("backend.pipeline.agent_generate.build_gap_ppt", return_value=("out.pptx", {})),
            patch("backend.pipeline.agent_generate.build_videos"),
        ):
            generate_node(state)

        # At least 2 invoke calls (one per topic, possibly more for LLM tiers)
        assert mock_llm.invoke.call_count >= 2

    def test_result_always_has_current_stage(self, tmp_path, monkeypatch):
        """Even with empty topics, generate_node returns current_stage."""
        state = self._build_state(output_formats="pdf", num_topics=0)
        result = self._run_generate(state, tmp_path, monkeypatch)
        assert result.get("current_stage") == "complete"
