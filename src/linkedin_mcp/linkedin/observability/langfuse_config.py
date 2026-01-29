"""Langfuse configuration for LinkedIn MCP observability."""

import os
from typing import Optional

from dotenv import load_dotenv
from loguru import logger

# Load environment variables
load_dotenv()


def configure_langfuse_for_mcp() -> Optional["LangfuseCallbackHandler"]:
    """
    Configure Langfuse observability for LinkedIn MCP components.

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
            logger.debug(
                "Langfuse credentials not found for MCP - observability disabled"
            )
            return None

        # Initialize Langfuse callback handler with MCP-specific configuration
        callback_handler = LangfuseCallbackHandler(
            secret_key=secret_key,
            public_key=public_key,
            host=host,
            debug=os.getenv("LANGFUSE_DEBUG", "false").lower() == "true",
            session_id=f"linkedin-mcp-{os.getpid()}",  # Unique session per MCP server process
        )

        # Use MCP logger with trace_id
        from src.linkedin_mcp.linkedin.utils.logging_config import get_mcp_logger

        mcp_logger = get_mcp_logger()
        mcp_logger.info(
            f"LinkedIn MCP Langfuse observability configured - host: {host}"
        )
        return callback_handler

    except ImportError:
        logger.debug("Langfuse not installed for MCP - observability disabled")
        return None
    except Exception as e:
        logger.error(f"Failed to configure Langfuse for MCP: {e}")
        return None


def get_langfuse_callback_for_mcp() -> Optional["LangfuseCallbackHandler"]:
    """
    Get configured Langfuse callback handler for MCP components.

    Returns:
        LangfuseCallbackHandler if available, None otherwise
    """
    return configure_langfuse_for_mcp()


def get_langfuse_config_for_mcp_langgraph(trace_id: str = None) -> dict:
    """
    Get Langfuse configuration for LinkedIn MCP LangGraph workflows.

    Args:
        trace_id: Optional trace ID to propagate through the workflow

    Returns:
        Configuration dict for LangGraph's compile method
    """
    callback_handler = get_langfuse_callback_for_mcp()

    if callback_handler:
        config = {
            "callbacks": [callback_handler],
            "tags": ["linkedin-mcp", "langgraph", "job-automation"],
        }

        # Set trace ID if provided
        if trace_id:
            callback_handler.trace_id = trace_id
            config["metadata"] = {"trace_id": trace_id}

        return config
    else:
        return {}


def trace_mcp_operation(operation_name: str):
    """
    Decorator to trace MCP operations with Langfuse using trace_id propagation.

    Args:
        operation_name: Name of the operation being traced
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            # Try to extract trace_id from args/kwargs
            trace_id = None

            # Look for trace_id in args (for self methods)
            if args and hasattr(args[0], "__dict__"):
                for arg in args:
                    if isinstance(arg, dict) and "trace_id" in arg:
                        trace_id = arg["trace_id"]
                        break
                    elif hasattr(arg, "get") and arg.get("trace_id"):
                        trace_id = arg.get("trace_id")
                        break

            # Look for trace_id in kwargs
            if not trace_id and "trace_id" in kwargs:
                trace_id = kwargs["trace_id"]

            callback_handler = get_langfuse_callback_for_mcp()
            if callback_handler:
                try:
                    from langfuse import Langfuse

                    # Initialize Langfuse client
                    langfuse = Langfuse(
                        secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
                        public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
                        host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
                    )

                    # Create span within existing trace if trace_id exists
                    if trace_id:
                        span = langfuse.span(
                            trace_id=trace_id,
                            name=operation_name,
                            metadata={
                                "operation": operation_name,
                                "component": "linkedin-mcp",
                                "args_count": len(args),
                                "kwargs_count": len(kwargs),
                            },
                        )
                    else:
                        # Create new trace if no trace_id
                        span = langfuse.trace(
                            name=operation_name,
                            metadata={
                                "operation": operation_name,
                                "component": "linkedin-mcp",
                                "args_count": len(args),
                                "kwargs_count": len(kwargs),
                            },
                        )

                    try:
                        result = func(*args, **kwargs)
                        span.update(
                            output=str(result)[:1000] if result else "Success",
                            metadata={
                                "operation": operation_name,
                                "success": True,
                                "trace_id": trace_id,
                            },
                        )
                        return result
                    except Exception as e:
                        span.update(
                            output=f"Error: {str(e)}",
                            metadata={
                                "operation": operation_name,
                                "error": True,
                                "error_type": type(e).__name__,
                                "trace_id": trace_id,
                            },
                        )
                        raise

                except ImportError:
                    # Fallback to callback handler
                    return func(*args, **kwargs)
            else:
                return func(*args, **kwargs)

        return wrapper

    return decorator


def create_mcp_trace(name: str, trace_id: str, metadata: dict = None):
    """
    Create a Langfuse trace for MCP operations with custom trace ID.

    Args:
        name: Name of the trace
        trace_id: UUID trace ID to use
        metadata: Additional metadata for the trace

    Returns:
        Langfuse trace object or None if not configured
    """
    try:
        from langfuse import Langfuse

        # Check if credentials are available
        secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        public_key = os.getenv("LANGFUSE_PUBLIC_KEY")

        if not secret_key or not public_key:
            return None

        # Initialize Langfuse client
        langfuse = Langfuse(
            secret_key=secret_key,
            public_key=public_key,
            host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        )

        # Create trace with custom ID
        trace = langfuse.trace(
            id=trace_id,
            name=name,
            metadata={"component": "linkedin-mcp", **(metadata or {})},
        )

        return trace

    except Exception as e:
        logger.error(f"Failed to create MCP Langfuse trace: {e}")
        return None
