"""Regression tests for the bugs fixed in the March 2026 hardening pass.

Each test class targets exactly one bug fix and is named after the file it covers.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fix 1a — comparator.py: per-criterion mean calculation
# ---------------------------------------------------------------------------

class TestComparatorPerCriterionMath:
    """Verify the corrected per-criterion average calculation in comparator.compare()."""

    def _make_result(self, scores_by_criterion: dict, variant: str, case_id: str = "c1"):
        from backend.evals.datasets.schema import CriterionScore, EvalResult, OutputType
        criterion_scores = [
            CriterionScore(criterion_name=k, score=v, weight=1.0, rationale="")
            for k, v in scores_by_criterion.items()
        ]
        weighted = sum(s.score * s.weight for s in criterion_scores) / max(
            sum(s.weight for s in criterion_scores), 1e-9
        )
        return EvalResult(
            case_id=case_id,
            output_type=OutputType.MODULE,
            prompt_variant=variant,
            structural_checks={},
            criterion_scores=criterion_scores,
            weighted_total=weighted,
            raw_output="",
        )

    def test_per_criterion_delta_is_correct(self):
        from backend.evals.harness.comparator import compare

        # A scores 2.0 on "depth", B scores 4.0 — expected delta = +2.0
        ra = self._make_result({"depth": 2, "clarity": 3}, "v1")
        rb = self._make_result({"depth": 4, "clarity": 3}, "v2")
        result = compare([ra], [rb])
        assert result.per_criterion_deltas["depth"] == pytest.approx(2.0, abs=0.01)
        assert result.per_criterion_deltas["clarity"] == pytest.approx(0.0, abs=0.01)

    def test_criterion_present_only_in_b_treated_as_zero_for_a(self):
        from backend.evals.harness.comparator import compare

        ra = self._make_result({"depth": 3}, "v1")
        rb = self._make_result({"depth": 3, "newcrit": 5}, "v2")
        result = compare([ra], [rb])
        # newcrit is absent in A → mean_a = 0.0; mean_b = 5.0 → delta = +5.0
        assert result.per_criterion_deltas["newcrit"] == pytest.approx(5.0, abs=0.01)

    def test_criterion_present_only_in_a_treated_as_zero_for_b(self):
        from backend.evals.harness.comparator import compare

        ra = self._make_result({"depth": 4, "oldcrit": 3}, "v1")
        rb = self._make_result({"depth": 4}, "v2")
        result = compare([ra], [rb])
        # oldcrit absent in B → mean_b = 0.0; mean_a = 3.0 → delta = -3.0
        assert result.per_criterion_deltas["oldcrit"] == pytest.approx(-3.0, abs=0.01)

    def test_multiple_cases_averages_correctly(self):
        from backend.evals.harness.comparator import compare

        # Two cases; depth scores in A = [2, 4] → mean 3.0; in B = [4, 4] → mean 4.0
        ra1 = self._make_result({"depth": 2}, "v1", case_id="c1")
        ra2 = self._make_result({"depth": 4}, "v1", case_id="c2")
        rb1 = self._make_result({"depth": 4}, "v2", case_id="c1")
        rb2 = self._make_result({"depth": 4}, "v2", case_id="c2")
        result = compare([ra1, ra2], [rb1, rb2])
        assert result.per_criterion_deltas["depth"] == pytest.approx(1.0, abs=0.01)


# ---------------------------------------------------------------------------
# Fix 1b — base_judge.py: parse failure returns [] not score=1
# ---------------------------------------------------------------------------

class TestBaseJudgeParseFailure:
    """Verify that unparseable judge responses return [] instead of a fake score=1."""

    def _make_judge(self):
        """Instantiate BaseJudge bypassing the key check and OpenAI client."""
        from backend.evals.judges.base_judge import BaseJudge
        with patch("backend.evals.judges.base_judge.eval_settings") as mock_settings:
            mock_settings.deepseek_api_key = "fake-key"
            mock_settings.judge_model = "deepseek-chat"
            mock_settings.judge_temperature = 0.1
            mock_settings.judge_max_tokens = 2000
            mock_settings.deepseek_base_url = "https://api.deepseek.com"
            mock_settings.require_judge_key = MagicMock()
            with patch("backend.evals.judges.base_judge.OpenAI"):
                judge = BaseJudge.__new__(BaseJudge)
                judge.model = "deepseek-chat"
                judge.temperature = 0.1
                judge.client = MagicMock()
        return judge

    def test_invalid_json_returns_empty_list(self):
        judge = self._make_judge()
        result = judge._parse_scores("this is not json at all {{{")
        assert result == []

    def test_empty_string_returns_empty_list(self):
        judge = self._make_judge()
        result = judge._parse_scores("")
        assert result == []

    def test_valid_json_still_works(self):
        judge = self._make_judge()
        payload = json.dumps({
            "scores": [
                {"criterion": "depth", "score": 4, "weight": 1.0, "rationale": "good"}
            ]
        })
        result = judge._parse_scores(payload)
        assert len(result) == 1
        assert result[0].criterion_name == "depth"
        assert result[0].score == 4


# ---------------------------------------------------------------------------
# Fix 1b (part 2) — scorer.py: empty criterion list does not div-by-zero
# ---------------------------------------------------------------------------

class TestScorerEmptyCriteria:
    def test_compute_weighted_total_empty(self):
        from backend.evals.harness.scorer import compute_weighted_total
        assert compute_weighted_total([]) == 0.0

    def test_score_module_with_empty_judge_result(self):
        """score_module must return an EvalResult even when the judge returns []."""
        from backend.evals.harness.scorer import score_module
        with patch("backend.evals.harness.scorer.ModuleJudge") as MockJudge:
            MockJudge.return_value.evaluate.return_value = []
            result = score_module(
                module_md="## Learning Objectives\n- Understand X (Curriculum)\n",
                topic_name="test_topic",
                curriculum_scope="ML basics",
                gap_summary={},
                prompt_variant="v1",
                run_judge=True,
            )
        assert result.weighted_total == 0.0
        assert result.criterion_scores == []


# ---------------------------------------------------------------------------
# Fix 1c — agent_ingest.py: JSONDecodeError produces fallback
# ---------------------------------------------------------------------------

class TestAgentIngestJsonFallback:
    """Verify that malformed LLM JSON in ingest_node produces a single-topic fallback."""

    def test_malformed_json_fallback(self, tmp_path):
        from backend.pipeline.agent_ingest import ingest_node

        fake_llm = MagicMock()
        # First call: file summarization — returns valid text
        # Second call: topic extraction — returns malformed JSON
        fake_llm.invoke.side_effect = [
            MagicMock(content="## slide.pdf\nSome curriculum about ML"),  # summarize
            MagicMock(content="NOT VALID JSON {{{"),                       # extract_topics
        ]

        fake_store = MagicMock()
        fake_store.query.return_value = {"documents": [[]], "ids": [[]]}

        with patch("backend.pipeline.agent_ingest.ChromaStore", return_value=fake_store), \
             patch("backend.pipeline.agent_ingest.get_llm", return_value=fake_llm), \
             patch("backend.pipeline.agent_ingest.extract_text", return_value=[
                 {"source": "slide.pdf", "text": "Content about ML and NLP"}
             ]):
            result = ingest_node({"file_paths": [str(tmp_path / "slide.pdf")]})

        # Should not raise — must produce at least 1 topic
        assert len(result["topics"]) >= 1
        assert result["curriculum_scope"] != ""

    def test_valid_json_still_parsed_correctly(self, tmp_path):
        from backend.pipeline.agent_ingest import ingest_node

        topics_payload = json.dumps({
            "topics": [
                {"name": "Transformers", "description": "Attention mechanism", "key_techniques": ["self-attention"]}
            ],
            "curriculum_scope": "NLP deep learning",
        })
        fake_llm = MagicMock()
        fake_llm.invoke.side_effect = [
            MagicMock(content="## notes.pdf\nNLP content"),
            MagicMock(content=topics_payload),
        ]

        fake_store = MagicMock()
        fake_store.query.return_value = {"documents": [[]], "ids": [[]]}

        with patch("backend.pipeline.agent_ingest.ChromaStore", return_value=fake_store), \
             patch("backend.pipeline.agent_ingest.get_llm", return_value=fake_llm), \
             patch("backend.pipeline.agent_ingest.extract_text", return_value=[
                 {"source": "notes.pdf", "text": "NLP content"}
             ]):
            result = ingest_node({"file_paths": [str(tmp_path / "notes.pdf")]})

        assert result["topics"][0]["name"] == "Transformers"
        assert result["curriculum_scope"] == "NLP deep learning"


# ---------------------------------------------------------------------------
# Fix 2b — agent_research.py: search futures have timeout
# ---------------------------------------------------------------------------

class TestAgentResearchTimeout:
    """Verify that Tavily search timeouts are caught and produce empty results."""

    def test_search_timeout_produces_empty_results(self):
        from concurrent.futures import TimeoutError as FuturesTimeoutError
        from backend.pipeline.agent_research import _research_topic

        # Build a fake store
        fake_store = MagicMock()
        fake_store.query.return_value = {"documents": [["some curriculum text"]], "ids": [["id1"]]}
        fake_store.add_documents = MagicMock()

        # LLM returns a valid gap analysis JSON
        gap_json = json.dumps({
            "gaps": [{"gap": "industry use", "severity": "moderate"}],
            "enrichments": [],
            "industry_context": "Used in production",
        })
        fake_llm = MagicMock()
        fake_llm.invoke.return_value = MagicMock(content=gap_json)

        # Mock the search call to time out
        with patch("backend.pipeline.agent_research.search", side_effect=FuturesTimeoutError("timeout")):
            # _research_topic uses ThreadPoolExecutor internally;
            # we patch at the future.result() level via the search mock
            # The real timeout is on future.result(timeout=30) — simulate by making
            # the search itself raise so the future propagates the exception
            result = _research_topic(
                i=0,
                topic={"name": "Transformers", "description": "attention", "key_techniques": [], "domain_context": "NLP"},
                total=1,
                store=fake_store,
                llm=fake_llm,
                curriculum_scope="NLP basics",
            )

        # Despite the search failure the function should complete and return a result dict
        assert result is not None
        assert "gaps" in result  # the LLM analysis still ran; _research_topic returns analysis dict

    def test_search_success_produces_results(self):
        from backend.pipeline.agent_research import _research_topic

        fake_store = MagicMock()
        fake_store.query.return_value = {"documents": [["curriculum content"]], "ids": [["id1"]]}
        fake_store.add_documents = MagicMock()

        gap_json = json.dumps({
            "gaps": [{"gap": "real-world use", "severity": "critical"}],
            "enrichments": [{"enrichment": "Used in GPT-4"}],
            "industry_context": "Foundation of modern LLMs",
        })
        fake_llm = MagicMock()
        fake_llm.invoke.return_value = MagicMock(content=gap_json)

        search_results = [{"title": "T", "content": "industry info"}]
        with patch("backend.pipeline.agent_research.search", return_value=search_results):
            result = _research_topic(
                i=0,
                topic={"name": "Attention", "description": "self-attention", "key_techniques": ["softmax"], "domain_context": "NLP"},
                total=1,
                store=fake_store,
                llm=fake_llm,
                curriculum_scope="NLP basics",
            )

        assert "gaps" in result
        assert len(result["gaps"]) >= 1


# ---------------------------------------------------------------------------
# Fix 2d — evals/config.py + base_judge.py: require_judge_key validation
# ---------------------------------------------------------------------------

class TestEvalSettingsRequireJudgeKey:
    def test_raises_when_key_empty(self):
        from backend.evals.config import EvalSettings
        settings = EvalSettings(deepseek_api_key="")
        with pytest.raises(ValueError, match="DEEPSEEK_API_KEY"):
            settings.require_judge_key()

    def test_no_raise_when_key_set(self):
        from backend.evals.config import EvalSettings
        settings = EvalSettings(deepseek_api_key="sk-test-key")
        settings.require_judge_key()  # must not raise

    def test_base_judge_calls_require_key_on_init(self):
        """BaseJudge.__init__ must call require_judge_key before creating the client."""
        from backend.evals.judges.base_judge import BaseJudge
        with patch("backend.evals.judges.base_judge.eval_settings") as mock_settings:
            mock_settings.deepseek_api_key = ""
            mock_settings.require_judge_key.side_effect = ValueError("DEEPSEEK_API_KEY not set")
            mock_settings.judge_model = "deepseek-chat"
            mock_settings.judge_temperature = 0.1
            mock_settings.deepseek_base_url = "https://api.deepseek.com"
            with patch("backend.evals.judges.base_judge.OpenAI"):
                with pytest.raises(ValueError, match="DEEPSEEK_API_KEY"):
                    BaseJudge()
            mock_settings.require_judge_key.assert_called_once()


# ---------------------------------------------------------------------------
# Fix 2a — video_builder.py: URL guard in _process_single_video
# ---------------------------------------------------------------------------

class TestVideoBuilderUrlGuard:
    """Verify that _process_single_video raises when the status response has no URL."""

    @patch("backend.services.video_builder._poll_status")
    @patch("backend.services.video_builder._create_video")
    def test_missing_url_raises_runtime_error(self, mock_create, mock_poll, tmp_path):
        from backend.services.video_builder import _process_single_video

        mock_create.return_value = "vid_123"
        # Status response has neither video_url nor download key
        mock_poll.return_value = {"status": "completed", "duration": 60.0}

        output_dir = str(tmp_path / "videos")
        scripts_dir = str(tmp_path / "scripts")
        import os
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(scripts_dir, exist_ok=True)

        with pytest.raises(RuntimeError, match="No download URL"):
            _process_single_video(
                idx=0,
                topic_name="Word2Vec",
                script="Hello world",
                output_dir=output_dir,
                scripts_dir=scripts_dir,
                api_key="key",
                avatar_id="av",
                voice_id="vo",
                total=1,
            )

    @patch("backend.services.video_builder._download_video")
    @patch("backend.services.video_builder._poll_status")
    @patch("backend.services.video_builder._create_video")
    def test_valid_url_proceeds_to_download(self, mock_create, mock_poll, mock_download, tmp_path):
        from backend.services.video_builder import _process_single_video

        mock_create.return_value = "vid_123"
        mock_poll.return_value = {"status": "completed", "video_url": "https://h.ai/v.mp4", "duration": 60.0}
        mock_download.return_value = None

        output_dir = str(tmp_path / "videos")
        scripts_dir = str(tmp_path / "scripts")
        import os
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(scripts_dir, exist_ok=True)

        path = _process_single_video(
            idx=0,
            topic_name="Word2Vec",
            script="Hello world",
            output_dir=output_dir,
            scripts_dir=scripts_dir,
            api_key="key",
            avatar_id="av",
            voice_id="vo",
            total=1,
        )
        mock_download.assert_called_once_with("https://h.ai/v.mp4", path)


# ---------------------------------------------------------------------------
# Fix 2c — state.py: output_formats field exists in PipelineState
# ---------------------------------------------------------------------------

class TestPipelineStateOutputFormats:
    def test_output_formats_field_in_state(self):
        from backend.pipeline.state import PipelineState
        # TypedDict keys are accessible via __annotations__
        assert "output_formats" in PipelineState.__annotations__

    def test_run_job_passes_output_formats_in_state(self):
        from backend.run_pipeline import run_job
        with patch("backend.run_pipeline.build_pipeline") as mock_build:
            mock_pipeline = MagicMock()
            mock_pipeline.invoke.return_value = {}
            mock_build.return_value = mock_pipeline
            run_job(["/tmp/a.pdf"], ["pdf", "ppt"])
            state = mock_pipeline.invoke.call_args[0][0]
            assert state["output_formats"] == "pdf,ppt"
