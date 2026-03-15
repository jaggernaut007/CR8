"""Tests for backend/pipeline/agent_generate.py.

Covers:
- _VideoJobInputs dataclass -- field storage, optional defaults
- _build_chroma_cache -- ChromaDB query routing and result assembly
- _validate_module -- length gate, missing sections, valid module
- _generate_module -- severity-based model routing, success on first attempt,
  retry on failure, best-effort fallback after max retries
- generate_node -- dual PDF+PPT parallel path and PPT-only path
"""

import json
from unittest.mock import MagicMock, patch

from backend.pipeline.agent_generate import (
    _MAX_MODULE_RETRIES,
    _MIN_MODULE_CHARS,
    _REQUIRED_SECTIONS,
    _GenerateCtx,
    _VideoJobInputs,
    _build_chroma_cache,
    _validate_module,
    _generate_module,
)


# ---------------------------------------------------------------------------
# _VideoJobInputs
# ---------------------------------------------------------------------------


class TestVideoJobInputs:
    def test_stores_video_topics(self):
        topics = [{"name": "Topic A"}]
        obj = _VideoJobInputs(topics, [], "/tmp/vid", [])
        assert obj.video_topics == topics

    def test_stores_scripts(self):
        scripts = ["script one", "script two"]
        obj = _VideoJobInputs([], scripts, "/tmp/vid", [])
        assert obj.scripts == scripts

    def test_stores_video_dir(self):
        obj = _VideoJobInputs([], [], "/tmp/output/videos", [])
        assert obj.video_dir == "/tmp/output/videos"

    def test_stores_slide_images(self):
        images = ["/tmp/slide_001.png", "/tmp/slide_002.png"]
        obj = _VideoJobInputs([], [], "/tmp/vid", images)
        assert obj.slide_images == images

    def test_topic_slide_map_defaults_to_none(self):
        obj = _VideoJobInputs([], [], "/tmp/vid", [])
        assert obj.topic_slide_map is None

    def test_ppt_path_defaults_to_none(self):
        obj = _VideoJobInputs([], [], "/tmp/vid", [])
        assert obj.ppt_path is None

    def test_explicit_topic_slide_map(self):
        tsm = {"Topic A": [1, 2]}
        obj = _VideoJobInputs([], [], "/tmp/vid", [], topic_slide_map=tsm)
        assert obj.topic_slide_map == tsm

    def test_explicit_ppt_path(self):
        obj = _VideoJobInputs([], [], "/tmp/vid", [], ppt_path="/tmp/deck.pptx")
        assert obj.ppt_path == "/tmp/deck.pptx"


# ---------------------------------------------------------------------------
# _build_chroma_cache
# ---------------------------------------------------------------------------


def _make_store(curriculum_docs, research_docs):
    """Build a mock ChromaStore returning the given doc lists."""
    store = MagicMock()

    def query_side_effect(collection, name, n_results):
        if collection == "curriculum":
            return {"documents": [curriculum_docs]}
        return {"documents": [research_docs]}

    store.query.side_effect = query_side_effect
    return store


class TestBuildChromaCache:
    def test_returns_dict_keyed_by_topic_name(self):
        store = _make_store(["chunk1"], ["res1"])
        topics = [{"name": "NLP Basics"}]
        cache = _build_chroma_cache(store, topics)
        assert "NLP Basics" in cache

    def test_curriculum_text_joins_documents(self):
        store = _make_store(["chunk A", "chunk B"], [])
        topics = [{"name": "Topic"}]
        cache = _build_chroma_cache(store, topics)
        assert "chunk A" in cache["Topic"]["curriculum_text"]
        assert "chunk B" in cache["Topic"]["curriculum_text"]

    def test_research_text_joins_documents(self):
        store = _make_store([], ["res X", "res Y"])
        topics = [{"name": "Topic"}]
        cache = _build_chroma_cache(store, topics)
        assert "res X" in cache["Topic"]["research_text"]

    def test_empty_curriculum_docs_returns_placeholder(self):
        store = _make_store([], ["res1"])
        topics = [{"name": "Topic"}]
        cache = _build_chroma_cache(store, topics)
        assert cache["Topic"]["curriculum_text"] == "No curriculum content available."

    def test_empty_research_docs_returns_placeholder(self):
        store = _make_store(["chunk1"], [])
        topics = [{"name": "Topic"}]
        cache = _build_chroma_cache(store, topics)
        assert cache["Topic"]["research_text"] == "No research content available."

    def test_queries_both_collections_per_topic(self):
        store = _make_store(["c"], ["r"])
        topics = [{"name": "Alpha"}, {"name": "Beta"}]
        _build_chroma_cache(store, topics)
        # 2 topics, 2 queries each = 4 total calls
        assert store.query.call_count == 4

    def test_queries_curriculum_collection_with_n_results_5(self):
        store = _make_store(["c"], ["r"])
        topics = [{"name": "T"}]
        _build_chroma_cache(store, topics)
        store.query.assert_any_call("curriculum", "T", n_results=5)

    def test_queries_research_collection_with_n_results_5(self):
        store = _make_store(["c"], ["r"])
        topics = [{"name": "T"}]
        _build_chroma_cache(store, topics)
        store.query.assert_any_call("research", "T", n_results=5)

    def test_empty_topics_returns_empty_dict(self):
        store = MagicMock()
        cache = _build_chroma_cache(store, [])
        assert cache == {}


# ---------------------------------------------------------------------------
# _validate_module
# ---------------------------------------------------------------------------


def _long_module_with_sections(sections):
    """Return a string containing all given section headers, padded to >2000 chars."""
    content = "\n".join(sections) + "\n"
    content += "x" * max(0, _MIN_MODULE_CHARS - len(content) + 1)
    return content


class TestValidateModule:
    def test_valid_module_returns_true(self, valid_module_md):
        is_valid, _issues = _validate_module(valid_module_md, "Test Topic")
        assert is_valid is True

    def test_valid_module_returns_empty_issues(self, valid_module_md):
        _, issues = _validate_module(valid_module_md, "Test Topic")
        assert issues == []

    def test_too_short_returns_false(self):
        short = "\n".join(_REQUIRED_SECTIONS) + "\n"  # < _MIN_MODULE_CHARS
        is_valid, _ = _validate_module(short, "Topic")
        assert is_valid is False

    def test_too_short_includes_length_issue(self):
        short = "\n".join(_REQUIRED_SECTIONS) + "\n"
        _, issues = _validate_module(short, "Topic")
        assert any("Too short" in i for i in issues)

    def test_missing_section_returns_false(self):
        module = _long_module_with_sections(_REQUIRED_SECTIONS[1:])  # drop first
        is_valid, _ = _validate_module(module, "Topic")
        assert is_valid is False

    def test_missing_section_named_in_issues(self):
        missing = _REQUIRED_SECTIONS[0]
        module = _long_module_with_sections(_REQUIRED_SECTIONS[1:])
        _, issues = _validate_module(module, "Topic")
        assert any(missing in i for i in issues)

    def test_all_required_sections_present_and_long_enough(self):
        module = _long_module_with_sections(_REQUIRED_SECTIONS)
        is_valid, _ = _validate_module(module, "Topic")
        assert is_valid is True

    def test_multiple_issues_reported_together(self):
        """Both 'too short' and 'missing section' can appear in the same issues list."""
        very_short = "tiny"  # misses every section and is short
        _, issues = _validate_module(very_short, "Topic")
        assert len(issues) >= 2

    def test_topic_name_does_not_affect_validation(self):
        """topic_name is accepted but not factored into validation logic."""
        module = _long_module_with_sections(_REQUIRED_SECTIONS)
        is_valid_a, _ = _validate_module(module, "Alpha")
        is_valid_b, _ = _validate_module(module, "Beta")
        assert is_valid_a == is_valid_b


# ---------------------------------------------------------------------------
# _generate_module
# ---------------------------------------------------------------------------


def _make_chroma_cache(name):
    return {
        name: {
            "curriculum_text": "curriculum content",
            "research_text": "research content",
        }
    }


def _make_gap_lookup(name, severity="moderate"):
    return {name: {"severity": severity, "gaps": ["gap1"]}}


def _make_valid_response(content=None):
    if content is None:
        content = _long_module_with_sections(_REQUIRED_SECTIONS)
    resp = MagicMock()
    resp.content = content
    return resp


def _make_module_ctx(chroma_cache, llm_premium, llm_mini, scope, gap_lookup):
    """Build a _GenerateCtx for _generate_module tests."""
    ctx = _GenerateCtx()
    ctx.chroma_cache = chroma_cache
    ctx.llm_premium = llm_premium
    ctx.llm_mini = llm_mini
    ctx.curriculum_scope = scope
    ctx.gap_lookup = gap_lookup
    return ctx


class TestGenerateModule:
    def test_returns_string_on_success(self):
        topic = {"name": "Transformers", "description": "desc", "key_techniques": []}
        cache = _make_chroma_cache("Transformers")
        gap_lookup = _make_gap_lookup("Transformers")
        llm = MagicMock()
        llm.invoke.return_value = _make_valid_response()
        ctx = _make_module_ctx(cache, llm, llm, "CS224N", gap_lookup)

        result = _generate_module(0, topic, 1, ctx)
        assert isinstance(result, str)

    def test_uses_premium_llm_for_critical_severity(self):
        topic = {"name": "Topic", "description": "", "key_techniques": []}
        cache = _make_chroma_cache("Topic")
        gap_lookup = _make_gap_lookup("Topic", severity="critical")
        llm_premium = MagicMock()
        llm_mini = MagicMock()
        llm_premium.invoke.return_value = _make_valid_response()
        ctx = _make_module_ctx(cache, llm_premium, llm_mini, "scope", gap_lookup)

        _generate_module(0, topic, 1, ctx)
        assert llm_premium.invoke.called
        assert not llm_mini.invoke.called

    def test_uses_mini_llm_for_moderate_severity(self):
        topic = {"name": "Topic", "description": "", "key_techniques": []}
        cache = _make_chroma_cache("Topic")
        gap_lookup = _make_gap_lookup("Topic", severity="moderate")
        llm_premium = MagicMock()
        llm_mini = MagicMock()
        llm_mini.invoke.return_value = _make_valid_response()
        ctx = _make_module_ctx(cache, llm_premium, llm_mini, "scope", gap_lookup)

        _generate_module(0, topic, 1, ctx)
        assert llm_mini.invoke.called
        assert not llm_premium.invoke.called

    def test_uses_mini_llm_for_minor_severity(self):
        topic = {"name": "Topic", "description": "", "key_techniques": []}
        cache = _make_chroma_cache("Topic")
        gap_lookup = _make_gap_lookup("Topic", severity="minor")
        llm_premium = MagicMock()
        llm_mini = MagicMock()
        llm_mini.invoke.return_value = _make_valid_response()
        ctx = _make_module_ctx(cache, llm_premium, llm_mini, "scope", gap_lookup)

        _generate_module(0, topic, 1, ctx)
        assert llm_mini.invoke.called

    def test_returns_immediately_when_first_attempt_valid(self):
        topic = {"name": "Topic", "description": "", "key_techniques": []}
        cache = _make_chroma_cache("Topic")
        gap_lookup = _make_gap_lookup("Topic")
        llm = MagicMock()
        llm.invoke.return_value = _make_valid_response()
        ctx = _make_module_ctx(cache, llm, llm, "scope", gap_lookup)

        _generate_module(0, topic, 1, ctx)
        assert llm.invoke.call_count == 1

    def test_retries_when_first_response_invalid(self):
        topic = {"name": "Topic", "description": "", "key_techniques": []}
        cache = _make_chroma_cache("Topic")
        gap_lookup = _make_gap_lookup("Topic")
        llm = MagicMock()
        # First call: too-short invalid response; second call: valid
        short_resp = MagicMock()
        short_resp.content = "too short"
        valid_resp = _make_valid_response()
        llm.invoke.side_effect = [short_resp, valid_resp]
        ctx = _make_module_ctx(cache, llm, llm, "scope", gap_lookup)

        result = _generate_module(0, topic, 1, ctx)
        assert llm.invoke.call_count == 2
        assert result == valid_resp.content

    def test_returns_best_effort_after_max_retries(self):
        topic = {"name": "Topic", "description": "", "key_techniques": []}
        cache = _make_chroma_cache("Topic")
        gap_lookup = _make_gap_lookup("Topic")
        llm = MagicMock()

        # All responses are invalid (too short)
        bad_resp = MagicMock()
        bad_resp.content = "stub"
        llm.invoke.return_value = bad_resp
        ctx = _make_module_ctx(cache, llm, llm, "scope", gap_lookup)

        result = _generate_module(0, topic, 1, ctx)
        # Should have tried _MAX_MODULE_RETRIES + 1 times in total
        assert llm.invoke.call_count == _MAX_MODULE_RETRIES + 1
        assert result == "stub"

    def test_uses_gap_analysis_no_gap_text_when_missing(self):
        topic = {"name": "NoGap", "description": "", "key_techniques": []}
        cache = _make_chroma_cache("NoGap")
        llm = MagicMock()
        llm.invoke.return_value = _make_valid_response()
        ctx = _make_module_ctx(cache, llm, llm, "scope", {})

        # gap_lookup has no entry for this topic — should not raise
        result = _generate_module(0, topic, 1, ctx)
        assert isinstance(result, str)

    def test_custom_prompt_template_used_when_provided(self):
        topic = {"name": "Topic", "description": "", "key_techniques": []}
        cache = _make_chroma_cache("Topic")
        gap_lookup = _make_gap_lookup("Topic")
        llm = MagicMock()
        llm.invoke.return_value = _make_valid_response()
        ctx = _make_module_ctx(cache, llm, llm, "scope", gap_lookup)

        custom_template = (
            "Custom: {topic_name} {topic_description} {key_techniques} "
            "{curriculum_scope} {curriculum_chunks} {research_chunks} {gap_analysis}"
        )
        _generate_module(0, topic, 1, ctx, prompt_template=custom_template)

        call_args = llm.invoke.call_args[0][0]
        assert "Custom:" in call_args


# ---------------------------------------------------------------------------
# generate_node — dual PDF+PPT parallel path
# ---------------------------------------------------------------------------


def _make_state_with_gap(formats="pdf,ppt"):
    return {
        "job_id": "abcd1234",
        "file_paths": [],
        "topics": [{"name": "NLP Basics", "description": "intro", "key_techniques": []}],
        "raw_text": "",
        "curriculum_scope": "CS224N",
        "gap_summary": [{"topic": "NLP Basics", "severity": "moderate", "gaps": ["gap1"]}],
        "pdf_path": "",
        "ppt_path": "",
        "video_dir": "",
        "output_formats": formats,
        "current_stage": "generate",
        "modules_md": [],
    }


class TestGenerateNodeDualPath:
    """Tests for the parallel PDF+PPT path in generate_node."""

    @patch("backend.pipeline.agent_generate.ChromaStore")
    @patch("backend.pipeline.agent_generate.get_llm")
    @patch("backend.pipeline.agent_generate.build_pdf")
    @patch("backend.pipeline.agent_generate._structure_slides_parallel")
    @patch("backend.pipeline.agent_generate.build_gap_ppt")
    @patch("backend.pipeline.agent_generate._generate_module")
    def test_pdf_path_in_result_when_pdf_and_ppt_requested(
        self,
        mock_gen_module,
        mock_build_ppt,
        mock_structure,
        mock_build_pdf,
        mock_get_llm,
        mock_chroma_cls,
        valid_ppt_full,
    ):
        mock_get_llm.return_value = MagicMock()
        mock_chroma_cls.return_value.query.return_value = {"documents": [["content"]]}
        mock_gen_module.return_value = _long_module_with_sections(_REQUIRED_SECTIONS)
        mock_structure.return_value = json.loads(valid_ppt_full)
        mock_build_ppt.return_value = ("/tmp/deck.pptx", {"NLP Basics": [1, 2]})

        from backend.pipeline.agent_generate import generate_node
        result = generate_node(_make_state_with_gap("pdf,ppt"))

        assert "pdf_path" in result

    @patch("backend.pipeline.agent_generate.ChromaStore")
    @patch("backend.pipeline.agent_generate.get_llm")
    @patch("backend.pipeline.agent_generate.build_pdf")
    @patch("backend.pipeline.agent_generate._structure_slides_parallel")
    @patch("backend.pipeline.agent_generate.build_gap_ppt")
    @patch("backend.pipeline.agent_generate._generate_module")
    def test_ppt_path_in_result_when_pdf_and_ppt_requested(
        self,
        mock_gen_module,
        mock_build_ppt,
        mock_structure,
        mock_build_pdf,
        mock_get_llm,
        mock_chroma_cls,
        valid_ppt_full,
    ):
        mock_get_llm.return_value = MagicMock()
        mock_chroma_cls.return_value.query.return_value = {"documents": [["content"]]}
        mock_gen_module.return_value = _long_module_with_sections(_REQUIRED_SECTIONS)
        mock_structure.return_value = json.loads(valid_ppt_full)
        mock_build_ppt.return_value = ("/tmp/deck.pptx", {"NLP Basics": [1, 2]})

        from backend.pipeline.agent_generate import generate_node
        result = generate_node(_make_state_with_gap("pdf,ppt"))

        assert "ppt_path" in result

    @patch("backend.pipeline.agent_generate.ChromaStore")
    @patch("backend.pipeline.agent_generate.get_llm")
    @patch("backend.pipeline.agent_generate.build_pdf")
    @patch("backend.pipeline.agent_generate._structure_slides_parallel")
    @patch("backend.pipeline.agent_generate.build_gap_ppt")
    @patch("backend.pipeline.agent_generate._generate_module")
    def test_build_pdf_called_once_in_parallel_path(
        self,
        mock_gen_module,
        mock_build_ppt,
        mock_structure,
        mock_build_pdf,
        mock_get_llm,
        mock_chroma_cls,
        valid_ppt_full,
    ):
        mock_get_llm.return_value = MagicMock()
        mock_chroma_cls.return_value.query.return_value = {"documents": [["content"]]}
        mock_gen_module.return_value = _long_module_with_sections(_REQUIRED_SECTIONS)
        mock_structure.return_value = json.loads(valid_ppt_full)
        mock_build_ppt.return_value = ("/tmp/deck.pptx", {"NLP Basics": [1, 2]})

        from backend.pipeline.agent_generate import generate_node
        generate_node(_make_state_with_gap("pdf,ppt"))

        assert mock_build_pdf.call_count == 1

    @patch("backend.pipeline.agent_generate.ChromaStore")
    @patch("backend.pipeline.agent_generate.get_llm")
    @patch("backend.pipeline.agent_generate.build_pdf")
    @patch("backend.pipeline.agent_generate._structure_slides_parallel")
    @patch("backend.pipeline.agent_generate.build_gap_ppt")
    @patch("backend.pipeline.agent_generate._generate_module")
    def test_structure_slides_called_once_in_parallel_path(
        self,
        mock_gen_module,
        mock_build_ppt,
        mock_structure,
        mock_build_pdf,
        mock_get_llm,
        mock_chroma_cls,
        valid_ppt_full,
    ):
        mock_get_llm.return_value = MagicMock()
        mock_chroma_cls.return_value.query.return_value = {"documents": [["content"]]}
        mock_gen_module.return_value = _long_module_with_sections(_REQUIRED_SECTIONS)
        mock_structure.return_value = json.loads(valid_ppt_full)
        mock_build_ppt.return_value = ("/tmp/deck.pptx", {"NLP Basics": [1, 2]})

        from backend.pipeline.agent_generate import generate_node
        generate_node(_make_state_with_gap("pdf,ppt"))

        assert mock_structure.call_count == 1

    @patch("backend.pipeline.agent_generate.ChromaStore")
    @patch("backend.pipeline.agent_generate.get_llm")
    @patch("backend.pipeline.agent_generate.build_pdf")
    @patch("backend.pipeline.agent_generate._structure_slides_parallel")
    @patch("backend.pipeline.agent_generate._ppt_monolithic_fallback")
    @patch("backend.pipeline.agent_generate.build_gap_ppt")
    @patch("backend.pipeline.agent_generate._generate_module")
    def test_monolithic_fallback_called_when_parallel_returns_none(
        self,
        mock_gen_module,
        mock_build_ppt,
        mock_fallback,
        mock_structure,
        mock_build_pdf,
        mock_get_llm,
        mock_chroma_cls,
        valid_ppt_full,
    ):
        mock_get_llm.return_value = MagicMock()
        mock_chroma_cls.return_value.query.return_value = {"documents": [["content"]]}
        mock_gen_module.return_value = _long_module_with_sections(_REQUIRED_SECTIONS)
        # Parallel structuring fails
        mock_structure.return_value = None
        mock_fallback.return_value = json.loads(valid_ppt_full)
        mock_build_ppt.return_value = ("/tmp/deck.pptx", {})

        from backend.pipeline.agent_generate import generate_node
        generate_node(_make_state_with_gap("pdf,ppt"))

        mock_fallback.assert_called_once()

    @patch("backend.pipeline.agent_generate.ChromaStore")
    @patch("backend.pipeline.agent_generate.get_llm")
    @patch("backend.pipeline.agent_generate.build_pdf")
    @patch("backend.pipeline.agent_generate._generate_module")
    def test_pdf_only_format_does_not_call_build_ppt(
        self,
        mock_gen_module,
        mock_build_pdf,
        mock_get_llm,
        mock_chroma_cls,
    ):
        mock_get_llm.return_value = MagicMock()
        mock_chroma_cls.return_value.query.return_value = {"documents": [["content"]]}
        mock_gen_module.return_value = _long_module_with_sections(_REQUIRED_SECTIONS)

        with patch("backend.pipeline.agent_generate.build_gap_ppt") as mock_ppt:
            from backend.pipeline.agent_generate import generate_node
            result = generate_node(_make_state_with_gap("pdf"))
            mock_ppt.assert_not_called()

        assert "pdf_path" in result
        assert "ppt_path" not in result

    @patch("backend.pipeline.agent_generate.ChromaStore")
    @patch("backend.pipeline.agent_generate.get_llm")
    @patch("backend.pipeline.agent_generate._generate_module")
    def test_result_contains_current_stage_complete(
        self, mock_gen_module, mock_get_llm, mock_chroma_cls
    ):
        mock_get_llm.return_value = MagicMock()
        mock_chroma_cls.return_value.query.return_value = {"documents": [["content"]]}
        mock_gen_module.return_value = _long_module_with_sections(_REQUIRED_SECTIONS)

        with patch("backend.pipeline.agent_generate.build_pdf"):
            from backend.pipeline.agent_generate import generate_node
            result = generate_node(_make_state_with_gap("pdf"))

        assert result["current_stage"] == "complete"

    @patch("backend.pipeline.agent_generate.ChromaStore")
    @patch("backend.pipeline.agent_generate.get_llm")
    @patch("backend.pipeline.agent_generate._generate_module")
    def test_result_contains_modules_md(
        self, mock_gen_module, mock_get_llm, mock_chroma_cls
    ):
        mock_get_llm.return_value = MagicMock()
        mock_chroma_cls.return_value.query.return_value = {"documents": [["content"]]}
        module_content = _long_module_with_sections(_REQUIRED_SECTIONS)
        mock_gen_module.return_value = module_content

        with patch("backend.pipeline.agent_generate.build_pdf"):
            from backend.pipeline.agent_generate import generate_node
            result = generate_node(_make_state_with_gap("pdf"))

        assert "modules_md" in result
        assert len(result["modules_md"]) == 1

    @patch("backend.pipeline.agent_generate.ChromaStore")
    @patch("backend.pipeline.agent_generate.get_llm")
    @patch("backend.pipeline.agent_generate._generate_module")
    def test_ppt_skipped_when_no_gap_summary(
        self, mock_gen_module, mock_get_llm, mock_chroma_cls
    ):
        mock_get_llm.return_value = MagicMock()
        mock_chroma_cls.return_value.query.return_value = {"documents": [["content"]]}
        mock_gen_module.return_value = _long_module_with_sections(_REQUIRED_SECTIONS)

        state = _make_state_with_gap("pdf,ppt")
        state["gap_summary"] = []  # no gap data

        with (
            patch("backend.pipeline.agent_generate.build_pdf"),
            patch("backend.pipeline.agent_generate.build_gap_ppt") as mock_ppt,
        ):
            from backend.pipeline.agent_generate import generate_node
            generate_node(state)

        mock_ppt.assert_not_called()
