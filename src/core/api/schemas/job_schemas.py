"""Request/response schemas for the job application workflow."""

from typing import Any, Dict, List

from pydantic import BaseModel

from src.core.api.schemas.common import CredentialsModel


class JobSearchItem(BaseModel):
    job_title: str
    location: str
    monthly_salary: int
    limit: int = 20


class JobApplyRequest(BaseModel):
    job_searches: List[JobSearchItem]
    credentials: CredentialsModel
    cv_data_path: str = "./data/cv_data.json"


class JobApplyResponse(BaseModel):
    task_id: str
    status: str
    total_jobs_found: int
    total_filtered: int
    total_applied: int
    all_found_jobs: List[Dict[str, Any]]
    filtered_jobs: List[Dict[str, Any]]
    application_results: List[Dict[str, Any]]
    cv_analysis: Dict[str, Any]
    errors: List[str]
    trace_id: str
