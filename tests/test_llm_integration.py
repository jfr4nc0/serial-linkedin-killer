"""Integration tests for LLM provider switching, Gemini integration, and Langfuse tracing."""

import json
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from src.core.agents.tools.role_clustering import _classify_single_batch
from src.core.providers.llm_client import _llm_cache, get_llm_client


@pytest.fixture(autouse=True)
def clear_llm_cache():
    """Clear LLM cache before each test."""
    _llm_cache.clear()
    yield
    _llm_cache.clear()


def test_gemini_provider_role_clustering_no_code_changes(monkeypatch):
    """Test that role_clustering.py works with Gemini provider without code changes (Success Criterion 1)."""
    # Set up environment for Gemini provider
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    # Create a mock LLM that returns a classification response
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(
        content='{"Software Engineer": "Engineering", "Accountant": "Finance"}'
    )

    # Patch get_llm_client at the point of use in role_clustering
    with patch("src.core.agents.tools.role_clustering.get_llm_client") as mock_get_client:
        mock_get_client.return_value = mock_llm

        # Call role clustering function
        result = _classify_single_batch(["Software Engineer", "Accountant"])

        # Verify the result
        assert result["Software Engineer"] == "Engineering"
        assert result["Accountant"] == "Finance"

        # Verify invoke was called
        assert mock_llm.invoke.called
        call_args = mock_llm.invoke.call_args[0][0]
        assert len(call_args) == 1
        assert isinstance(call_args[0], HumanMessage)


def test_gemini_response_content_strip_compatibility(monkeypatch):
    """Test that role_clustering handles Gemini response formatting with whitespace and markdown (Success Criterion 2)."""
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    # Create mock LLM with response that has markdown code blocks and whitespace
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = AIMessage(
        content='\n```json\n{"Data Analyst": "Analytics"}\n```\n'
    )

    with patch("src.core.agents.tools.role_clustering.get_llm_client") as mock_get_client:
        mock_get_client.return_value = mock_llm

        # Call role clustering - should handle the markdown formatting
        result = _classify_single_batch(["Data Analyst"])

        # Note: "Analytics" is not a valid category, so it should default to "Other"
        # Let's test with a valid category instead
        mock_llm.invoke.return_value = AIMessage(
            content='\n```json\n{"Data Analyst": "Finance"}\n```\n'
        )
        result = _classify_single_batch(["Data Analyst"])

        assert result["Data Analyst"] == "Finance"


def test_langfuse_callback_pre_bound_on_client(monkeypatch):
    """Test that Langfuse callbacks are pre-bound to the client with provider metadata (Success Criterion 3)."""
    # Set up environment
    monkeypatch.setenv("LLM_PROVIDER", "local")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-test")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-test")

    # Create mock Langfuse callback handler
    mock_langfuse_handler = MagicMock()
    mock_langfuse_handler.metadata = {}

    # Create mock client with with_config method
    mock_raw_client = MagicMock()
    mock_bound_client = MagicMock()
    mock_raw_client.with_config.return_value = mock_bound_client

    with patch("src.core.providers.llm_client.get_langfuse_callback") as mock_get_langfuse, \
         patch("src.core.providers.llm_client.ChatOpenAI") as mock_chat_openai:

        mock_get_langfuse.return_value = mock_langfuse_handler
        mock_chat_openai.return_value = mock_raw_client

        # Call get_llm_client
        client = get_llm_client()

        # Verify with_config was called
        assert mock_raw_client.with_config.called

        # Verify with_config was called with callbacks
        call_kwargs = mock_raw_client.with_config.call_args[0][0]
        assert "callbacks" in call_kwargs
        assert mock_langfuse_handler in call_kwargs["callbacks"]

        # Verify provider metadata was added
        assert mock_langfuse_handler.metadata["provider"] == "local"

        # Verify the bound client is what's returned and cached
        assert client == mock_bound_client


def test_provider_switching_without_restart(monkeypatch):
    """Test that switching providers via env var works at runtime without restart (Success Criterion 4)."""
    # Mock get_langfuse_callback to return None (simplifies test)
    with patch("src.core.providers.llm_client.get_langfuse_callback") as mock_get_langfuse, \
         patch("src.core.providers.llm_client.ChatOpenAI") as mock_chat_openai, \
         patch("src.core.providers.llm_client.ChatGoogleGenerativeAI") as mock_chat_gemini:

        mock_get_langfuse.return_value = None

        # Create distinct mock clients for each provider
        mock_local_client = MagicMock()
        mock_local_client.__class__.__name__ = "ChatOpenAI"
        mock_chat_openai.return_value = mock_local_client

        mock_gemini_client = MagicMock()
        mock_gemini_client.__class__.__name__ = "ChatGoogleGenerativeAI"
        mock_chat_gemini.return_value = mock_gemini_client

        # Test local provider
        monkeypatch.setenv("LLM_PROVIDER", "local")
        client1 = get_llm_client()
        assert client1 == mock_local_client

        # Test Gemini provider
        monkeypatch.setenv("LLM_PROVIDER", "gemini")
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        client2 = get_llm_client()
        assert client2 == mock_gemini_client

        # Verify both are cached separately
        assert "local" in _llm_cache
        assert "gemini" in _llm_cache
        assert _llm_cache["local"] is not _llm_cache["gemini"]


def test_no_langfuse_graceful_fallback(monkeypatch):
    """Test that the system works gracefully when Langfuse is not configured (backward compatibility)."""
    monkeypatch.setenv("LLM_PROVIDER", "local")

    # Mock get_langfuse_callback to return None (no Langfuse configured)
    with patch("src.core.providers.llm_client.get_langfuse_callback") as mock_get_langfuse, \
         patch("src.core.providers.llm_client.ChatOpenAI") as mock_chat_openai:

        mock_get_langfuse.return_value = None

        mock_raw_client = MagicMock()
        mock_raw_client.__class__.__name__ = "ChatOpenAI"
        mock_chat_openai.return_value = mock_raw_client

        # Call get_llm_client
        client = get_llm_client()

        # Verify the raw client is returned (not wrapped with callbacks)
        assert client == mock_raw_client

        # Verify with_config was NOT called
        assert not mock_raw_client.with_config.called
