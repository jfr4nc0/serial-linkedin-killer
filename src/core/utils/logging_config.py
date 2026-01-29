"""Logging configuration for the core agent with structured output and file logging."""

import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from loguru import logger

# Load environment variables
load_dotenv()


def configure_core_agent_logging(
    log_level: Optional[str] = None,
    log_file: Optional[str] = None,
    default_trace_id: Optional[str] = None,
) -> None:
    """
    Configure logging for the core agent with structured output.
    Always includes trace_id in logs.

    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional)
        default_trace_id: Default trace_id for agent logs (defaults to UUID)
    """
    import uuid

    # Remove default logger to reconfigure
    logger.remove()

    # Get configuration from environment or parameters
    log_level = log_level or os.getenv("CORE_AGENT_LOG_LEVEL", "INFO")
    log_file = log_file or os.getenv("CORE_AGENT_LOG_FILE")
    default_trace_id = default_trace_id or str(uuid.uuid4())

    # Console logging with rich colors - always includes trace_id
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>core-agent</cyan> | "
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

        def format_func(record):
            """Custom format function to handle missing trace_id."""
            trace_id = record.get("extra", {}).get("trace_id", "no-trace")
            base_format = (
                "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
                "{level: <8} | "
                "core-agent | "
                "{name}:{function}:{line} | "
                f"trace_id={trace_id} | "
                "{message}"
            )
            return base_format

        logger.add(
            log_file,
            format=format_func,
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
            f"Core agent logging configured - file: {log_file}, level: {log_level}"
        )
    else:
        # Get logger with default trace_id for startup messages
        startup_logger = logger.bind(trace_id=default_trace_id)
        startup_logger.info(
            f"Core agent logging configured - console only, level: {log_level}"
        )


def get_core_agent_logger(trace_id: Optional[str] = None) -> "logger":
    """
    Get a logger instance bound with trace_id for the core agent.
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


def log_core_agent_startup(trace_id: str, config: dict) -> None:
    """
    Log core agent startup information.

    Args:
        trace_id: UUID trace ID for this session
        config: Configuration dictionary
    """
    startup_logger = get_core_agent_logger(trace_id)

    startup_logger.info(
        "Core agent starting up",
        cv_file_path=config.get("cv_file_path"),
        job_searches_count=len(config.get("job_searches", [])),
        output_format=config.get("output_format"),
        mcp_host=config.get("mcp_host"),
        mcp_port=config.get("mcp_port"),
    )


def log_core_agent_completion(trace_id: str, results: dict) -> None:
    """
    Log core agent completion with results summary.

    Args:
        trace_id: UUID trace ID for this session
        results: Results dictionary
    """
    completion_logger = get_core_agent_logger(trace_id)

    completion_logger.info(
        "Core agent workflow completed",
        total_jobs_found=results.get("total_jobs_found", 0),
        total_jobs_applied=results.get("total_jobs_applied", 0),
        success_rate=results.get("success_rate", 0.0),
        errors_count=len(results.get("errors", [])),
    )
