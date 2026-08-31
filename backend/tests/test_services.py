"""Tests for backend services: llm.py, web_search.py, and ChromaStore edge cases.

All external API calls (OpenAI, Tavily) are mocked.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch



# ===========================================================================
# get_llm — tier routing
# ===========================================================================


class TestGetLlm:
    """Tests for get_llm() tier routing in backend.services.llm."""

    def _call_get_llm(self, tier, temperature=None):
        """Call get_llm with all external deps mocked."""
        from backend.services.llm import get_llm

        with patch("backend.services.llm.ChatOpenAI") as MockChatOpenAI:
            with patch("backend.services.llm.settings") as mock_settings:
                mock_settings.openai_api_key = "test-key"
                mock_settings.openai_model_nano = "gpt-4o-mini"
                mock_settings.openai_model_mini = "gpt-4o-mini"
                mock_settings.openai_model_premium = "gpt-4o"
                mock_settings.temp_analysis = 0.0
                mock_settings.temp_structured = 0.2
                mock_settings.temp_creative = 0.7

                if temperature is not None:
                    result = get_llm(tier, temperature=temperature)
                else:
                    result = get_llm(tier)
                return result, MockChatOpenAI

    def test_nano_tier_creates_chat_openai(self):
        _, MockChatOpenAI = self._call_get_llm("nano")
        MockChatOpenAI.assert_called_once()
        call_kwargs = MockChatOpenAI.call_args
        # Should use the nano model
        assert "gpt-4o-mini" in str(call_kwargs)

    def test_mini_tier_creates_chat_openai(self):
        _, MockChatOpenAI = self._call_get_llm("mini")
        MockChatOpenAI.assert_called_once()

    def test_premium_tier_creates_chat_openai(self):
        _, MockChatOpenAI = self._call_get_llm("premium")
        MockChatOpenAI.assert_called_once()
        call_kwargs = MockChatOpenAI.call_args
        assert "gpt-4o" in str(call_kwargs)

    def test_full_alias_accepted(self):
        """'full' is a backward-compat alias for 'premium'."""
        _, MockChatOpenAI = self._call_get_llm("full")
        MockChatOpenAI.assert_called_once()

    def test_temperature_override_is_used(self):
        from backend.services.llm import get_llm

        with patch("backend.services.llm.ChatOpenAI") as MockChatOpenAI:
            with patch("backend.services.llm.settings") as mock_settings:
                mock_settings.openai_api_key = "test-key"
                mock_settings.openai_model_mini = "gpt-4o-mini"
                mock_settings.temp_structured = 0.2

                get_llm("mini", temperature=0.9)

                call_kwargs = MockChatOpenAI.call_args
                assert "0.9" in str(call_kwargs) or 0.9 in call_kwargs[1].values() or 0.9 in call_kwargs[0]

    def test_unknown_tier_falls_back_silently(self):
        """Unknown tier should NOT raise — it silently falls back to 'mini'."""
        from backend.services.llm import get_llm

        with patch("backend.services.llm.ChatOpenAI") as MockChatOpenAI:
            with patch("backend.services.llm.settings") as mock_settings:
                mock_settings.openai_api_key = "test-key"
                mock_settings.openai_model_mini = "gpt-4o-mini"
                mock_settings.temp_structured = 0.2

                # Should not raise
                get_llm("turbo_does_not_exist")
                MockChatOpenAI.assert_called_once()

    def test_get_llm_returns_callable_object(self):
        result, _ = self._call_get_llm("mini")
        # The mock result is the ChatOpenAI instance, should be non-None
        assert result is not None


# ===========================================================================
# web_search — search()
# ===========================================================================


class TestWebSearch:
    """Tests for search() in backend.services.web_search."""

    def setup_method(self):
        """Reset the singleton client before each test."""
        import backend.services.web_search as ws_module
        ws_module._client = None

    def test_happy_path_returns_results(self):
        from backend.services.web_search import search

        mock_client = MagicMock()
        mock_client.search.return_value = {
            "results": [
                {"title": "Paper 1", "content": "About transformers", "url": "http://a.com", "score": 0.9},
                {"title": "Paper 2", "content": "About BERT", "url": "http://b.com", "score": 0.8},
            ]
        }

        with patch("backend.services.web_search.TavilyClient", return_value=mock_client):
            with patch("backend.services.web_search.settings") as mock_settings:
                mock_settings.tavily_api_key = "test-key"
                results = search("transformer architecture")

        assert len(results) == 2
        assert results[0]["title"] == "Paper 1"

    def test_empty_results_returns_empty_list(self):
        from backend.services.web_search import search

        mock_client = MagicMock()
        mock_client.search.return_value = {"results": []}

        with patch("backend.services.web_search.TavilyClient", return_value=mock_client):
            with patch("backend.services.web_search.settings") as mock_settings:
                mock_settings.tavily_api_key = "test-key"
                results = search("obscure topic with no results")

        assert results == []

    def test_missing_results_key_returns_empty_list(self):
        from backend.services.web_search import search

        mock_client = MagicMock()
        mock_client.search.return_value = {}  # no "results" key

        with patch("backend.services.web_search.TavilyClient", return_value=mock_client):
            with patch("backend.services.web_search.settings") as mock_settings:
                mock_settings.tavily_api_key = "test-key"
                results = search("anything")

        assert results == []

    def test_client_exception_returns_empty_list(self):
        """Tavily errors are caught gracefully and return an empty list."""
        from backend.services.web_search import search

        mock_client = MagicMock()
        mock_client.search.side_effect = RuntimeError("Network error")

        with patch("backend.services.web_search.TavilyClient", return_value=mock_client):
            with patch("backend.services.web_search.settings") as mock_settings:
                mock_settings.tavily_api_key = "test-key"
                result = search("any query")
                assert result == []

    def test_max_results_passed_to_client(self):
        from backend.services.web_search import search

        mock_client = MagicMock()
        mock_client.search.return_value = {"results": []}

        with patch("backend.services.web_search.TavilyClient", return_value=mock_client):
            with patch("backend.services.web_search.settings") as mock_settings:
                mock_settings.tavily_api_key = "test-key"
                search("query", max_results=3)

        call_kwargs = mock_client.search.call_args
        assert call_kwargs[1]["max_results"] == 3 or 3 in call_kwargs[0]

    def test_singleton_client_reused(self):
        """_get_client() only creates TavilyClient once per process."""
        from backend.services.web_search import search

        mock_client = MagicMock()
        mock_client.search.return_value = {"results": []}

        with patch("backend.services.web_search.TavilyClient", return_value=mock_client) as MockClient:
            with patch("backend.services.web_search.settings") as mock_settings:
                mock_settings.tavily_api_key = "test-key"
                search("query 1")
                search("query 2")

            # TavilyClient constructor should only be called once
            assert MockClient.call_count == 1
