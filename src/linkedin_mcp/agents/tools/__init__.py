from src.linkedin_mcp.agents.tools.employee_tools import register_employee_tools
from src.linkedin_mcp.agents.tools.job_tools import register_job_tools


def register_all_tools(
    mcp, job_search_service, job_application_service, employee_outreach_service
):
    """Register all MCP tools on the given server instance."""
    register_job_tools(mcp, job_search_service, job_application_service)
    register_employee_tools(mcp, employee_outreach_service)
