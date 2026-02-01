"""
Main source package for the job application system.
"""

from src.core.agent import JobApplicationAgent
from src.core.agents.tools.cv_analysis_tools import analyze_cv_structure, read_pdf_cv
from src.core.model.application_request import ApplicationRequest
from src.core.model.application_result import ApplicationResult
from src.core.model.cv_analysis import CVAnalysis
from src.core.model.job_application_agent_state import JobApplicationAgentState
from src.core.model.job_result import JobResult
from src.core.model.job_search_request import JobSearchRequest
from src.core.providers.linkedin_mcp_client_sync import LinkedInMCPClientSync
from src.core.providers.llm_client import get_llm_client

__all__ = [
    # Types
    "JobSearchRequest",
    "JobResult",
    "ApplicationRequest",
    "ApplicationResult",
    "CVAnalysis",
    "JobApplicationAgentState",
    # Providers
    "get_llm_client",
    "LinkedInMCPClientSync",
    # Tools
    "read_pdf_cv",
    "analyze_cv_structure",
    # Agent
    "JobApplicationAgent",
]
