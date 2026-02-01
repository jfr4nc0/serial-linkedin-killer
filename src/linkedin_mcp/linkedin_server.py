"""
LinkedIn MCP Server - Main entry point
Uses standard TCP implementation for MCP protocol
"""

import atexit
import os
import signal
import sys

from fastmcp import FastMCP

from src.linkedin_mcp.agents.tools import register_all_tools
from src.linkedin_mcp.services.employee_outreach_service import EmployeeOutreachService
from src.linkedin_mcp.services.job_application_service import JobApplicationService
from src.linkedin_mcp.services.job_search_service import JobSearchService
from src.linkedin_mcp.utils.logging_config import (
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

# Register all MCP tools
register_all_tools(
    mcp, job_search_service, job_application_service, employee_outreach_service
)

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
    from src.linkedin_mcp.services.browser_manager_service import BrowserManagerService

    BrowserManagerService.cleanup_all()


atexit.register(_shutdown_services)


def _signal_handler(sig, frame):
    """Handle SIGTERM/SIGINT: cleanup then hard exit to avoid threading deadlocks."""
    _shutdown_services()
    os._exit(0)


import threading

if threading.current_thread() is threading.main_thread():
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)


if __name__ == "__main__":
    import argparse

    from src.config.config_loader import load_config

    # Load config from YAML
    config = load_config()
    default_host = os.getenv("MCP_SERVER_HOST", config.mcp_server.host)
    default_port = int(os.getenv("MCP_SERVER_PORT", str(config.mcp_server.port)))

    parser = argparse.ArgumentParser(description="LinkedIn MCP Server")
    parser.add_argument("--host", default=default_host, help="HTTP server host")
    parser.add_argument(
        "--port", type=int, default=default_port, help="HTTP server port"
    )
    args = parser.parse_args()

    print(f"Starting LinkedIn MCP HTTP server on {args.host}:{args.port}")
    mcp.run(transport="http", host=args.host, port=args.port)
