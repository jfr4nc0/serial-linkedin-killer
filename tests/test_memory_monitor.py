"""Unit tests for memory monitor utility."""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

import src.config.config_loader as config_loader
from src.core.utils.memory_monitor import (
    check_memory_threshold,
    get_memory_usage,
    log_memory_checkpoint,
)


@pytest.fixture(autouse=True)
def clear_config_cache():
    """Clear cached config before each test so env overrides take effect."""
    config_loader._cached_config = None
    yield
    config_loader._cached_config = None


def test_get_memory_usage_returns_expected_keys():
    """get_memory_usage returns dict with rss_mb and percent as positive floats."""
    result = get_memory_usage()
    assert "rss_mb" in result
    assert "percent" in result
    assert isinstance(result["rss_mb"], float)
    assert isinstance(result["percent"], float)
    assert result["rss_mb"] > 0
    assert 0 <= result["percent"] <= 100


def test_check_memory_threshold_under():
    """Returns False when memory is under threshold."""
    mock_vm = MagicMock()
    mock_vm.percent = 50.0

    with patch("src.core.utils.memory_monitor.psutil") as mock_psutil:
        mock_psutil.virtual_memory.return_value = mock_vm
        mock_psutil.Process.return_value.memory_info.return_value.rss = 100 * 1024 * 1024
        result = check_memory_threshold(threshold_percent=80.0)

    assert result is False


def test_check_memory_threshold_over():
    """Returns True when memory exceeds threshold."""
    mock_vm = MagicMock()
    mock_vm.percent = 85.0

    with patch("src.core.utils.memory_monitor.psutil") as mock_psutil:
        mock_psutil.virtual_memory.return_value = mock_vm
        mock_psutil.Process.return_value.memory_info.return_value.rss = 200 * 1024 * 1024
        result = check_memory_threshold(threshold_percent=80.0)

    assert result is True


def test_check_memory_threshold_uses_config_default():
    """When no threshold arg, loads default from config (80.0)."""
    mock_vm = MagicMock()
    mock_vm.percent = 50.0

    mock_config = MagicMock()
    mock_config.memory.threshold_percent = 80.0

    with patch("src.core.utils.memory_monitor.psutil") as mock_psutil, \
         patch("src.config.config_loader.load_config", return_value=mock_config):
        mock_psutil.virtual_memory.return_value = mock_vm
        mock_psutil.Process.return_value.memory_info.return_value.rss = 100 * 1024 * 1024
        result = check_memory_threshold()

    assert result is False


def test_log_memory_checkpoint_logs_info(capfd):
    """log_memory_checkpoint emits an INFO log containing [MEMORY] and checkpoint name."""
    mock_vm = MagicMock()
    mock_vm.percent = 42.0

    with patch("src.core.utils.memory_monitor.psutil") as mock_psutil:
        mock_psutil.virtual_memory.return_value = mock_vm
        mock_psutil.Process.return_value.memory_info.return_value.rss = 150 * 1024 * 1024

        # Use loguru's sink capture
        from loguru import logger
        import sys

        messages = []
        handler_id = logger.add(lambda m: messages.append(str(m)), level="INFO")
        try:
            log_memory_checkpoint("test-checkpoint")
        finally:
            logger.remove(handler_id)

    log_output = "".join(messages)
    assert "[MEMORY]" in log_output
    assert "test-checkpoint" in log_output


def test_memory_config_in_agent_config():
    """load_config with a YAML containing memory section returns correct threshold."""
    yaml_content = """\
memory:
  threshold_percent: 75.0
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        tmp_path = f.name

    try:
        config = config_loader.load_config(config_path=tmp_path)
        assert config.memory.threshold_percent == 75.0
    finally:
        os.unlink(tmp_path)


def test_memory_config_env_override(monkeypatch):
    """MEMORY_THRESHOLD_PERCENT env var overrides the YAML value."""
    monkeypatch.setenv("MEMORY_THRESHOLD_PERCENT", "90")
    config = config_loader.load_config()
    assert config.memory.threshold_percent == 90.0
