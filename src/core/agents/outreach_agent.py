"""LangGraph agent for employee outreach workflow."""

import uuid
from typing import Any, Dict, List, Optional

from langgraph.graph import END, StateGraph
from loguru import logger

from src.config.config_loader import load_config
from src.core.model.outreach_state import OutreachAgentState
from src.core.providers.linkedin_mcp_client_sync import LinkedInMCPClientSync
from src.core.tools.message_template import render_template
from src.core.utils.logging_config import get_core_agent_logger


class EmployeeOutreachAgent:
    """
    LangGraph agent that orchestrates the employee outreach workflow.

    Supports two execution modes:
    - Full workflow (legacy): search → send with single template
    - Two-phase workflow:
      - Phase 1: search employees only (run_search_only)
      - Phase 2: send messages with per-employee templates (run_send)
    """

    def __init__(self, config_path: str = None):
        self.config = load_config(config_path)
        self._full_graph = self._build_full_graph()
        self._search_graph = self._build_search_graph()
        self._send_graph = self._build_send_graph()

    def _build_full_graph(self) -> StateGraph:
        """Build the legacy full workflow graph."""
        workflow = StateGraph(OutreachAgentState)

        workflow.add_node("search_employees_node", self.search_employees_node)
        workflow.add_node("send_messages_node", self.send_messages_node)

        workflow.set_entry_point("search_employees_node")
        workflow.add_edge("search_employees_node", "send_messages_node")
        workflow.add_edge("send_messages_node", END)

        return workflow.compile()

    def _build_search_graph(self) -> StateGraph:
        """Build the Phase 1 search-only graph."""
        workflow = StateGraph(OutreachAgentState)

        workflow.add_node("search_employees_node", self.search_employees_node)

        workflow.set_entry_point("search_employees_node")
        workflow.add_edge("search_employees_node", END)

        return workflow.compile()

    def _build_send_graph(self) -> StateGraph:
        """Build the Phase 2 send-only graph."""
        workflow = StateGraph(OutreachAgentState)

        workflow.add_node("send_messages_node", self.send_messages_with_templates_node)

        workflow.set_entry_point("send_messages_node")
        workflow.add_edge("send_messages_node", END)

        return workflow.compile()

    def search_employees_node(self, state: OutreachAgentState) -> Dict[str, Any]:
        """Search for employees at all filtered companies via single batch MCP call."""
        trace_id = state.get("trace_id", str(uuid.uuid4()))
        agent_logger = get_core_agent_logger(trace_id)

        all_employees = []
        mcp_client = None

        try:
            mcp_client = LinkedInMCPClientSync()
            employees_per_company = self.config.outreach.employees_per_company

            # Build batch request
            companies_to_search = []
            for company in state["companies"]:
                linkedin_url = company.get("linkedin_url", "")
                company_name = company.get("name", "Unknown")
                if not linkedin_url:
                    agent_logger.warning(f"Skipping {company_name}: no linkedin_url")
                    continue
                companies_to_search.append(
                    {
                        "company_linkedin_url": linkedin_url,
                        "company_name": company_name,
                        "limit": employees_per_company,
                    }
                )

            if not companies_to_search:
                return {
                    "employees_found": [],
                    "current_status": "No companies with LinkedIn URLs to search",
                }

            agent_logger.info(
                f"Batch searching employees at {len(companies_to_search)} companies",
            )

            # Single MCP call for all companies (single browser session)
            batch_results = mcp_client.search_employees_batch(
                companies=companies_to_search,
                email=state["user_credentials"]["email"],
                password=state["user_credentials"]["password"],
                total_limit=state.get("total_limit"),
                trace_id=trace_id,
            )

            # Flatten results
            for result in batch_results:
                company_name = result.get("company_name", "Unknown")
                for emp in result.get("employees", []):
                    emp["company_name"] = company_name
                all_employees.extend(result.get("employees", []))

                for error in result.get("errors", []):
                    state["errors"] = state.get("errors", []) + [
                        f"{company_name}: {error}"
                    ]

            return {
                "employees_found": all_employees,
                "current_status": f"Found {len(all_employees)} employees across {len(companies_to_search)} companies",
            }

        except Exception as e:
            error_msg = f"Batch employee search failed: {str(e)}"
            return {
                "errors": state.get("errors", []) + [error_msg],
                "current_status": "Employee search failed",
            }
        finally:
            del mcp_client

    def send_messages_node(self, state: OutreachAgentState) -> Dict[str, Any]:
        """Send messages to all found employees via MCP (legacy single-template mode)."""
        trace_id = state.get("trace_id", str(uuid.uuid4()))
        agent_logger = get_core_agent_logger(trace_id)

        message_results = []
        messages_sent = state.get("messages_sent_today", 0)
        daily_limit = state.get(
            "daily_message_limit", self.config.outreach.daily_message_limit
        )

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
                    message_results.append(
                        {
                            "employee_profile_url": employee.get("profile_url", ""),
                            "employee_name": employee.get("name", ""),
                            "sent": False,
                            "method": "",
                            "error": str(e),
                        }
                    )

            successful = sum(1 for r in message_results if r.get("sent"))

            return {
                "message_results": message_results,
                "messages_sent_today": messages_sent,
                "current_status": f"Sent {successful}/{len(message_results)} messages",
            }

        except Exception as e:
            error_msg = f"Message sending failed: {str(e)}"
            return {
                "errors": state.get("errors", []) + [error_msg],
                "current_status": "Message sending failed",
            }

    def send_messages_with_templates_node(
        self, state: OutreachAgentState
    ) -> Dict[str, Any]:
        """Send messages using per-employee templates (Phase 2 mode).

        Each employee in employees_found has:
        - _template: message template for this employee's role group
        - _template_vars: static variables for this template
        - _role: role category for result grouping
        """
        trace_id = state.get("trace_id", str(uuid.uuid4()))
        agent_logger = get_core_agent_logger(trace_id)

        message_results = []
        messages_sent = state.get("messages_sent_today", 0)
        daily_limit = state.get(
            "daily_message_limit", self.config.outreach.daily_message_limit
        )

        try:
            mcp_client = LinkedInMCPClientSync()

            for employee in state["employees_found"]:
                if messages_sent >= daily_limit:
                    agent_logger.info(f"Daily message limit reached ({daily_limit})")
                    break

                # Get per-employee template
                template = employee.get("_template", "")
                static_vars = employee.get("_template_vars", {})
                role = employee.get("_role", "Other")

                if not template:
                    agent_logger.warning(
                        f"No template for employee {employee.get('name', '')}"
                    )
                    continue

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
                        f"Sending message to {employee.get('name', '')} ({role}) at {employee.get('company_name', '')}",
                    )

                    result = mcp_client.send_message(
                        employee_profile_url=employee["profile_url"],
                        employee_name=employee.get("name", ""),
                        message=message_text,
                        email=state["user_credentials"]["email"],
                        password=state["user_credentials"]["password"],
                        trace_id=trace_id,
                    )

                    # Include role in result for grouping
                    result["_role"] = role
                    message_results.append(result)

                    if result.get("sent"):
                        messages_sent += 1

                except Exception as e:
                    error_msg = f"Failed to send message to {employee.get('name', '')}: {str(e)}"
                    agent_logger.error(error_msg)
                    message_results.append(
                        {
                            "employee_profile_url": employee.get("profile_url", ""),
                            "employee_name": employee.get("name", ""),
                            "sent": False,
                            "method": "",
                            "error": str(e),
                            "_role": role,
                        }
                    )

            successful = sum(1 for r in message_results if r.get("sent"))

            return {
                "message_results": message_results,
                "messages_sent_today": messages_sent,
                "current_status": f"Sent {successful}/{len(message_results)} messages",
            }

        except Exception as e:
            error_msg = f"Message sending failed: {str(e)}"
            return {
                "errors": state.get("errors", []) + [error_msg],
                "current_status": "Message sending failed",
            }

    # === Phase 1: Search Only ===

    def run_search_only(
        self,
        companies: List[Dict[str, str]],
        user_credentials: Dict[str, str],
        total_limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Execute Phase 1: search employees only.

        Args:
            companies: List of filtered company dicts from DB
            user_credentials: LinkedIn credentials {email, password}

        Returns:
            List of employee dicts found
        """
        trace_id = str(uuid.uuid4())

        agent_logger = get_core_agent_logger(trace_id)
        agent_logger.info(
            "Starting search-only phase",
            companies_count=len(companies),
        )

        if total_limit is not None:
            agent_logger.info(f"Total employee limit: {total_limit}")

        initial_state = OutreachAgentState(
            companies=companies,
            company_filters={},
            message_template="",
            template_variables={},
            user_credentials=user_credentials,
            employees_found=[],
            message_results=[],
            errors=[],
            current_status="Starting employee search",
            trace_id=trace_id,
            daily_message_limit=0,
            messages_sent_today=0,
            total_limit=total_limit,
        )

        final_state = self._search_graph.invoke(initial_state)

        agent_logger.info(
            "Search phase completed",
            employees_found=len(final_state.get("employees_found", [])),
        )

        return final_state.get("employees_found", [])

    # === Phase 2: Send Only ===

    def run_send(
        self,
        employees_with_templates: List[Dict[str, Any]],
        user_credentials: Dict[str, str],
        daily_limit: int,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute Phase 2: send messages with per-employee templates.

        Args:
            employees_with_templates: Employees with _template, _template_vars, _role fields
            user_credentials: LinkedIn credentials {email, password}
            daily_limit: Maximum messages to send
            trace_id: Optional trace ID for logging correlation

        Returns:
            Final agent state with message_results
        """
        trace_id = trace_id or str(uuid.uuid4())

        agent_logger = get_core_agent_logger(trace_id)
        agent_logger.info(
            "Starting send phase",
            employees_count=len(employees_with_templates),
            daily_limit=daily_limit,
        )

        initial_state = OutreachAgentState(
            companies=[],
            company_filters={},
            message_template="",
            template_variables={},
            user_credentials=user_credentials,
            employees_found=employees_with_templates,
            message_results=[],
            errors=[],
            current_status="Starting message sending",
            trace_id=trace_id,
            daily_message_limit=daily_limit,
            messages_sent_today=0,
            total_limit=None,
        )

        final_state = self._send_graph.invoke(initial_state)

        agent_logger.info(
            "Send phase completed",
            messages_sent=final_state.get("messages_sent_today", 0),
        )

        return final_state

    # === Legacy Full Workflow ===

    def run(
        self,
        companies: List[Dict[str, str]],
        message_template: str,
        template_variables: Dict[str, str],
        user_credentials: Dict[str, str],
    ) -> OutreachAgentState:
        """Execute the legacy full outreach workflow (search + send single template).

        Args:
            companies: List of filtered company dicts from DB
            message_template: Message template with {placeholders}
            template_variables: Static template variables (my_name, my_role, etc.)
            user_credentials: LinkedIn credentials {email, password}

        Returns:
            Final agent state with all results
        """
        trace_id = str(uuid.uuid4())

        agent_logger = get_core_agent_logger(trace_id)
        agent_logger.info(
            "Starting outreach agent (full workflow)",
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
            total_limit=None,
        )

        final_state = self._full_graph.invoke(initial_state)

        agent_logger.info(
            "Outreach agent completed",
            employees_found=len(final_state.get("employees_found", [])),
            messages_sent=final_state.get("messages_sent_today", 0),
        )

        return final_state
