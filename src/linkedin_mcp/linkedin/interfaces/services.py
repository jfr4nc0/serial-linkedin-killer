"""Service interface definitions."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from selenium.webdriver.remote.webdriver import WebDriver

from src.linkedin_mcp.linkedin.model.types import (
    ApplicationRequest,
    ApplicationResult,
    CVAnalysis,
    JobResult,
)


class IBrowserManager(ABC):
    """Interface for browser management services."""

    @abstractmethod
    def get_driver(self) -> WebDriver:
        """Get the current WebDriver instance."""
        pass

    @abstractmethod
    def navigate_to_job(self, job_id: str) -> None:
        """Navigate to a specific job page."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up browser resources."""
        pass


class IJobApplicationService(ABC):
    """Interface for job application services."""

    @abstractmethod
    def apply_to_jobs(
        self,
        applications: List[ApplicationRequest],
        cv_analysis: CVAnalysis,
        user_credentials: Dict[str, str],
    ) -> List[ApplicationResult]:
        """
        Apply to multiple jobs.

        Args:
            applications: List of job applications to process
            cv_analysis: CV analysis results
            user_credentials: User authentication credentials

        Returns:
            List of application results
        """
        pass


class IEmployeeOutreachService(ABC):
    """Interface for employee outreach services."""

    @abstractmethod
    def search_employees(
        self,
        company_linkedin_url: str,
        company_name: str,
        limit: int,
        user_credentials: Dict[str, str],
    ) -> list:
        """Search for employees at a company on LinkedIn."""
        pass

    @abstractmethod
    def send_message(
        self,
        employee_profile_url: str,
        employee_name: str,
        message: str,
        user_credentials: Dict[str, str],
    ) -> dict:
        """Send a message or connection request to an employee."""
        pass


class IJobSearchService(ABC):
    """Interface for job search services."""

    @abstractmethod
    def search_jobs(
        self,
        job_title: str,
        location: str,
        limit: int,
        user_credentials: Dict[str, str],
    ) -> List[JobResult]:
        """
        Search for jobs on LinkedIn.

        Args:
            job_title: Job title to search for
            location: Location to search in
            limit: Maximum number of jobs to return
            user_credentials: User authentication credentials

        Returns:
            List of job search results
        """
        pass
