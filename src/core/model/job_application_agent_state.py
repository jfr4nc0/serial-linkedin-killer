from typing import Any, Dict, List, TypedDict

from src.core.model.application_result import ApplicationResult
from src.core.model.cv_analysis import CVAnalysis
from src.core.model.job_result import JobResult
from src.core.model.job_search_request import JobSearchRequest


class JobApplicationAgentState(TypedDict):
    # Input from user
    job_searches: List[JobSearchRequest]
    cv_content: str  # JSON string containing CV data
    user_credentials: Dict[str, str]  # {email, password}

    # Processing state
    current_search_index: int
    all_found_jobs: List[JobResult]
    filtered_jobs: List[JobResult]
    application_results: List[ApplicationResult]

    # Agent memory
    cv_analysis: CVAnalysis
    conversation_history: List[Dict[str, Any]]
    errors: List[str]

    # Status tracking
    total_jobs_found: int
    total_jobs_applied: int
    current_status: str

    # Observability
    trace_id: str  # UUID for tracing this workflow execution
