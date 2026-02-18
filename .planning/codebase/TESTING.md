# Testing Patterns

**Analysis Date:** 2026-02-11

## Test Framework

**Runner:**
- pytest (v9.0.2) - configured in pyproject.toml
- No explicit pytest.ini or conftest.py found

**Assertion Library:**
- Python built-in assertions
- pytest fixtures for test setup

**Run Commands:**
```bash
pytest                           # Run all tests
pytest -v                        # Verbose mode with test names
pytest tests/                    # Run specific test directory
pytest -k "test_search"          # Run tests matching pattern
pytest tests/test_outreach.py    # Run specific test file
```

## Test File Organization

**Location:**
- Tests co-located in `/home/jfr4nc0/workspace/serial-linkedin-killer/tests/` directory (separate from source)
- Test data in `tests/data/` subdirectory

**Naming:**
- Test files: `test_*.py` prefix (e.g., `test_job_application.py`, `test_search_jobs.py`)
- Test functions: `test_*()` prefix (e.g., `test_load_companies()`, `test_filter_by_country()`)
- Fixtures: descriptive names with `@pytest.fixture` decorator

**Structure:**
```
tests/
├── data/                      # Test data files
├── test_cv_json_integration.py
├── test_job_application.py
├── test_outreach.py
├── test_search_jobs.py
└── test_message_send_graph.py
```

## Test Structure

**Suite Organization:**
Tests use pytest fixtures for setup and direct function/class testing:

```python
@pytest.fixture
def sample_csv(tmp_path):
    """Create a sample CSV file for testing."""
    csv_content = """country,founded,id,industry,..."""
    csv_file = tmp_path / "test_companies.csv"
    csv_file.write_text(csv_content)
    return str(csv_file)


def test_load_companies(sample_csv):
    df = load_companies(sample_csv)
    assert len(df) == 5
    assert list(df.columns) == [...]
```

**Patterns:**
- Setup: pytest fixtures provide test data and resources
- Execution: Call function/method directly with test inputs
- Assertion: Python assert statements with clear messages
- Teardown: Fixtures automatically cleanup (pytest handles cleanup)

**Examples from test_outreach.py:**
```python
def test_get_unique_values(sample_csv):
    df = load_companies(sample_csv)

    countries = get_unique_values(df, "country")
    assert "germany" in countries
    assert "united states" in countries
    assert len(countries) == 3
```

## Mocking

**Framework:**
- Not explicitly configured
- Manual mocking possible via fixtures
- Integration testing preferred over unit testing with mocks

**Patterns:**
- Fixtures provide test doubles instead of mocking libraries
- Real file I/O mocked via `tmp_path` fixture from pytest
- CSV data provided inline in fixtures for isolation

**Example from test_outreach.py (lines 22-34):**
```python
@pytest.fixture
def sample_csv(tmp_path):
    """Create a sample CSV file for testing."""
    csv_content = """country,founded,id,..."""
    csv_file = tmp_path / "test_companies.csv"
    csv_file.write_text(csv_content)
    return str(csv_file)
```

**What to Mock:**
- External services (if needed)
- File operations (use tmp_path fixture instead)
- Time-dependent logic (provide controlled inputs)

**What NOT to Mock:**
- Core business logic (test with real implementations)
- Data transformations (test with sample data fixtures)
- Schema validation (test Pydantic models directly)

## Fixtures and Factories

**Test Data:**
Inline fixture creation with sample data:

```python
@pytest.fixture
def sample_csv(tmp_path):
    """Create a sample CSV file for testing."""
    csv_content = """country,founded,id,industry,linkedin_url,locality,name,region,size,website
united states,2010,abc123,software,linkedin.com/company/acme,san francisco,acme corp,california,51-200,acme.com
germany,2015,def456,automotive,linkedin.com/company/autohaus,munich,autohaus gmbh,bavaria,201-500,autohaus.de
united states,2020,ghi789,software,linkedin.com/company/startupx,new york,startup x,new york,1-10,startupx.io
romania,2012,jkl012,investment banking,linkedin.com/company/romfin,bucharest,romfin,bucharest,11-50,romfin.ro
germany,2008,mno345,software,linkedin.com/company/devhaus,berlin,devhaus ag,berlin,51-200,devhaus.de
"""
    csv_file = tmp_path / "test_companies.csv"
    csv_file.write_text(csv_content)
    return str(csv_file)
```

**Location:**
- Within test files using fixtures
- No centralized factory pattern observed
- Test data embedded in test functions or fixture content

## Coverage

**Requirements:** Not enforced
- No `.coveragerc` or coverage configuration found
- No coverage badges or minimum threshold set

**View Coverage:**
```bash
pytest --cov=src --cov-report=html
# Generates HTML report in htmlcov/
```

## Test Types

**Unit Tests:**
- Test individual functions and classes in isolation
- Examples: `test_load_companies()`, `test_filter_by_country()`, `test_get_unique_values()`
- Location: `tests/test_outreach.py` (lines 37-80)
- Scope: Single function behavior with sample data

**Integration Tests:**
- End-to-end workflow testing
- Examples: `test_cv_loader()`, `test_agent_integration()`, `test_mcp_client_signature()`
- Location: `tests/test_cv_json_integration.py`
- Scope: Multiple components working together, real file I/O
- Pattern: Import actual modules and run workflows

**E2E Tests:**
- Workflow testing with multiple agents/services
- Examples: `test_cv_json_integration.py` contains agent workflow tests
- Framework: None specified (custom integration tests)
- Approach: Load config, create agents, run workflows, check results
- Uses real LinkedIn MCP connections in some tests

## Common Patterns

**Async Testing:**
Not prominently used - most code is synchronous
- Async components exist but tests use synchronous patterns
- Example: `LinkedInMCPClientSync` used instead of async client in tests
- Pattern: Direct function calls without async/await in test context

**Error Testing:**
Tests verify error conditions and success states:
```python
def test_cv_loader():
    """Test CV JSON loading and analysis extraction."""
    try:
        from src.core.tools.cv_loader import extract_cv_analysis, load_cv_data

        # Load CV data
        cv_data = load_cv_data("./data/cv_data.json")
        print(f"✅ CV data loaded: {cv_data['name']}")

    except Exception as e:
        print(f"❌ CV loader test failed: {e}")
        import traceback
        traceback.print_exc()
        return None, None
```

**Path Setup in Tests:**
Tests add project root to sys.path:
```python
import sys
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Or using Path:
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
```

**Environment Setup:**
Tests load environment variables for integration:
```python
from dotenv import load_dotenv

load_dotenv()

user_credentials = {
    "email": os.getenv("LINKEDIN_EMAIL", "test@example.com"),
    "password": os.getenv("LINKEDIN_PASSWORD", "test_password"),
}
```

## Test Examples from Codebase

**test_outreach.py structure:**
```python
"""Tests for the employee outreach components."""

import os
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from src.config.config_loader import AgentConfig, load_config
from src.core.tools.company_db import CompanyDB
from src.core.tools.company_loader import (
    filter_companies,
    get_unique_values,
    load_companies,
)
from src.core.tools.message_template import render_template


@pytest.fixture
def sample_csv(tmp_path):
    # fixture implementation


def test_load_companies(sample_csv):
    df = load_companies(sample_csv)
    assert len(df) == 5


def test_filter_by_country(sample_csv):
    df = load_companies(sample_csv)
    filtered = filter_companies(df, {"country": ["germany"]})
    assert len(filtered) == 2
    assert all(filtered["country"] == "germany")
```

**test_cv_json_integration.py structure:**
```python
#!/usr/bin/env python3
"""Test CV JSON integration end-to-end."""

import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_cv_loader():
    """Test CV JSON loading and analysis extraction."""
    try:
        from src.core.tools.cv_loader import extract_cv_analysis, load_cv_data
        cv_data = load_cv_data("./data/cv_data.json")
        # assertions and checks
    except Exception as e:
        print(f"❌ CV loader test failed: {e}")
        return None, None
```

## Test Execution Notes

- Tests can be run directly as scripts: `python tests/test_job_application.py`
- Many tests load environment variables from `.env` file
- Integration tests may require running services (Kafka, databases)
- Some tests verify method signatures and parameter presence:
  ```python
  import inspect
  run_sig = inspect.signature(agent.run)
  params = list(run_sig.parameters.keys())

  if "cv_data_path" in params:
      print("✅ Agent run method accepts cv_data_path parameter")
  ```

---

*Testing analysis: 2026-02-11*
