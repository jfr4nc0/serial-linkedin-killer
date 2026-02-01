"""Message template rendering with named placeholders."""

from collections import defaultdict
from pathlib import Path
from typing import Dict


def load_template(template_path: str) -> str:
    """Load a message template from a file."""
    return Path(template_path).read_text(encoding="utf-8")


def render_template(template: str, variables: Dict[str, str]) -> str:
    """Render a message template with named variables.

    Uses str.format_map with a defaultdict so missing variables
    are left as-is (e.g. {unknown_var} stays in the output).

    Available dynamic variables (populated per-employee):
        {employee_name}, {company_name}, {employee_title}

    Available static variables (from config/TUI input):
        {my_name}, {my_role}, {topic}, {custom_closing}, etc.
    """
    safe_vars = defaultdict(str, variables)
    return template.format_map(safe_vars)
