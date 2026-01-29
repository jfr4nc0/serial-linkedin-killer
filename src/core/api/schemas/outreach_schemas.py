"""Request/response schemas for the outreach workflow."""

from typing import Any, Dict, List

from pydantic import BaseModel

from src.core.api.schemas.common import CredentialsModel


class OutreachFiltersResponse(BaseModel):
    industries: List[str]
    countries: List[str]
    sizes: List[str]
    total_companies: int


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
