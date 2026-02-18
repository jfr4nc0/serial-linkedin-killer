# Coding Conventions

**Analysis Date:** 2026-02-11

## Naming Patterns

**Files:**
- Modules use snake_case: `job_service.py`, `cv_analysis_tools.py`, `agent_db.py`
- API controllers: `job_controller.py`, `outreach_controller.py`
- Models/data classes: `job_application_agent_state.py`, `cv_analysis.py`
- Tools files: `cv_loader.py`, `company_db.py`
- Test files use prefix: `test_*.py` (e.g., `test_job_application.py`, `test_outreach.py`)

**Functions:**
- Lowercase with underscores: `search_jobs_node()`, `filter_jobs_node()`, `apply_to_jobs_node()`
- Private functions prefixed with underscore: `_get_executor()`, `_shutdown_executor()`, `_delivery_report()`
- Tool functions use `@tool` decorator from langchain_core: `read_pdf_cv()`, `analyze_cv_structure()`
- Helper functions prefixed with underscore: `_extract_basic_skills()`, `_infer_domain_from_position()`

**Variables:**
- Local variables: snake_case
- Constants: UPPERCASE_WITH_UNDERSCORES (e.g., `TOPIC_JOB_RESULTS`, `TOPIC_OUTREACH_RESULTS`)
- Module-level private variables: prefixed with underscore (e.g., `_producer`, `_agent_db`, `_executor`)
- Type hints extensively used throughout codebase

**Types:**
- Pydantic models for schemas: `JobApplyRequest`, `JobApplyResponse`, `CredentialsModel`
- TypedDict for state management: `JobApplicationAgentState`, `OutreachState`
- Union types for optional values: `Union[Engine, str]`, `str | None` (Python 3.10+ style)
- Import from typing: `Dict`, `List`, `Any`, `Optional`, `Union`

## Code Style

**Formatting:**
- Tool: Black (version 25.9.0) - enabled in pre-commit hooks
- Language version: Python 3.12+
- Line length: Black default (88 characters)
- Triple-quoted docstrings for all public functions and classes

**Linting:**
- Tool: Configured via `.pre-commit-config.yaml`
- Pre-commit hooks: black, isort, trailing-whitespace, end-of-file-fixer, check-yaml
- Type checking: basedpyright (v1.37.2) with config in `pyrightconfig.json`
- Pre-commit enabled for: black (Python 3.12), isort (--profile black)

## Import Organization

**Order:**
1. Standard library imports (e.g., `import json`, `import uuid`, `from typing import Any`)
2. Third-party imports (e.g., `from pydantic import BaseModel`, `from fastapi import FastAPI`, `from loguru import logger`)
3. Local imports (e.g., `from src.config.config_loader import load_config`, `from src.core.api.services.job_service import JobService`)

**Path Aliases:**
- Project uses absolute imports from package root: `from src.core.api.app import ...`
- No relative imports (`from . import` or `from .. import`)
- All imports specify module/function explicitly

**Example from `src/core/api/app.py`:**
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from loguru import logger

from src.config.config_loader import load_config
from src.core.api.controllers.job_controller import router as job_router
```

## Error Handling

**Patterns:**
- Broad try-except for service operations with logging via loguru
- Exception messages logged with context: `logger.exception("Job application workflow failed", task_id=task_id)`
- Errors stored in state for workflow tracking: `state["errors"] = state.get("errors", []) + [error_msg]`
- Custom exception chaining: wraps errors in user-friendly messages
- File operations check existence before processing: `if not os.path.exists(file_path): raise FileNotFoundError(...)`
- Database operations use context managers: `with self._session_factory() as session:`

**Error handling in job_service.py (lines 90-104):**
```python
except Exception as e:
    logger.exception("Job application workflow failed", task_id=task_id)
    response = JobApplyResponse(
        task_id=task_id,
        status=f"failed: {e}",
        errors=[str(e)],
        ...
    )
finally:
    del agent
    gc.collect()
```

## Logging

**Framework:** loguru
- Imported as: `from loguru import logger`
- Used in all modules for structured logging
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

**Patterns:**
- Always include context in log calls: `logger.info("Searching jobs", job_title=..., location=...)`
- Trace ID included via context: `logger.info("Starting job search", searches_count=len(...))`
- Exception logging: `logger.exception("message", **context)`
- Timing logs for performance: `logger.info("[TIMING] Pydantic serialization", elapsed_ms=..., payload_bytes=...)`
- Structured logging with keyword arguments for JSON compatibility

**Configuration location:** `src/core/utils/logging_config.py`
- Console logging with color formatting
- Optional file logging with rotation (10 MB), retention (7 days), and compression
- Trace ID auto-injected into all logs via `configure_trace_logging()`

## Comments

**When to Comment:**
- Module docstrings: Always include at top of file (e.g., `"""Kafka producer for publishing agent workflow results."""`)
- Class docstrings: Always for public classes (e.g., `"""Orchestrates the job application agent and publishes results to Kafka."""`)
- Complex logic: Brief inline comments for non-obvious implementations
- Public methods: Always include docstrings with Args/Returns
- Helper functions: Include when behavior isn't self-documenting

**JSDoc/TSDoc:**
- Use triple-quoted docstrings for all public functions:
```python
def submit(self, request: JobApplyRequest) -> str:
    """Submit a job application workflow. Returns task_id immediately."""
```

**Example with full documentation from cv_analysis_tools.py:**
```python
@tool
def read_pdf_cv(file_path: str) -> str:
    """
    Extract text content from PDF CV file.

    Args:
        file_path: Path to the PDF CV file

    Returns:
        Extracted text content from the PDF
    """
```

## Function Design

**Size:**
- Most functions 15-50 lines
- Complex logic broken into private helper functions
- Single responsibility principle observed (e.g., `_extract_basic_skills()`, `_infer_domain_from_position()`)

**Parameters:**
- Type hints on all parameters: `def search_jobs_node(self, state: JobApplicationAgentState) -> Dict[str, Any]:`
- Optional parameters use Python 3.10+ syntax: `server_host: str = None`, `server_port: int = None`
- Keyword-only arguments common in service methods

**Return Values:**
- All functions have return type hints
- Services return Pydantic models: `JobApplyResponse`, `TaskResponse`
- Node functions return dicts: `Dict[str, Any]`
- Database operations return typed values: `bool`, `Dict[str, Any]`, `set`
- Fallback returns (empty lists, None) well-defined

## Module Design

**Exports:**
- Explicit imports in `__init__.py` files (some modules use them: `src/core/api/__init__.py`)
- Public classes and functions exported from modules
- No wildcard imports (`from module import *`)

**Barrel Files:**
- Limited use of barrel files - mostly direct imports
- Controllers and services imported explicitly in main app
- Example: `from src.core.api.controllers.job_controller import router as job_router`

**Layering:**
- Controllers: Handle HTTP requests/responses
- Services: Business logic and orchestration
- Schemas: Pydantic request/response models
- Models: Data structures and state
- Tools: Utility functions with @tool decorator
- Agents: LangGraph workflow orchestration
- DB: Data persistence layer
- Queue: Message publishing (Kafka)

---

*Convention analysis: 2026-02-11*
