"""Agent interface definitions."""

from abc import ABC, abstractmethod
from typing import Any, Dict

from src.linkedin_mcp.model.types import ApplicationRequest, CVAnalysis


class IJobApplicationAgent(ABC):
    """Interface for job application agents."""

    @abstractmethod
    def apply_to_job(
        self,
        job_id: str,
        application_request: ApplicationRequest,
        cv_analysis: CVAnalysis,
        browser_manager: Any,  # IBrowserManager
    ) -> Dict[str, Any]:
        """
        Apply to a specific job.

        Args:
            job_id: LinkedIn job ID
            application_request: Application details
            cv_analysis: CV analysis results
            browser_manager: Browser management service

        Returns:
            Application result dictionary
        """
        pass

    @abstractmethod
    def is_easy_apply_available(self, job_id: str, browser_manager: Any) -> bool:
        """Check if Easy Apply is available for the job."""
        pass
