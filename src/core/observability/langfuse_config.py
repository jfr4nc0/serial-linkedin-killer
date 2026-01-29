"""Langfuse configuration and callback setup for LangGraph observability."""

import os
from typing import Optional

from dotenv import load_dotenv
from loguru import logger

# Load environment variables
load_dotenv()


def configure_langfuse() -> Optional["LangfuseCallbackHandler"]:
    """
    Configure Langfuse observability if credentials are available.

    Returns:
        LangfuseCallbackHandler if configured, None otherwise
    """
    try:
        from langfuse.callback import CallbackHandler as LangfuseCallbackHandler

        # Check if Langfuse credentials are available
        secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

        if not secret_key or not public_key:
            logger.info("Langfuse credentials not found - observability disabled")
            return None

        # Initialize Langfuse callback handler
        callback_handler = LangfuseCallbackHandler(
            secret_key=secret_key,
            public_key=public_key,
            host=host,
            debug=os.getenv("LANGFUSE_DEBUG", "false").lower() == "true",
        )

        # Use a bound logger with observability trace_id
        obs_logger = logger.bind(trace_id="observability")
        obs_logger.info(f"Langfuse observability configured - host: {host}")
        return callback_handler

    except ImportError:
        # Use a bound logger with observability trace_id
        obs_logger = logger.bind(trace_id="observability")
        obs_logger.warning("Langfuse not installed - observability disabled")
        return None
    except Exception as e:
        # Use a bound logger with observability trace_id
        obs_logger = logger.bind(trace_id="observability")
        obs_logger.error(f"Failed to configure Langfuse: {e}")
        return None


def get_langfuse_callback() -> Optional["LangfuseCallbackHandler"]:
    """
    Get configured Langfuse callback handler.

    Returns:
        LangfuseCallbackHandler if available, None otherwise
    """
    return configure_langfuse()


def get_langfuse_config_for_langgraph(trace_id: str = None) -> dict:
    """
    Get Langfuse configuration for LangGraph compile() method.

    Args:
        trace_id: Optional trace ID to propagate through the workflow

    Returns:
        Configuration dict for LangGraph's compile method
    """
    callback_handler = get_langfuse_callback()

    if callback_handler:
        config = {
            "callbacks": [callback_handler],
            "tags": ["langgraph", "job-application-agent"],
        }

        # Set trace ID if provided
        if trace_id:
            callback_handler.trace_id = trace_id
            config["metadata"] = {"trace_id": trace_id}

        return config
    else:
        return {}


def create_langfuse_trace(name: str, trace_id: str = None, metadata: dict = None):
    """
    Create a new Langfuse trace with the given trace ID.

    Args:
        name: Name of the trace
        trace_id: UUID trace ID to use
        metadata: Additional metadata for the trace

    Returns:
        Langfuse trace object or None if not configured
    """
    callback_handler = get_langfuse_callback()

    if callback_handler:
        try:
            from langfuse import Langfuse

            # Initialize Langfuse client
            langfuse = Langfuse(
                secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
                public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
                host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
            )

            # Create trace with custom ID
            trace = langfuse.trace(id=trace_id, name=name, metadata=metadata or {})

            return trace

        except Exception as e:
            logger.error(f"Failed to create Langfuse trace: {e}")
            return None

    return None
