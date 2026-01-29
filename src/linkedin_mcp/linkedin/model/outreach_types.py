"""Type definitions for employee outreach workflow."""

from typing import Any, List, Optional, TypedDict

from src.linkedin_mcp.linkedin.interfaces.services import IBrowserManager


class EmployeeResult(TypedDict):
    name: str
    title: str
    profile_url: str


class MessageResult(TypedDict):
    employee_profile_url: str
    employee_name: str
    sent: bool
    method: str  # "direct_message" or "connection_request"
    error: Optional[str]


class EmployeeSearchState(TypedDict):
    company_linkedin_url: str
    company_name: str
    browser_manager: IBrowserManager
    collected_employees: List[EmployeeResult]
    current_page: int
    limit: int
    errors: List[str]


class MessageSendState(TypedDict):
    employee_profile_url: str
    employee_name: str
    message_text: str
    browser_manager: IBrowserManager
    sent: bool
    method: str
    error: str
