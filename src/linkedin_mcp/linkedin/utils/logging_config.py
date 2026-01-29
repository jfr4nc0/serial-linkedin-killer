"""Logging configuration for LinkedIn MCP server with structured output and file logging."""

import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from loguru import logger

# Load environment variables
load_dotenv()


def configure_mcp_logging(
    log_level: Optional[str] = None,
    log_file: Optional[str] = None,
    server_id: Optional[str] = None,
    default_trace_id: Optional[str] = None,
) -> None:
    """
    Configure logging for the LinkedIn MCP server with structured output.
    Always includes trace_id in logs.

    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional)
        server_id: Unique server identifier (defaults to PID)
        default_trace_id: Default trace_id for server logs (defaults to UUID)
    """
    import uuid

    # Remove default logger to reconfigure
    logger.remove()

    # Get configuration from environment or parameters
    log_level = log_level or os.getenv("LINKEDIN_MCP_LOG_LEVEL", "INFO")
    log_file = log_file or os.getenv("LINKEDIN_MCP_LOG_FILE")
    server_id = server_id or f"mcp-{os.getpid()}"
    default_trace_id = default_trace_id or str(uuid.uuid4())

    # Console logging with rich colors for MCP - always includes trace_id
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<magenta>linkedin-mcp</magenta> | "
        f"<yellow>{server_id}</yellow> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "trace_id={extra[trace_id]} - <level>{message}</level>"
    )

    # Add console handler
    logger.add(
        sys.stderr,
        format=console_format,
        level=log_level,
        colorize=True,
        backtrace=True,
        diagnose=True,
        enqueue=True,
    )

    # Add file handler if specified
    if log_file:
        # Ensure log directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_format = (
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
            "{level: <8} | "
            "linkedin-mcp | "
            f"{server_id} | "
            "{name}:{function}:{line} | "
            "trace_id={extra[trace_id]} | "
            "{message}"
        )

        logger.add(
            log_file,
            format=file_format,
            level=log_level,
            rotation="10 MB",
            retention="7 days",
            compression="gz",
            backtrace=True,
            diagnose=True,
            enqueue=True,
            serialize=False,  # Use human-readable format
        )

        # Get logger with default trace_id for startup messages
        startup_logger = logger.bind(trace_id=default_trace_id)
        startup_logger.info(
            f"LinkedIn MCP logging configured - file: {log_file}, level: {log_level}"
        )
    else:
        # Get logger with default trace_id for startup messages
        startup_logger = logger.bind(trace_id=default_trace_id)
        startup_logger.info(
            f"LinkedIn MCP logging configured - console only, level: {log_level}"
        )


def get_mcp_logger(trace_id: Optional[str] = None) -> "logger":
    """
    Get a logger instance bound with trace_id for LinkedIn MCP.
    Always ensures a trace_id is present.

    Args:
        trace_id: UUID trace ID for correlation (generates new UUID if None)

    Returns:
        Logger instance with bound trace_id
    """
    import uuid

    if trace_id is None:
        trace_id = str(uuid.uuid4())

    return logger.bind(trace_id=trace_id)


def log_mcp_server_startup(server_info: dict) -> None:
    """
    Log LinkedIn MCP server startup information.

    Args:
        server_info: Server configuration and info
    """
    startup_logger = get_mcp_logger("startup")

    startup_logger.info(
        "LinkedIn MCP server starting",
        server_name=server_info.get("name", "LinkedIn Job Applier"),
        version=server_info.get("version", "unknown"),
        transport=server_info.get("transport", "stdio"),
        host=server_info.get("host"),
        port=server_info.get("port"),
        fastmcp_version=server_info.get("fastmcp_version"),
        mcp_sdk_version=server_info.get("mcp_sdk_version"),
    )


def log_mcp_tool_registration(tools: list) -> None:
    """
    Log MCP tool registration.

    Args:
        tools: List of registered tools
    """
    registration_logger = get_mcp_logger("registration")

    registration_logger.info(
        "MCP tools registered",
        tools_count=len(tools),
        tool_names=[tool.get("name", "unknown") for tool in tools],
    )


def log_mcp_operation_completion(
    trace_id: str, operation: str, results: dict, duration_ms: Optional[float] = None
) -> None:
    """
    Log MCP operation completion with results.

    Args:
        trace_id: UUID trace ID for this operation
        operation: Operation name (search_jobs, easy_apply_for_jobs)
        results: Operation results
        duration_ms: Operation duration in milliseconds
    """
    completion_logger = get_mcp_logger(trace_id)

    log_data = {
        "operation": operation,
        "success": results.get("success", False),
    }

    if duration_ms:
        log_data["duration_ms"] = duration_ms

    # Add operation-specific metrics
    if operation == "search_jobs":
        log_data.update(
            {
                "jobs_found": len(results.get("jobs", [])),
                "query": results.get("query", "unknown"),
            }
        )
    elif operation == "easy_apply_for_jobs":
        log_data.update(
            {
                "applications_count": len(results.get("applications", [])),
                "successful_applications": len(
                    [
                        r
                        for r in results.get("applications", [])
                        if r.get("success", False)
                    ]
                ),
                "failed_applications": len(
                    [
                        r
                        for r in results.get("applications", [])
                        if not r.get("success", False)
                    ]
                ),
            }
        )

    if results.get("error"):
        log_data["error"] = results["error"]
        completion_logger.error("MCP operation completed with error", **log_data)
    else:
        completion_logger.info("MCP operation completed successfully", **log_data)
