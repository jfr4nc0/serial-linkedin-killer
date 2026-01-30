import os

_llm_cache: dict = {}


def get_llm_client(
    model_name: str = "Qwen/Qwen3-30B-A3B-Thinking-2507",
):
    """
    Get a cached ChatHuggingFace client configured for Hugging Face Serverless API.

    Args:
        model_name: The model name to use (defaults to Qwen3-30B-A3B-Thinking)

    Returns:
        Configured ChatHuggingFace client pointing to HF Serverless API
    """
    if model_name in _llm_cache:
        return _llm_cache[model_name]

    from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

    hf_token = os.getenv("HUGGING_FACE_HUB_TOKEN")
    if not hf_token:
        raise ValueError("HUGGING_FACE_HUB_TOKEN environment variable is required")

    llm = HuggingFaceEndpoint(
        repo_id=model_name,
        huggingfacehub_api_token=hf_token,
        temperature=0.1,
        max_new_tokens=2000,
        timeout=300,
        streaming=False,
        task="text-generation",
    )

    client = ChatHuggingFace(llm=llm)
    _llm_cache[model_name] = client
    return client
