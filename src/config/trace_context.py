"""Centralized trace context for distributed tracing across all services.

This module provides a thread-safe, context-aware trace_id that automatically
propagates through sync/async code and across service boundaries.

Usage:
    # At request entry point (once per request):
    from src.config.trace_context import set_trace_id, trace_logger

    set_trace_id("abc-123")  # or set_trace_id() to generate new UUID

    # All subsequent logs automatically include trace_id:
    trace_logger.info("This log has trace_id automatically")

    # Or use get_trace_id() to pass to other services:
    from src.config.trace_context import get_trace_id
    response = call_other_service(trace_id=get_trace_id())
"""

import contextvars
import uuid
from contextlib import contextmanager
from typing import Generator, Optional

from loguru import logger

# Thread-safe context variable for trace_id
# Works correctly with threading, asyncio, and ThreadPoolExecutor
_trace_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "trace_id", default=""
)


def set_trace_id(trace_id: Optional[str] = None) -> str:
    """Set trace_id for current execution context.

    Args:
        trace_id: UUID trace ID. If None, generates a new UUID.

    Returns:
        The trace_id that was set.
    """
    tid = trace_id or str(uuid.uuid4())
    _trace_id_var.set(tid)
    return tid


def get_trace_id() -> str:
    """Get trace_id from current execution context.

    Returns:
        Current trace_id, or "no-trace" if not set.
    """
    return _trace_id_var.get() or "no-trace"


def clear_trace_id() -> None:
    """Clear the trace_id from current context."""
    _trace_id_var.set("")


@contextmanager
def trace_context(trace_id: Optional[str] = None) -> Generator[str, None, None]:
    """Context manager for scoped trace_id.

    Automatically sets trace_id on entry and restores previous value on exit.

    Args:
        trace_id: UUID trace ID. If None, generates a new UUID.

    Yields:
        The trace_id for this context.

    Example:
        with trace_context("request-123") as tid:
            logger.info("Inside traced context")
            # All logs here have trace_id="request-123"
        # trace_id restored to previous value
    """
    previous = _trace_id_var.get()
    tid = set_trace_id(trace_id)
    try:
        yield tid
    finally:
        _trace_id_var.set(previous)


def _inject_trace_id(record: dict) -> None:
    """Loguru patcher that injects trace_id from context into every log record."""
    record["extra"]["trace_id"] = get_trace_id()


def configure_trace_logging() -> None:
    """Configure loguru to automatically include trace_id in all logs.

    Call this once at application startup, before any logging.
    """
    logger.configure(patcher=_inject_trace_id)


# Pre-configured logger that always has trace_id
# Use this instead of importing logger directly from loguru
trace_logger = logger


# HTTP header name for propagating trace_id between services
TRACE_ID_HEADER = "X-Trace-ID"


def extract_trace_id_from_headers(headers: dict) -> Optional[str]:
    """Extract trace_id from HTTP headers (case-insensitive).

    Args:
        headers: HTTP headers dict.

    Returns:
        trace_id if found, None otherwise.
    """
    # Handle case-insensitive header lookup
    for key, value in headers.items():
        if key.lower() == TRACE_ID_HEADER.lower():
            return value
    return None


def inject_trace_id_to_headers(headers: Optional[dict] = None) -> dict:
    """Add current trace_id to headers dict for outgoing requests.

    Args:
        headers: Existing headers dict (optional).

    Returns:
        Headers dict with X-Trace-ID added.
    """
    headers = headers or {}
    headers[TRACE_ID_HEADER] = get_trace_id()
    return headers
