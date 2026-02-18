"""Tests for the employee outreach components."""

import os
import tempfile
from pathlib import Path

import pytest

from src.config.config_loader import AgentConfig, load_config
from src.core.agents.tools.company_db import CompanyDB
from src.core.agents.tools.message_template import render_template
from src.core.db.agent_db import AgentDB


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


# --- Message Template Tests ---


def test_render_template_basic():
    template = "Hi {employee_name}, I work at {company_name}."
    result = render_template(
        template,
        {
            "employee_name": "Alice",
            "company_name": "Acme",
        },
    )
    assert result == "Hi Alice, I work at Acme."


def test_render_template_missing_variable():
    template = "Hi {employee_name}, topic: {topic}"
    result = render_template(template, {"employee_name": "Bob"})
    assert result == "Hi Bob, topic: "


def test_render_template_static_and_dynamic():
    template = "Hi {employee_name}, I'm {my_name}, a {my_role} at {company_name}."
    result = render_template(
        template,
        {
            "employee_name": "Carol",
            "company_name": "TechCo",
            "my_name": "Dan",
            "my_role": "Engineer",
        },
    )
    assert result == "Hi Carol, I'm Dan, a Engineer at TechCo."


# --- Config Loader Tests ---


def test_load_default_config():
    config = load_config()
    assert isinstance(config, AgentConfig)
    assert config.llm.temperature == 0.1
    assert config.outreach.daily_message_limit == 50
    assert config.browser.browser_type == "chrome"


def test_load_config_from_yaml(tmp_path):
    yaml_content = """
llm:
  base_url: "http://localhost:9999/v1"
  temperature: 0.5
outreach:
  daily_message_limit: 25
  employees_per_company: 5
"""
    config_file = tmp_path / "test_config.yaml"
    config_file.write_text(yaml_content)

    config = load_config(str(config_file))
    assert config.llm.base_url == "http://localhost:9999/v1"
    assert config.llm.temperature == 0.5
    assert config.outreach.daily_message_limit == 25
    assert config.outreach.employees_per_company == 5
    # Defaults still apply
    assert config.browser.browser_type == "chrome"


def test_config_env_override(tmp_path, monkeypatch):
    yaml_content = """
linkedin:
  email: "from_yaml@test.com"
"""
    config_file = tmp_path / "test_config.yaml"
    config_file.write_text(yaml_content)

    monkeypatch.setenv("LINKEDIN_EMAIL", "from_env@test.com")

    config = load_config(str(config_file))
    assert config.linkedin.email == "from_env@test.com"


# --- CompanyDB Tests ---


@pytest.fixture
def company_db(sample_csv):
    """Create a CompanyDB with in-memory SQLite imported from sample CSV."""
    db = CompanyDB("sqlite:///:memory:")
    db.import_csv(sample_csv)
    yield db
    db.close()


def test_db_import_count(company_db):
    assert company_db.get_total_count() == 5


def test_db_unique_values(company_db):
    countries = company_db.get_unique_values("country")
    assert "germany" in countries
    assert "united states" in countries
    assert "romania" in countries
    assert len(countries) == 3

    industries = company_db.get_unique_values("industry")
    assert "software" in industries
    assert len(industries) == 3


def test_db_filter_by_country(company_db):
    results = company_db.filter_companies({"country": ["germany"]})
    assert len(results) == 2
    assert all(r["country"] == "germany" for r in results)


def test_db_filter_by_industry(company_db):
    results = company_db.filter_companies({"industry": ["software"]})
    assert len(results) == 3


def test_db_filter_multiple_columns(company_db):
    results = company_db.filter_companies(
        {
            "country": ["germany"],
            "industry": ["software"],
        }
    )
    assert len(results) == 1
    assert results[0]["name"] == "devhaus ag"


def test_db_filter_empty_means_all(company_db):
    results = company_db.filter_companies({"country": []})
    assert len(results) == 5


def test_db_filter_case_insensitive(company_db):
    results = company_db.filter_companies({"country": ["GERMANY"]})
    assert len(results) == 2


def test_db_filter_companies_chunk_size(company_db):
    """Verify chunk_size doesn't affect correctness."""
    results = company_db.filter_companies({"country": ["germany"]}, chunk_size=1)
    assert len(results) == 2
    assert all(r["country"] == "germany" for r in results)


# --- AgentDB Tests ---


@pytest.fixture
def agent_db():
    """Create an in-memory AgentDB for testing."""
    db = AgentDB("sqlite:///:memory:")
    yield db


def test_get_search_results_returns_iterable(agent_db):
    """Verify get_search_results returns an iterable that yields correct dicts."""
    agent_db.save_search_results(
        "batch1",
        "Acme Corp",
        "linkedin.com/company/acme",
        [{"name": "Alice", "title": "Engineer", "profile_url": "linkedin.com/in/alice"}]
    )
    results = agent_db.get_search_results("batch1")
    results_list = list(results)

    assert len(results_list) == 1
    emp = results_list[0]
    assert emp["name"] == "Alice"
    assert emp["title"] == "Engineer"
    assert emp["profile_url"] == "linkedin.com/in/alice"
    assert emp["company_name"] == "Acme Corp"
    assert emp["company_linkedin_url"] == "linkedin.com/company/acme"


def test_get_search_results_chunk_size(agent_db):
    """Verify chunk_size doesn't affect correctness."""
    employees = [
        {"name": f"Employee{i}", "title": f"Title{i}", "profile_url": f"linkedin.com/in/emp{i}"}
        for i in range(5)
    ]
    agent_db.save_search_results("batch2", "BigCo", "linkedin.com/company/bigco", employees)

    results = list(agent_db.get_search_results("batch2", chunk_size=2))

    assert len(results) == 5
    names = {r["name"] for r in results}
    assert names == {f"Employee{i}" for i in range(5)}


def test_get_search_results_empty(agent_db):
    """Verify empty result set works correctly."""
    results = list(agent_db.get_search_results("nonexistent"))
    assert results == []
