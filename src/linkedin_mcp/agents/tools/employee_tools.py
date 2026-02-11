"""MCP tools for employee search and messaging."""

from loguru import logger

from src.config.trace_context import set_trace_id
from src.linkedin_mcp.model.outreach_types import EmployeeResult, MessageResult


def register_employee_tools(mcp, employee_outreach_service):
    """Register employee-related MCP tools."""

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
        # Set trace context (auto-propagates to all logs)
        if trace_id:
            set_trace_id(trace_id)

        logger.info(
            f"Starting employee search for {company_name}",
            company=company_name,
        )

        user_credentials = {"email": email, "password": password}
        result = employee_outreach_service.search_employees(
            company_linkedin_url, company_name, limit, user_credentials
        )

        logger.info(
            f"Employee search completed: found {len(result)} employees",
            employees_found=len(result),
        )

        return result

    @mcp.tool
    def send_messages_batch(
        messages: str,
        email: str,
        password: str,
        trace_id: str = None,
    ) -> list[dict]:
        """
        Send multiple messages using a single browser session.
        Much more efficient than calling send_message per employee.

        Args:
            messages: JSON string of list of dicts with keys: profile_url, name, message, subject
            email: LinkedIn email for authentication
            password: LinkedIn password for authentication
            trace_id: Optional trace ID for correlation

        Returns:
            List of MessageResult dicts with sent status per message
        """
        import json as _json

        if trace_id:
            set_trace_id(trace_id)

        parsed_messages = _json.loads(messages)
        logger.info(
            f"Starting batch message send: {len(parsed_messages)} messages",
        )

        user_credentials = {"email": email, "password": password}
        results = employee_outreach_service.send_messages_batch(
            parsed_messages, user_credentials, trace_id=trace_id
        )

        successful = sum(1 for r in results if r.get("sent"))
        logger.info(
            f"Batch send complete: {successful}/{len(results)} sent",
        )

        return results

    @mcp.tool
    def search_employees_batch(
        companies: list[dict],
        email: str,
        password: str,
        total_limit: int = None,
        exclude_companies: list[str] = None,
        exclude_profile_urls: list[str] = None,
        batch_id: str = None,
        trace_id: str = None,
    ) -> dict:
        """
        Search employees across multiple companies in a single browser session.
        Much more efficient than calling search_employees per company.

        Args:
            companies: List of dicts with company_linkedin_url, company_name, and limit
            email: LinkedIn email for authentication
            password: LinkedIn password for authentication
            total_limit: Optional max total employees across all companies
            exclude_companies: Optional list of company LinkedIn URLs to skip
            exclude_profile_urls: Optional list of employee profile URLs to exclude from results
            trace_id: Optional trace ID for correlation

        Returns:
            List of results per company with employees and errors
        """
        # Set trace context (auto-propagates to all logs)
        if trace_id:
            set_trace_id(trace_id)

        logger.info(
            f"Starting batch employee search: {len(companies)} companies"
            + (f", total_limit={total_limit}" if total_limit else ""),
            companies_count=len(companies),
        )

        user_credentials = {"email": email, "password": password}
        result = employee_outreach_service.submit_search_batch(
            companies,
            user_credentials,
            batch_id=batch_id or str(__import__("uuid").uuid4()),
            trace_id=trace_id or "",
            total_limit=total_limit,
            exclude_companies=exclude_companies,
            exclude_profile_urls=exclude_profile_urls,
        )

        logger.info(f"Batch search submitted, batch_id={result['batch_id']}")

        return result
