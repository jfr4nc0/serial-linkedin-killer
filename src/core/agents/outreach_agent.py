"""LangGraph agent for employee outreach workflow."""

import json
import uuid
from pathlib import Path
from typing import Any, Dict, List

from langgraph.graph import END, StateGraph
from loguru import logger

from src.config.config_loader import load_config
from src.core.model.outreach_state import OutreachAgentState
from src.core.providers.linkedin_mcp_client_sync import LinkedInMCPClientSync
from src.core.tools.company_loader import filter_companies, load_companies
from src.core.tools.message_template import load_template, render_template
from src.core.utils.logging_config import get_core_agent_logger


class EmployeeOutreachAgent:
    """
    LangGraph agent that orchestrates the employee outreach workflow:
    1. Load and filter companies from CSV dataset
    2. Search for employees at each company on LinkedIn
    3. Send messages to employees using a configurable template
    """

    def __init__(self, config_path: str = None):
        self.config = load_config(config_path)
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(OutreachAgentState)

        workflow.add_node("search_employees_node", self.search_employees_node)
        workflow.add_node("send_messages_node", self.send_messages_node)

        workflow.set_entry_point("search_employees_node")
        workflow.add_edge("search_employees_node", "send_messages_node")
        workflow.add_edge("send_messages_node", END)

        return workflow.compile()

    def search_employees_node(self, state: OutreachAgentState) -> Dict[str, Any]:
        """Search for employees at each filtered company via MCP."""
        trace_id = state.get("trace_id", str(uuid.uuid4()))
        agent_logger = get_core_agent_logger(trace_id)

        all_employees = []

        try:
            mcp_client = LinkedInMCPClientSync()
            employees_per_company = self.config.outreach.employees_per_company

            for company in state["companies"]:
                company_name = company.get("name", "Unknown")
                linkedin_url = company.get("linkedin_url", "")

                if not linkedin_url:
                    agent_logger.warning(f"Skipping {company_name}: no linkedin_url")
                    continue

                try:
                    agent_logger.info(
                        f"Searching employees at {company_name}",
                        company=company_name,
                    )

                    employees = mcp_client.search_employees(
                        company_linkedin_url=linkedin_url,
                        company_name=company_name,
                        email=state["user_credentials"]["email"],
                        password=state["user_credentials"]["password"],
                        limit=employees_per_company,
                        trace_id=trace_id,
                    )

                    for emp in employees:
                        emp["company_name"] = company_name
                    all_employees.extend(employees)

                except Exception as e:
                    error_msg = f"Failed to search employees at {company_name}: {str(e)}"
                    agent_logger.error(error_msg)
                    state["errors"] = state.get("errors", []) + [error_msg]

            return {
                **state,
                "employees_found": all_employees,
                "current_status": f"Found {len(all_employees)} employees across {len(state['companies'])} companies",
            }

        except Exception as e:
            error_msg = f"Employee search failed: {str(e)}"
            return {
                **state,
                "errors": state.get("errors", []) + [error_msg],
                "current_status": "Employee search failed",
            }

    def send_messages_node(self, state: OutreachAgentState) -> Dict[str, Any]:
        """Send messages to all found employees via MCP."""
        trace_id = state.get("trace_id", str(uuid.uuid4()))
        agent_logger = get_core_agent_logger(trace_id)

        message_results = []
        messages_sent = state.get("messages_sent_today", 0)
        daily_limit = state.get("daily_message_limit", self.config.outreach.daily_message_limit)

        try:
            mcp_client = LinkedInMCPClientSync()
            template = state["message_template"]
            static_vars = state.get("template_variables", {})

            for employee in state["employees_found"]:
                if messages_sent >= daily_limit:
                    agent_logger.info(f"Daily message limit reached ({daily_limit})")
                    break

                # Render template with employee-specific variables
                variables = {
                    **static_vars,
                    "employee_name": employee.get("name", ""),
                    "company_name": employee.get("company_name", ""),
                    "employee_title": employee.get("title", ""),
                }
                message_text = render_template(template, variables)

                try:
                    agent_logger.info(
                        f"Sending message to {employee.get('name', '')} at {employee.get('company_name', '')}",
                    )

                    result = mcp_client.send_message(
                        employee_profile_url=employee["profile_url"],
                        employee_name=employee.get("name", ""),
                        message=message_text,
                        email=state["user_credentials"]["email"],
                        password=state["user_credentials"]["password"],
                        trace_id=trace_id,
                    )

                    message_results.append(result)
                    if result.get("sent"):
                        messages_sent += 1

                except Exception as e:
                    error_msg = f"Failed to send message to {employee.get('name', '')}: {str(e)}"
                    agent_logger.error(error_msg)
                    message_results.append({
                        "employee_profile_url": employee.get("profile_url", ""),
                        "employee_name": employee.get("name", ""),
                        "sent": False,
                        "method": "",
                        "error": str(e),
                    })

            successful = sum(1 for r in message_results if r.get("sent"))

            return {
                **state,
                "message_results": message_results,
                "messages_sent_today": messages_sent,
                "current_status": f"Sent {successful}/{len(message_results)} messages",
            }

        except Exception as e:
            error_msg = f"Message sending failed: {str(e)}"
            return {
                **state,
                "errors": state.get("errors", []) + [error_msg],
                "current_status": "Message sending failed",
            }

    def run(
        self,
        companies: List[Dict[str, str]],
        message_template: str,
        template_variables: Dict[str, str],
        user_credentials: Dict[str, str],
    ) -> OutreachAgentState:
        """Execute the outreach workflow.

        Args:
            companies: List of filtered company dicts from CSV
            message_template: Message template with {placeholders}
            template_variables: Static template variables (my_name, my_role, etc.)
            user_credentials: LinkedIn credentials {email, password}

        Returns:
            Final agent state with all results
        """
        trace_id = str(uuid.uuid4())

        from src.core.utils.logging_config import configure_core_agent_logging
        configure_core_agent_logging(default_trace_id=trace_id)

        agent_logger = get_core_agent_logger(trace_id)
        agent_logger.info(
            "Starting outreach agent",
            companies_count=len(companies),
        )

        initial_state = OutreachAgentState(
            companies=companies,
            company_filters={},
            message_template=message_template,
            template_variables=template_variables,
            user_credentials=user_credentials,
            employees_found=[],
            message_results=[],
            errors=[],
            current_status="Starting outreach workflow",
            trace_id=trace_id,
            daily_message_limit=self.config.outreach.daily_message_limit,
            messages_sent_today=0,
        )

        final_state = self.graph.invoke(initial_state)

        agent_logger.info(
            "Outreach agent completed",
            employees_found=len(final_state.get("employees_found", [])),
            messages_sent=final_state.get("messages_sent_today", 0),
        )

        return final_state
