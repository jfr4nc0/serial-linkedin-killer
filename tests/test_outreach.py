"""Tests for the employee outreach components."""

import os
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from src.config.config_loader import AgentConfig, load_config
from src.core.tools.company_loader import filter_companies, get_unique_values, load_companies
from src.core.tools.message_template import render_template


# --- Company Loader Tests ---


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


def test_load_companies(sample_csv):
    df = load_companies(sample_csv)
    assert len(df) == 5
    assert list(df.columns) == [
        "country", "founded", "id", "industry", "linkedin_url",
        "locality", "name", "region", "size", "website",
    ]


def test_get_unique_values(sample_csv):
    df = load_companies(sample_csv)

    countries = get_unique_values(df, "country")
    assert "germany" in countries
    assert "united states" in countries
    assert "romania" in countries
    assert len(countries) == 3

    industries = get_unique_values(df, "industry")
    assert "software" in industries
    assert "automotive" in industries
    assert len(industries) == 3


def test_filter_by_country(sample_csv):
    df = load_companies(sample_csv)
    filtered = filter_companies(df, {"country": ["germany"]})
    assert len(filtered) == 2
    assert all(filtered["country"] == "germany")


def test_filter_by_industry(sample_csv):
    df = load_companies(sample_csv)
    filtered = filter_companies(df, {"industry": ["software"]})
    assert len(filtered) == 3


def test_filter_by_multiple_columns(sample_csv):
    df = load_companies(sample_csv)
    filtered = filter_companies(df, {
        "country": ["germany"],
        "industry": ["software"],
    })
    assert len(filtered) == 1
    assert filtered.iloc[0]["name"] == "devhaus ag"


def test_filter_empty_values_means_all(sample_csv):
    df = load_companies(sample_csv)
    filtered = filter_companies(df, {"country": []})
    assert len(filtered) == 5


def test_filter_case_insensitive(sample_csv):
    df = load_companies(sample_csv)
    filtered = filter_companies(df, {"country": ["GERMANY"]})
    assert len(filtered) == 2


# --- Message Template Tests ---


def test_render_template_basic():
    template = "Hi {employee_name}, I work at {company_name}."
    result = render_template(template, {
        "employee_name": "Alice",
        "company_name": "Acme",
    })
    assert result == "Hi Alice, I work at Acme."


def test_render_template_missing_variable():
    template = "Hi {employee_name}, topic: {topic}"
    result = render_template(template, {"employee_name": "Bob"})
    assert result == "Hi Bob, topic: "


def test_render_template_static_and_dynamic():
    template = "Hi {employee_name}, I'm {my_name}, a {my_role} at {company_name}."
    result = render_template(template, {
        "employee_name": "Carol",
        "company_name": "TechCo",
        "my_name": "Dan",
        "my_role": "Engineer",
    })
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
