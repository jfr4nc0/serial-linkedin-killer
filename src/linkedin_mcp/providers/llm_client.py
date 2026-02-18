"""LLM client factory supporting local OpenAI-compatible, Google Gemini, and AWS Bedrock providers."""

import os

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from src.config.config_loader import load_config

_llm_cache: dict[str, BaseChatModel] = {}


def get_llm_client() -> BaseChatModel:
    """Get a cached LLM client configured from LLMConfig (config/agent.yaml).

    Provider selection priority: LLM_PROVIDER env var > llm.provider in config > default "local"

    Supported providers:
    - "local": Returns ChatOpenAI configured for local llama.cpp server
    - "gemini": Returns ChatGoogleGenerativeAI configured for Google Gemini API
    - "bedrock": Returns ChatBedrockConverse configured for AWS Bedrock.
                 Auth via AWS_BEARER_TOKEN_BEDROCK env var (long-term API key) or
                 standard AWS credential chain (AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY).

    Returns:
        BaseChatModel: Configured LLM client

    Raises:
        ValueError: If provider is not "local", "gemini", or "bedrock"
    """
    config = load_config()
    provider = os.getenv("LLM_PROVIDER", config.llm.provider).lower()

    if provider in _llm_cache:
        return _llm_cache[provider]

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        client = ChatGoogleGenerativeAI(
            model=config.llm.gemini_model,
            google_api_key=os.getenv("GEMINI_API_KEY"),
            temperature=config.llm.temperature,
            max_output_tokens=config.llm.max_tokens,
        )
    elif provider == "local":
        client = ChatOpenAI(
            base_url=config.llm.base_url,
            api_key=config.llm.api_key,
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens,
        )
    elif provider == "bedrock":
        from langchain_aws import ChatBedrockConverse

        region = os.getenv("AWS_DEFAULT_REGION", config.llm.bedrock_region)
        bedrock_kwargs: dict = dict(
            model_id=config.llm.bedrock_model,
            region_name=region,
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens,
        )
        if config.llm.bedrock_provider:
            bedrock_kwargs["provider"] = config.llm.bedrock_provider
        client = ChatBedrockConverse(**bedrock_kwargs)
    else:
        raise ValueError(
            f"Unknown LLM provider: '{provider}'. Must be 'local', 'gemini', or 'bedrock'. "
            f"Set via LLM_PROVIDER env var or llm.provider in config/agent.yaml."
        )

    _llm_cache[provider] = client
    return client
