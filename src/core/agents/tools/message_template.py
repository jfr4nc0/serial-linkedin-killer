"""Message template rendering with named placeholders."""

from collections import defaultdict
from pathlib import Path
from typing import Dict


def load_template(template_path: str) -> str:
    """Load a message template from a file."""
    return Path(template_path).read_text(encoding="utf-8")


def extract_first_name(full_name: str) -> str:
    """Extract the first name from a full name string."""
    if not full_name:
        return ""
    return full_name.split()[0]


def render_template(template: str, variables: Dict[str, str]) -> str:
    """Render a message template with named variables.

    Uses str.format_map with a defaultdict so missing variables
    are left as-is (e.g. {unknown_var} stays in the output).

    Available dynamic variables (populated per-employee):
        {employee_name} - first name only (e.g., "Ignacio")
        {employee_full_name} - full name (e.g., "Ignacio Castelar Carballo")
        {company_name}, {employee_title}

    Available static variables (from config/TUI input):
        {my_name}, {my_role}, {topic}, {custom_closing}, etc.
    """
    # Auto-extract first name if full name is provided
    if "employee_name" in variables and "employee_full_name" not in variables:
        full_name = variables["employee_name"]
        variables = dict(variables)  # Don't mutate original
        variables["employee_full_name"] = full_name
        variables["employee_name"] = extract_first_name(full_name)

    safe_vars = defaultdict(str, variables)
    return template.format_map(safe_vars)
