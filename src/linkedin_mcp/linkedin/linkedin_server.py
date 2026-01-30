"""
LinkedIn MCP Server - Main entry point
Uses standard TCP implementation for MCP protocol
"""

import atexit
import os
import signal
import sys

from fastmcp import FastMCP

from src.linkedin_mcp.linkedin.model.outreach_types import EmployeeResult, MessageResult
from src.linkedin_mcp.linkedin.model.types import (
    ApplicationRequest,
    ApplicationResult,
    CVAnalysis,
    JobResult,
)
from src.linkedin_mcp.linkedin.services.employee_outreach_service import (
    EmployeeOutreachService,
)
from src.linkedin_mcp.linkedin.services.job_application_service import (
    JobApplicationService,
)
from src.linkedin_mcp.linkedin.services.job_search_service import JobSearchService
from src.linkedin_mcp.linkedin.utils.logging_config import (
    configure_mcp_logging,
    log_mcp_server_startup,
    log_mcp_tool_registration,
)

# Configure logging for LinkedIn MCP server
configure_mcp_logging()

mcp = FastMCP("LinkedIn Job Applier")

# Log server startup
log_mcp_server_startup(
    {
        "name": "LinkedIn Job Applier",
        "version": "1.16.0",
        "transport": "stdio",
        "fastmcp_version": "2.12.4",
        "mcp_sdk_version": "1.16.0",
    }
)

# Initialize services
job_search_service = JobSearchService()
job_application_service = JobApplicationService()
employee_outreach_service = EmployeeOutreachService()


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
    # Log with trace_id if provided
    from src.linkedin_mcp.linkedin.utils.logging_config import get_mcp_logger

    if trace_id:
        logger = get_mcp_logger(trace_id)
        logger.info(
            f"Starting job search: {job_title} in {location}",
            job_title=job_title,
            location=location,
            trace_id=trace_id,
        )

    # Pass credentials as a dictionary as expected by the service
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
    # Log with trace_id if provided
    from src.linkedin_mcp.linkedin.utils.logging_config import get_mcp_logger

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


@mcp.tool
def search_employees(
    company_linkedin_url: str,
    company_name: str,
    email: str,
    password: str,
    limit: int = 10,
    trace_id: str = None,
) -> list[EmployeeResult]:
    """
    Search for employees at a company on LinkedIn.

    Args:
        company_linkedin_url: LinkedIn URL of the company (e.g. linkedin.com/company/example)
        company_name: Name of the company
        email: LinkedIn email for authentication
        password: LinkedIn password for authentication
        limit: Maximum number of employees to collect (default: 10)
        trace_id: Optional trace ID for correlation

    Returns:
        List of employees with name, title, and profile_url
    """
    from src.linkedin_mcp.linkedin.utils.logging_config import get_mcp_logger

    if trace_id:
        logger = get_mcp_logger(trace_id)
        logger.info(
            f"Starting employee search for {company_name}",
            company=company_name,
            trace_id=trace_id,
        )

    user_credentials = {"email": email, "password": password}
    result = employee_outreach_service.search_employees(
        company_linkedin_url, company_name, limit, user_credentials
    )

    if trace_id:
        logger.info(
            f"Employee search completed: found {len(result)} employees",
            employees_found=len(result),
            trace_id=trace_id,
        )

    return result


@mcp.tool
def send_message(
    employee_profile_url: str,
    employee_name: str,
    message: str,
    email: str,
    password: str,
    trace_id: str = None,
) -> MessageResult:
    """
    Send a message or connection request to a LinkedIn user.
    Automatically detects whether to send a direct message or connection request with note.

    Args:
        employee_profile_url: LinkedIn profile URL of the employee
        employee_name: Name of the employee
        message: Message text to send (truncated to 300 chars for connection requests)
        email: LinkedIn email for authentication
        password: LinkedIn password for authentication
        trace_id: Optional trace ID for correlation

    Returns:
        MessageResult with sent status, method used, and optional error
    """
    from src.linkedin_mcp.linkedin.utils.logging_config import get_mcp_logger

    if trace_id:
        logger = get_mcp_logger(trace_id)
        logger.info(
            f"Sending message to {employee_name}",
            employee=employee_name,
            trace_id=trace_id,
        )

    user_credentials = {"email": email, "password": password}
    result = employee_outreach_service.send_message(
        employee_profile_url, employee_name, message, user_credentials
    )

    if trace_id:
        logger.info(
            f"Message send result: sent={result['sent']}, method={result.get('method', '')}",
            sent=result["sent"],
            trace_id=trace_id,
        )

    return result


@mcp.tool
def search_employees_batch(
    companies: list[dict],
    email: str,
    password: str,
    total_limit: int = None,
    trace_id: str = None,
) -> list[dict]:
    """
    Search employees across multiple companies in a single browser session.
    Much more efficient than calling search_employees per company.

    Args:
        companies: List of dicts with company_linkedin_url, company_name, and limit
        email: LinkedIn email for authentication
        password: LinkedIn password for authentication
        total_limit: Optional max total employees across all companies
        trace_id: Optional trace ID for correlation

    Returns:
        List of results per company with employees and errors
    """
    from src.linkedin_mcp.linkedin.utils.logging_config import get_mcp_logger

    if trace_id:
        logger = get_mcp_logger(trace_id)
        logger.info(
            f"Starting batch employee search: {len(companies)} companies"
            + (f", total_limit={total_limit}" if total_limit else ""),
            companies_count=len(companies),
            trace_id=trace_id,
        )

    user_credentials = {"email": email, "password": password}
    result = employee_outreach_service.search_employees_batch(
        companies, user_credentials, total_limit=total_limit
    )

    if trace_id:
        total_employees = sum(len(r.get("employees", [])) for r in result)
        logger.info(
            f"Batch employee search completed: {total_employees} employees across {len(companies)} companies",
            total_employees=total_employees,
            trace_id=trace_id,
        )

    return result


# Log registered tools
log_mcp_tool_registration(
    [
        {"name": "search_jobs", "description": "Search LinkedIn jobs with filters"},
        {
            "name": "easy_apply_for_jobs",
            "description": "Apply to jobs using Easy Apply with AI form handling",
        },
        {
            "name": "search_employees",
            "description": "Search for employees at a LinkedIn company",
        },
        {
            "name": "send_message",
            "description": "Send message or connection request to a LinkedIn user",
        },
        {
            "name": "search_employees_batch",
            "description": "Search employees across multiple companies in single browser session",
        },
    ]
)


def _shutdown_services(*args):
    """Cleanup all services on shutdown."""
    for service in [
        employee_outreach_service,
        job_search_service,
        job_application_service,
    ]:
        try:
            if hasattr(service, "browser_manager"):
                service.browser_manager.close_browser()
        except Exception:
            pass
    from src.linkedin_mcp.linkedin.services.browser_manager_service import (
        BrowserManagerService,
    )

    BrowserManagerService.cleanup_all()


atexit.register(_shutdown_services)

import threading

if threading.current_thread() is threading.main_thread():
    signal.signal(signal.SIGTERM, lambda s, f: (_shutdown_services(), sys.exit(0)))
    signal.signal(signal.SIGINT, lambda s, f: (_shutdown_services(), sys.exit(0)))


if __name__ == "__main__":
    import argparse

    from src.config.config_loader import load_config

    # Load config from YAML
    config = load_config()
    default_host = os.getenv("MCP_SERVER_HOST", config.mcp_server.host)
    default_port = int(os.getenv("MCP_SERVER_PORT", str(config.mcp_server.port)))

    parser = argparse.ArgumentParser(description="LinkedIn MCP Server")
    parser.add_argument("--http", action="store_true", help="Run as HTTP server")
    parser.add_argument("--host", default=default_host, help="HTTP server host")
    parser.add_argument(
        "--port", type=int, default=default_port, help="HTTP server port"
    )
    args = parser.parse_args()

    if args.http:
        # Run as direct HTTP server using FastMCP's built-in HTTP transport
        print(f"Starting LinkedIn MCP HTTP server on {args.host}:{args.port}")
        mcp.run(transport="http", host=args.host, port=args.port)
    else:
        # Run via stdio transport (default MCP pattern)
        mcp.run()
