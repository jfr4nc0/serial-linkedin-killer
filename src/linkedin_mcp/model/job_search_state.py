import operator
from typing import Annotated, List, Optional, TypedDict

from src.linkedin_mcp.interfaces.services import IBrowserManager
from src.linkedin_mcp.model.types import JobResult


class JobSearchState(TypedDict):
    job_title: str
    location: str
    easy_apply: bool
    limit: int
    browser_manager: IBrowserManager
    current_page: int
    collected_jobs: Annotated[List[JobResult], operator.add]
    search_url: Optional[str]
    total_found: int
    errors: Annotated[List[str], operator.add]
