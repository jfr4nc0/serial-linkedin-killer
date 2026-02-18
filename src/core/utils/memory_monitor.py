"""Memory monitoring utility for the outreach pipeline.

Provides functions to check RSS usage, detect high memory conditions,
and log memory stats at pipeline checkpoints.
"""

import os

import psutil
from loguru import logger


def get_memory_usage() -> dict:
    """Return current process memory usage.

    Returns:
        dict with keys:
          - rss_mb (float): Resident Set Size in megabytes (1 decimal)
          - percent (float): System-wide virtual memory usage percentage
    """
    process = psutil.Process(os.getpid())
    rss_bytes = process.memory_info().rss
    rss_mb = round(rss_bytes / (1024 * 1024), 1)
    percent = psutil.virtual_memory().percent
    return {"rss_mb": rss_mb, "percent": percent}


def check_memory_threshold(threshold_percent: float = None) -> bool:
    """Check whether system memory usage exceeds the configured threshold.

    Args:
        threshold_percent: Override threshold (0-100). When *None*, the value
            is loaded from ``config.memory.threshold_percent``.

    Returns:
        True if memory percent >= threshold, False otherwise.
    """
    if threshold_percent is None:
        from src.config.config_loader import load_config

        threshold_percent = load_config().memory.threshold_percent

    usage = get_memory_usage()
    if usage["percent"] >= threshold_percent:
        logger.warning(
            "[MEMORY] Circuit breaker triggered: {percent}% used "
            "(threshold: {threshold}%), RSS: {rss_mb}MB",
            percent=usage["percent"],
            threshold=threshold_percent,
            rss_mb=usage["rss_mb"],
        )
        return True
    return False


def log_memory_checkpoint(checkpoint_name: str) -> None:
    """Log current memory usage at a named pipeline checkpoint.

    Args:
        checkpoint_name: Human-readable label (e.g. "pre-search").
    """
    usage = get_memory_usage()
    logger.info(
        "[MEMORY] {checkpoint_name}: RSS={rss_mb}MB, used={percent}%",
        checkpoint_name=checkpoint_name,
        rss_mb=usage["rss_mb"],
        percent=usage["percent"],
    )
