"""Request/response schemas for the outreach workflow."""

from typing import Any, Dict, List

from pydantic import BaseModel

from src.core.api.schemas.common import CredentialsModel


class OutreachFiltersResponse(BaseModel):
    industries: List[str]
    countries: List[str]
    sizes: List[str]
    total_companies: int


# Legacy single-phase request (kept for backward compatibility)
class OutreachRunRequest(BaseModel):
    filters: Dict[str, List[str]]
    message_template: str
    template_variables: Dict[str, str]
    credentials: CredentialsModel
    warm_up: bool = False


class OutreachRunResponse(BaseModel):
    task_id: str
    status: str
    employees_found: List[Dict[str, Any]]
    message_results: List[Dict[str, Any]]
    messages_sent: int
    errors: List[str]
    trace_id: str


# Phase 1: Search & Cluster
class OutreachSearchRequest(BaseModel):
    """Request to search employees and cluster by role."""

    filters: Dict[str, List[str]]
    credentials: CredentialsModel


class OutreachSearchResponse(BaseModel):
    """Response with employees clustered by role category."""

    session_id: str
    role_groups: Dict[str, List[Dict[str, Any]]]
    total_employees: int
    companies_processed: int
    trace_id: str


# Phase 2: Send Messages
class RoleGroupConfig(BaseModel):
    """Configuration for messaging a single role group."""

    enabled: bool = True
    message_template: str
    template_variables: Dict[str, str] = {}


class OutreachSendRequest(BaseModel):
    """Request to send messages to selected role groups."""

    session_id: str
    selected_groups: Dict[str, RoleGroupConfig]
    credentials: CredentialsModel
    warm_up: bool = False


class OutreachSendResponse(BaseModel):
    """Response from the send phase (delivered via Kafka)."""

    task_id: str
    status: str
    message_results: List[Dict[str, Any]]
    messages_sent: int
    results_by_role: Dict[str, Dict[str, Any]]
    errors: List[str]
    trace_id: str
