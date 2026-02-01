"""MCP tools for employee search and messaging."""

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
        from src.linkedin_mcp.utils.logging_config import get_mcp_logger

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
        from src.linkedin_mcp.utils.logging_config import get_mcp_logger

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
        exclude_companies: list[str] = None,
        exclude_profile_urls: list[str] = None,
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
            exclude_companies: Optional list of company LinkedIn URLs to skip
            exclude_profile_urls: Optional list of employee profile URLs to exclude from results
            trace_id: Optional trace ID for correlation

        Returns:
            List of results per company with employees and errors
        """
        from src.linkedin_mcp.utils.logging_config import get_mcp_logger

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
            companies,
            user_credentials,
            total_limit=total_limit,
            exclude_companies=exclude_companies,
            exclude_profile_urls=exclude_profile_urls,
        )

        if trace_id:
            total_employees = sum(len(r.get("employees", [])) for r in result)
            logger.info(
                f"Batch employee search completed: {total_employees} employees across {len(companies)} companies",
                total_employees=total_employees,
                trace_id=trace_id,
            )

        return result
