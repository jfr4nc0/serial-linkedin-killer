import asyncio
import os
from typing import Any, Dict, List, Optional, Union

from dotenv import load_dotenv
from fastmcp import Client
from fastmcp.client.transports import StdioTransport, StreamableHttpTransport

from src.core.model import ApplicationRequest, ApplicationResult, CVAnalysis, JobResult

# Load environment variables
load_dotenv()


class LinkedInMCPClient:
    """
    Official FastMCP client for communicating with the LinkedIn MCP server.
    Uses FastMCP's StdioTransport for protocol communication over stdio.
    The client manages the LinkedIn MCP server lifecycle as a subprocess.
    """

    def __init__(
        self,
        use_http: bool = True,
        server_url: Optional[str] = None,
        keep_alive: bool = True,
    ):
        self.use_http = use_http

        # Build server URL from config if not provided
        if server_url is None and use_http:
            from src.config.config_loader import load_config

            config = load_config()
            host = os.getenv("MCP_SERVER_HOST", config.mcp_server.host)
            port = os.getenv("MCP_SERVER_PORT", str(config.mcp_server.port))
            server_url = f"http://{host}:{port}/mcp"

        if use_http:
            # Use StreamableHttpTransport - connect to running HTTP server
            self.transport = StreamableHttpTransport(server_url)
            self.client = Client(self.transport)
        else:
            # Use stdio transport - launch server as subprocess
            env = {
                "LINKEDIN_EMAIL": os.getenv("LINKEDIN_EMAIL"),
                "LINKEDIN_PASSWORD": os.getenv("LINKEDIN_PASSWORD"),
                "LINKEDIN_MCP_LOG_LEVEL": os.getenv("LINKEDIN_MCP_LOG_LEVEL", "INFO"),
                "LINKEDIN_MCP_LOG_FILE": os.getenv("LINKEDIN_MCP_LOG_FILE"),
            }
            env = {k: v for k, v in env.items() if v is not None}

            command_parts = [
                "poetry",
                "run",
                "python",
                "-m",
                "src.linkedin_mcp.linkedin.linkedin_server",
            ]
            command = command_parts[0] if command_parts else "python"
            args = command_parts[1:] if len(command_parts) > 1 else []

            self.transport = StdioTransport(
                command=command, args=args, env=env, keep_alive=keep_alive
            )
            self.client = Client(self.transport)

    async def __aenter__(self):
        # FastMCP client handles both HTTP and stdio connections
        await self.client.__aenter__()
        return self

    async def list_tools(self):
        """
        Discover available tools on the LinkedIn MCP server.

        Returns:
            List of available tools with their metadata
        """
        return await self.client.list_tools()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.__aexit__(exc_type, exc_val, exc_tb)

    async def _call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call an MCP tool using FastMCP Client.

        Args:
            tool_name: Name of the MCP tool to call
            arguments: Tool arguments

        Returns:
            Tool result data

        Raises:
            Exception: If the MCP call fails
        """
        try:
            # Call the tool using FastMCP Client with manual error checking
            result = await self.client.call_tool(
                tool_name, arguments, raise_on_error=False
            )

            # Check if the tool execution failed
            if result.is_error:
                error_content = (
                    result.content[0].text if result.content else "Unknown error"
                )
                raise Exception(f"Tool '{tool_name}' execution failed: {error_content}")

            # FastMCP returns structured data directly
            return result.data

        except Exception as e:
            transport_type = "HTTP" if self.use_http else "stdio"
            raise Exception(
                f"FastMCP tool call failed for '{tool_name}' via {transport_type}: {str(e)}"
            )

    async def search_jobs(
        self,
        job_title: str,
        location: str,
        easy_apply: bool,
        email: str,
        password: str,
        limit: int = 50,
        trace_id: str = None,
    ) -> List[JobResult]:
        """
        Search for jobs on LinkedIn via MCP protocol.

        Args:
            job_title: The job title to search for
            location: The location to search in
            easy_apply: Whether to filter for easy apply jobs only
            email: LinkedIn email for authentication
            password: LinkedIn password for authentication
            limit: Maximum number of jobs to collect (default: 50)

        Returns:
            List of jobs with id_job and job_description
        """
        arguments = {
            "job_title": job_title,
            "location": location,
            "easy_apply": easy_apply,
            "email": email,
            "password": password,
            "limit": limit,
        }

        # Add trace_id if provided
        if trace_id:
            arguments["trace_id"] = trace_id

        result = await self._call_tool("search_jobs", arguments)

        # Convert result to JobResult format
        return [
            JobResult(id_job=job["id_job"], job_description=job["job_description"])
            for job in result
        ]

    async def search_employees(
        self,
        company_linkedin_url: str,
        company_name: str,
        email: str,
        password: str,
        limit: int = 10,
        trace_id: str = None,
    ) -> List[Dict[str, Any]]:
        """Search for employees at a company on LinkedIn via MCP protocol."""
        arguments = {
            "company_linkedin_url": company_linkedin_url,
            "company_name": company_name,
            "email": email,
            "password": password,
            "limit": limit,
        }
        if trace_id:
            arguments["trace_id"] = trace_id

        return await self._call_tool("search_employees", arguments)

    async def send_message(
        self,
        employee_profile_url: str,
        employee_name: str,
        message: str,
        email: str,
        password: str,
        trace_id: str = None,
    ) -> Dict[str, Any]:
        """Send a message or connection request to a LinkedIn user via MCP protocol."""
        arguments = {
            "employee_profile_url": employee_profile_url,
            "employee_name": employee_name,
            "message": message,
            "email": email,
            "password": password,
        }
        if trace_id:
            arguments["trace_id"] = trace_id

        return await self._call_tool("send_message", arguments)

    async def search_employees_batch(
        self,
        companies: List[Dict[str, Any]],
        email: str,
        password: str,
        total_limit: int = None,
        trace_id: str = None,
    ) -> List[Dict[str, Any]]:
        """Search employees across multiple companies in a single browser session."""
        arguments = {
            "companies": companies,
            "email": email,
            "password": password,
        }
        if total_limit is not None:
            arguments["total_limit"] = total_limit
        if trace_id:
            arguments["trace_id"] = trace_id

        return await self._call_tool("search_employees_batch", arguments)

    async def easy_apply_for_jobs(
        self,
        applications: List[ApplicationRequest],
        cv_analysis: Union[CVAnalysis, Dict[str, Any]],
        email: str,
        password: str,
        trace_id: str = None,
    ) -> List[ApplicationResult]:
        """
        Apply to multiple jobs using LinkedIn's easy apply via MCP protocol.

        Args:
            applications: List of application requests with job_id and monthly_salary
            cv_analysis: CV data as dict (JSON structure) or CVAnalysis object for AI form filling
            email: LinkedIn email for authentication
            password: LinkedIn password for authentication
            trace_id: Optional trace ID for correlation

        Returns:
            List of application results with id_job, success status, and optional error message
        """
        # Convert TypedDict to regular dict for JSON serialization
        applications_dict = [
            {"job_id": app["job_id"], "monthly_salary": app["monthly_salary"]}
            for app in applications
        ]

        # Handle cv_analysis as either dict or CVAnalysis object
        if isinstance(cv_analysis, dict):
            # CV data is already a dict (JSON structure)
            cv_analysis_dict = cv_analysis
        else:
            # Convert CVAnalysis to dict format
            cv_analysis_dict = {
                "skills": cv_analysis["skills"],
                "experience_years": cv_analysis["experience_years"],
                "previous_roles": cv_analysis["previous_roles"],
                "education": cv_analysis["education"],
                "certifications": cv_analysis["certifications"],
                "domains": cv_analysis["domains"],
                "key_achievements": cv_analysis["key_achievements"],
                "technologies": cv_analysis["technologies"],
            }

        arguments = {
            "applications": applications_dict,
            "cv_analysis": cv_analysis_dict,
            "email": email,
            "password": password,
        }

        # Add trace_id if provided
        if trace_id:
            arguments["trace_id"] = trace_id

        result = await self._call_tool("easy_apply_for_jobs", arguments)

        # Convert result to ApplicationResult format
        return [
            ApplicationResult(
                id_job=app_result["id_job"],
                success=app_result["success"],
                error=app_result.get("error"),
            )
            for app_result in result
        ]
