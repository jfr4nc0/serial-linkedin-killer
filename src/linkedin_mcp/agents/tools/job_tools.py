"""MCP tools for job search and application."""

from src.linkedin_mcp.model.types import (
    ApplicationRequest,
    ApplicationResult,
    JobResult,
)


def register_job_tools(mcp, job_search_service, job_application_service):
    """Register job-related MCP tools."""

    @mcp.tool
    def search_jobs(
        job_title: str,
        location: str,
        easy_apply: bool,
        email: str,
        password: str,
        limit: int = 50,
        trace_id: str = None,
    ) -> list[JobResult]:
        """
        Search for jobs on LinkedIn based on title, location, and easy apply filter.
        Handles authentication automatically and paginates through results.

        Args:
            job_title: The job title to search for
            location: The location to search in
            easy_apply: Whether to filter for easy apply jobs only
            email: LinkedIn email for authentication
            password: LinkedIn password for authentication
            limit: Maximum number of jobs to collect (default: 50)
            trace_id: Optional trace ID for correlation

        Returns:
            List of jobs with id_job and job_description
        """
        from src.linkedin_mcp.utils.logging_config import get_mcp_logger

        if trace_id:
            logger = get_mcp_logger(trace_id)
            logger.info(
                f"Starting job search: {job_title} in {location}",
                job_title=job_title,
                location=location,
                trace_id=trace_id,
            )

        user_credentials = {"email": email, "password": password}
        result = job_search_service.search_jobs(
            job_title, location, limit, user_credentials
        )

        if trace_id:
            logger.info(
                f"Job search completed: found {len(result)} jobs",
                jobs_found=len(result),
                trace_id=trace_id,
            )

        return result

    @mcp.tool
    def easy_apply_for_jobs(
        applications: list[ApplicationRequest],
        cv_analysis: dict,
        email: str,
        password: str,
        trace_id: str = None,
    ) -> list[ApplicationResult]:
        """
        Apply to multiple jobs using LinkedIn's easy apply feature with AI-powered form handling.
        Handles authentication automatically and uses CV data to answer form questions intelligently.

        Args:
            applications: List of application requests with job_id and monthly_salary
            cv_analysis: Full CV data as dictionary (JSON structure with work_experience, skills, etc.)
            email: LinkedIn email for authentication
            password: LinkedIn password for authentication
            trace_id: Optional trace ID for correlation

        Returns:
            List of application results with id_job, success status, and optional error message
        """
        from src.linkedin_mcp.utils.logging_config import get_mcp_logger

        if trace_id:
            logger = get_mcp_logger(trace_id)
            logger.info(
                f"Starting job applications: {len(applications)} applications",
                applications_count=len(applications),
                trace_id=trace_id,
            )

        user_credentials = {"email": email, "password": password}
        result = job_application_service.apply_to_jobs(
            applications, cv_analysis, user_credentials
        )

        if trace_id:
            successful_count = sum(1 for r in result if r.success)
            logger.info(
                f"Job applications completed: {successful_count}/{len(applications)} successful",
                applications_count=len(applications),
                successful_count=successful_count,
                trace_id=trace_id,
            )

        return result
