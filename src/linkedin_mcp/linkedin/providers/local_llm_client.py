"""LLM client using local llama.cpp via OpenAI-compatible API."""

from langchain_openai import ChatOpenAI

from src.config.config_loader import load_config


def get_local_llm_client(config_path: str = None) -> ChatOpenAI:
    """Get a ChatOpenAI client configured for local llama.cpp inference.

    Reads base_url, api_key, temperature, and max_tokens from config/agent.yaml
    under the llm.* section.
    """
    config = load_config(config_path)

    return ChatOpenAI(
        base_url=config.llm.base_url,
        api_key=config.llm.api_key,
        temperature=config.llm.temperature,
        max_tokens=config.llm.max_tokens,
    )
