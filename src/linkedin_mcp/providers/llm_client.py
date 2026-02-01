"""LLM client using local llama.cpp via OpenAI-compatible API."""

from langchain_openai import ChatOpenAI

from src.config.config_loader import load_config

_llm_cache: dict = {}


def get_llm_client() -> ChatOpenAI:
    """Get a cached ChatOpenAI client configured from LLMConfig (config/agent.yaml).

    Returns:
        Configured ChatOpenAI client pointing at the local inference server.
    """
    if "default" in _llm_cache:
        return _llm_cache["default"]

    config = load_config()

    client = ChatOpenAI(
        base_url=config.llm.base_url,
        api_key=config.llm.api_key,
        temperature=config.llm.temperature,
        max_tokens=config.llm.max_tokens,
    )
    _llm_cache["default"] = client
    return client
