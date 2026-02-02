"""State definition for the outreach agent LangGraph workflow."""

from typing import Any, Dict, List, Optional, TypedDict


class OutreachAgentState(TypedDict):
    # Company data
    companies: List[Dict[str, str]]  # Filtered company records from CSV
    company_filters: Dict[str, List[str]]  # {industry: [], country: [], size: []}

    # Message template
    message_template: str
    template_variables: Dict[str, str]  # Static vars: {my_name}, {my_role}, etc.

    # Credentials
    user_credentials: Dict[str, str]  # {email, password}

    # Results
    employees_found: List[Dict[str, Any]]  # [{company_name, name, profile_url, title}]
    message_results: List[
        Dict[str, Any]
    ]  # [{employee_profile_url, sent, method, error}]
    errors: List[str]

    # Progress tracking
    current_status: str
    trace_id: str
    daily_message_limit: int
    messages_sent_today: int

    # Search limits
    total_limit: Optional[int]  # Max total employees across all companies

    # User-provided exclusions (LinkedIn URLs)
    exclude_companies: Optional[List[str]]
    exclude_profile_urls: Optional[List[str]]
