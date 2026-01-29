import os

from dotenv import load_dotenv
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint


def get_llm_client(
    model_name: str = "Qwen/Qwen3-30B-A3B-Thinking-2507",
) -> ChatHuggingFace:
    """
    Get a ChatHuggingFace client configured for Hugging Face Serverless API.

    Args:
        model_name: The model name to use (defaults to Qwen3-30B-A3B-Thinking)

    Returns:
        Configured ChatHuggingFace client pointing to HF Serverless API
    """
    load_dotenv()
    hf_token = os.getenv("HUGGING_FACE_HUB_TOKEN")
    if not hf_token:
        raise ValueError("HUGGING_FACE_HUB_TOKEN environment variable is required")

    # Create HuggingFace Endpoint for serverless inference
    llm = HuggingFaceEndpoint(
        repo_id=model_name,
        huggingfacehub_api_token=hf_token,
        temperature=0.1,
        max_new_tokens=2000,
        timeout=300,  # 5 minute timeout for complex analysis
        streaming=False,
        task="text-generation",
    )

    # Wrap with ChatHuggingFace for chat interface
    return ChatHuggingFace(llm=llm)
