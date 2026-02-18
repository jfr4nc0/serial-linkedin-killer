"""Integration tests for AWS Bedrock LLM provider.

These tests make real calls to AWS Bedrock and require:
  - AWS_BEARER_TOKEN_BEDROCK in .env (long-term API key)
  - AWS_DEFAULT_REGION in .env or bedrock_region in config/agent.yaml

Run with: poetry run pytest tests/test_bedrock_integration.py -v
"""

import pytest
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

load_dotenv()  # Load AWS_BEARER_TOKEN_BEDROCK and other vars from .env


@pytest.fixture(autouse=True)
def reset_caches():
    """Clear LLM client and config caches before/after each test to ensure env overrides take effect."""
    import src.config.config_loader as cfg_module
    import src.core.providers.llm_client as core_llm_module
    import src.linkedin_mcp.providers.llm_client as mcp_llm_module

    core_llm_module._llm_cache.clear()
    mcp_llm_module._llm_cache.clear()
    cfg_module._cached_config = None
    yield
    core_llm_module._llm_cache.clear()
    mcp_llm_module._llm_cache.clear()
    cfg_module._cached_config = None


def test_core_bedrock_client_instantiates(monkeypatch):
    """Core LLM client with provider=bedrock should return a ChatBedrockConverse instance.

    When Langfuse is configured the client is wrapped in a RunnableBinding,
    so we unwrap it to check the underlying model type.
    """
    from langchain_aws import ChatBedrockConverse
    from langchain_core.runnables import RunnableBinding

    monkeypatch.setenv("LLM_PROVIDER", "bedrock")

    from src.core.providers.llm_client import get_llm_client

    client = get_llm_client()
    # Unwrap RunnableBinding added by Langfuse with_config if present
    underlying = client.bound if isinstance(client, RunnableBinding) else client

    assert isinstance(underlying, ChatBedrockConverse)


def test_core_bedrock_client_real_response(monkeypatch):
    """Core LLM client with provider=bedrock gets a real non-empty response from AWS Bedrock."""
    monkeypatch.setenv("LLM_PROVIDER", "bedrock")

    from src.core.providers.llm_client import get_llm_client

    client = get_llm_client()
    response = client.invoke([HumanMessage(content="Reply with a single word: hello")])

    assert response.content, "Expected non-empty response content from Bedrock"
    assert isinstance(response.content, str)
    print(f"\nBedrock response (core): {response.content!r}")


def test_core_bedrock_client_is_cached(monkeypatch):
    """Subsequent calls with the same provider return the cached client instance."""
    from src.core.providers.llm_client import _llm_cache, get_llm_client

    monkeypatch.setenv("LLM_PROVIDER", "bedrock")

    client1 = get_llm_client()
    client2 = get_llm_client()

    assert client1 is client2
    assert "bedrock" in _llm_cache


def test_mcp_bedrock_client_instantiates(monkeypatch):
    """LinkedIn MCP LLM client with provider=bedrock should return a ChatBedrockConverse instance."""
    from langchain_aws import ChatBedrockConverse

    monkeypatch.setenv("LLM_PROVIDER", "bedrock")

    from src.linkedin_mcp.providers.llm_client import get_llm_client

    client = get_llm_client()

    assert isinstance(client, ChatBedrockConverse)


def test_mcp_bedrock_client_real_response(monkeypatch):
    """LinkedIn MCP LLM client with provider=bedrock gets a real non-empty response from AWS Bedrock."""
    monkeypatch.setenv("LLM_PROVIDER", "bedrock")

    from src.linkedin_mcp.providers.llm_client import get_llm_client

    client = get_llm_client()
    response = client.invoke([HumanMessage(content="Reply with a single word: hello")])

    assert response.content, "Expected non-empty response content from Bedrock"
    assert isinstance(response.content, str)
    print(f"\nBedrock response (mcp): {response.content!r}")
