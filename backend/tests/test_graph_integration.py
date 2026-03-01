"""LangGraph pipeline integration tests.

Tests the compiled graph structure and node routing using mocked agent functions.
No real LLMs, no ChromaDB, no external API calls.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestBuildPipeline:
    """Tests that build_pipeline() compiles and exposes the right structure."""

    def test_build_pipeline_compiles_without_error(self):
        from backend.pipeline.graph import build_pipeline

        pipeline = build_pipeline()
        assert pipeline is not None

    def test_compiled_graph_is_invocable(self):
        """build_pipeline() returns a compiled graph that has an invoke method."""
        from backend.pipeline.graph import build_pipeline

        pipeline = build_pipeline()
        assert callable(getattr(pipeline, "invoke", None))

    def test_graph_has_ingest_node(self):
        from backend.pipeline.graph import build_pipeline

        pipeline = build_pipeline()
        node_ids = {node.id for node in pipeline.get_graph().nodes.values()}
        assert "ingest" in node_ids

    def test_graph_has_research_node(self):
        from backend.pipeline.graph import build_pipeline

        pipeline = build_pipeline()
        node_ids = {node.id for node in pipeline.get_graph().nodes.values()}
        assert "research" in node_ids

    def test_graph_has_generate_node(self):
        from backend.pipeline.graph import build_pipeline

        pipeline = build_pipeline()
        node_ids = {node.id for node in pipeline.get_graph().nodes.values()}
        assert "generate" in node_ids


class TestGraphNodeRouting:
    """Tests that the pipeline routes state through all three nodes in order."""

    def test_pipeline_routes_through_all_three_nodes(self, base_pipeline_state):
        from backend.pipeline.graph import build_pipeline

        with (
            patch("backend.pipeline.graph.ingest_node") as mock_ingest,
            patch("backend.pipeline.graph.research_node") as mock_research,
            patch("backend.pipeline.graph.generate_node") as mock_generate,
        ):
            mock_ingest.return_value = {
                "topics": [{"name": "Transformers", "description": "Attention", "key_techniques": []}],
                "raw_text": "Some curriculum text",
                "curriculum_scope": "NLP basics",
                "current_stage": "ingested",
            }
            mock_research.return_value = {
                "gap_summary": [{"topic": "Transformers", "gaps": [], "enrichments": []}],
                "current_stage": "researched",
            }
            mock_generate.return_value = {
                "pdf_path": "/tmp/output.pdf",
                "ppt_path": "",
                "video_dir": "",
                "current_stage": "complete",
            }

            pipeline = build_pipeline()
            result = pipeline.invoke(base_pipeline_state)

        mock_ingest.assert_called_once()
        mock_research.assert_called_once()
        mock_generate.assert_called_once()

    def test_pipeline_final_stage_is_complete(self, base_pipeline_state):
        from backend.pipeline.graph import build_pipeline

        with (
            patch("backend.pipeline.graph.ingest_node") as mock_ingest,
            patch("backend.pipeline.graph.research_node") as mock_research,
            patch("backend.pipeline.graph.generate_node") as mock_generate,
        ):
            mock_ingest.return_value = {
                "topics": [],
                "raw_text": "",
                "curriculum_scope": "",
                "current_stage": "ingested",
            }
            mock_research.return_value = {
                "gap_summary": [],
                "current_stage": "researched",
            }
            mock_generate.return_value = {
                "pdf_path": "/tmp/output.pdf",
                "ppt_path": "",
                "video_dir": "",
                "current_stage": "complete",
            }

            pipeline = build_pipeline()
            result = pipeline.invoke(base_pipeline_state)

        assert result["current_stage"] == "complete"

    def test_state_propagates_between_nodes(self, base_pipeline_state):
        """State keys from ingest are visible when research is called."""
        from backend.pipeline.graph import build_pipeline

        captured_research_input = {}

        def fake_research(state):
            captured_research_input.update(state)
            return {"gap_summary": [], "current_stage": "researched"}

        with (
            patch("backend.pipeline.graph.ingest_node") as mock_ingest,
            patch("backend.pipeline.graph.research_node", side_effect=fake_research),
            patch("backend.pipeline.graph.generate_node") as mock_generate,
        ):
            mock_ingest.return_value = {
                "topics": [{"name": "BERT"}],
                "raw_text": "curriculum text",
                "curriculum_scope": "NLP",
                "current_stage": "ingested",
            }
            mock_generate.return_value = {
                "pdf_path": "",
                "ppt_path": "",
                "video_dir": "",
                "current_stage": "complete",
            }

            pipeline = build_pipeline()
            pipeline.invoke(base_pipeline_state)

        # research_node received the state with topics from ingest_node
        assert "topics" in captured_research_input
        assert captured_research_input["topics"] == [{"name": "BERT"}]
