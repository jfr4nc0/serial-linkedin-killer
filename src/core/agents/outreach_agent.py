"""LangGraph agent for employee outreach workflow."""

import uuid
from typing import Any, Dict, List, Optional

from langgraph.graph import END, StateGraph
from loguru import logger

from src.config.config_loader import load_config
from src.config.trace_context import get_trace_id
from src.core.agents.tools.message_template import render_template
from src.core.db.agent_db import AgentDB
from src.core.model.outreach_state import OutreachAgentState
from src.core.providers.linkedin_mcp_client_sync import LinkedInMCPClientSync
from src.core.queue.config import TOPIC_MCP_SEARCH_COMPLETE
from src.core.queue.consumer import KafkaResultConsumer
from src.core.queue.schemas import MCPSearchComplete


class EmployeeOutreachAgent:
    """
    LangGraph agent that orchestrates the employee outreach workflow.

    Supports two execution modes:
    - Full workflow (legacy): search → send with single template
    - Two-phase workflow:
      - Phase 1: search employees only (run_search_only)
      - Phase 2: send messages with per-employee templates (run_send)
    """

    def __init__(self, config_path: str = None, agent_db: AgentDB = None):
        self.config = load_config(config_path)
        self._db = agent_db or AgentDB(self.config.db.url)
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
        # Use trace_id from context (set by outreach_service)
        trace_id = get_trace_id()

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
                    logger.warning(f"Skipping {company_name}: no linkedin_url")
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

            # Build exclusion list: merge DB-based + user-provided exclusions
            messaged_urls = list(self._db.get_messaged_profile_urls())
            user_exclude_urls = state.get("exclude_profile_urls") or []
            all_exclude_urls = list(set(messaged_urls + user_exclude_urls))
            if all_exclude_urls:
                logger.info(
                    f"Excluding {len(all_exclude_urls)} profile URLs "
                    f"({len(messaged_urls)} already-messaged, {len(user_exclude_urls)} user-provided)",
                )

            exclude_companies = state.get("exclude_companies")
            if exclude_companies:
                logger.info(
                    f"Excluding {len(exclude_companies)} company URLs",
                )

            batch_id = str(uuid.uuid4())
            logger.info(
                f"Batch searching employees at {len(companies_to_search)} companies (batch_id={batch_id})",
            )

            # MCP call returns immediately with batch_id; search runs in background
            mcp_client.search_employees_batch(
                companies=companies_to_search,
                email=state["user_credentials"]["email"],
                password=state["user_credentials"]["password"],
                total_limit=state.get("total_limit"),
                trace_id=trace_id,
                exclude_profile_urls=all_exclude_urls if all_exclude_urls else None,
                exclude_companies=exclude_companies,
                batch_id=batch_id,
            )

            logger.info(
                f"MCP accepted batch {batch_id}, waiting for completion via Kafka...",
            )

            # Wait for MCP to publish completion event via Kafka
            consumer = KafkaResultConsumer()
            completion = consumer.consume(
                TOPIC_MCP_SEARCH_COMPLETE, batch_id, MCPSearchComplete, timeout=3600.0
            )

            if completion is None:
                raise Exception(
                    f"Timed out waiting for batch {batch_id} search completion"
                )
            if completion.status == "failed":
                raise Exception(f"MCP search failed: {completion.error}")

            logger.info(
                f"MCP search complete: {completion.total_employees} employees across "
                f"{completion.companies_processed} companies. Reading from DB...",
            )

            # Read actual employee data from shared DB
            db_results = self._db.get_search_results(batch_id)
            for emp in db_results:
                emp["company_name"] = emp.get("company_name", "Unknown")
                # Keep company_linkedin_url for tracking contacted companies
                all_employees.append(emp)

            # Cleanup search results from DB
            self._db.delete_search_results(batch_id)
            logger.info(
                f"Loaded {len(all_employees)} employees from DB, batch cleaned up",
            )

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

    def send_messages_node(self, state: OutreachAgentState) -> Dict[str, Any]:
        """Send messages to all found employees via MCP (legacy single-template mode).

        Pre-filters employees (quota, already-messaged), renders templates,
        then sends the entire batch via a single MCP call (one browser session).
        """
        trace_id = get_trace_id()

        messages_sent = self._db.get_daily_quota()
        daily_limit = state.get(
            "daily_message_limit", self.config.outreach.daily_message_limit
        )

        template = state["message_template"]
        static_vars = state.get("template_variables", {})

        # Batch load all messaged URLs once (fixes N+1 query)
        messaged_urls = self._db.get_messaged_profile_urls()

        # === Phase A: Pre-filter and render messages ===
        messages_to_send = []
        message_metadata = []

        for employee in state["employees_found"]:
            if messages_sent + len(messages_to_send) >= daily_limit:
                logger.info(f"Daily message limit reached ({daily_limit})")
                break

            profile_url = employee.get("profile_url", "")
            if profile_url in messaged_urls:
                logger.info(f"Skipping {employee.get('name', '')}: already messaged")
                continue

            # Render template with employee-specific variables
            variables = {
                **static_vars,
                "employee_name": employee.get("name", ""),
                "company_name": employee.get("company_name", ""),
                "employee_title": employee.get("title", ""),
            }
            message_text = render_template(template, variables)
            subject = static_vars.get("topic", "")

            messages_to_send.append(
                {
                    "profile_url": profile_url,
                    "name": employee.get("name", ""),
                    "message": message_text,
                    "subject": subject,
                }
            )
            message_metadata.append(
                {
                    "profile_url": profile_url,
                    "name": employee.get("name", ""),
                    "company_name": employee.get("company_name", ""),
                    "company_linkedin_url": employee.get("company_linkedin_url", ""),
                }
            )

        if not messages_to_send:
            logger.info("No messages to send after filtering")
            return {
                "message_results": [],
                "messages_sent_today": messages_sent,
                "current_status": "No messages to send",
            }

        logger.info(f"Sending batch of {len(messages_to_send)} messages")

        # === Phase B: Batch send via single MCP call (one browser) ===
        try:
            mcp_client = LinkedInMCPClientSync()
            batch_results = mcp_client.send_messages_batch(
                messages=messages_to_send,
                email=state["user_credentials"]["email"],
                password=state["user_credentials"]["password"],
                trace_id=trace_id,
            )
        except Exception as e:
            error_msg = f"Batch message sending failed: {str(e)}"
            logger.error(error_msg)
            return {
                "errors": state.get("errors", []) + [error_msg],
                "current_status": "Message sending failed",
            }

        # === Phase C: Process results ===
        message_results = []
        for i, result in enumerate(batch_results):
            meta = message_metadata[i] if i < len(message_metadata) else {}

            if not isinstance(result, dict):
                result = dict(result)

            message_results.append(result)

            sent = result.get("sent", False)
            self._db.record_message(
                meta.get("profile_url", ""),
                meta.get("name", ""),
                sent,
                result.get("method", ""),
                result.get("error"),
                company_name=meta.get("company_name"),
                company_linkedin_url=meta.get("company_linkedin_url"),
            )
            if sent:
                messages_sent = self._db.increment_daily_quota()

        successful = sum(1 for r in message_results if r.get("sent"))

        return {
            "message_results": message_results,
            "messages_sent_today": messages_sent,
            "current_status": f"Sent {successful}/{len(message_results)} messages",
        }

    def send_messages_with_templates_node(
        self, state: OutreachAgentState
    ) -> Dict[str, Any]:
        """Send messages using per-employee templates (Phase 2 mode).

        Pre-filters employees (quota, per-company limits, already-messaged),
        then sends the entire batch via a single MCP call (one browser session).
        """
        trace_id = get_trace_id()

        messages_sent = self._db.get_daily_quota()
        daily_limit = state.get(
            "daily_message_limit", self.config.outreach.daily_message_limit
        )
        max_per_company = state.get("max_per_company")
        company_message_count: Dict[str, int] = {}

        # Batch load all messaged URLs once (fixes N+1 query)
        messaged_urls = self._db.get_messaged_profile_urls()

        # === Phase A: Pre-filter and render messages ===
        messages_to_send = []
        # Track metadata per message for post-processing
        message_metadata = []

        for employee in state["employees_found"]:
            if messages_sent + len(messages_to_send) >= daily_limit:
                logger.info(f"Daily message limit reached ({daily_limit})")
                break

            profile_url = employee.get("profile_url", "")
            if profile_url in messaged_urls:
                logger.info(f"Skipping {employee.get('name', '')}: already messaged")
                continue

            company_name = employee.get("company_name", "Unknown")
            if max_per_company:
                current_count = company_message_count.get(company_name, 0)
                if current_count >= max_per_company:
                    logger.info(
                        f"Skipping {employee.get('name', '')}: company limit reached "
                        f"({current_count}/{max_per_company} for {company_name})"
                    )
                    continue

            template = employee.get("_template", "")
            static_vars = employee.get("_template_vars", {})
            role = employee.get("_role", "Other")

            if not template:
                logger.warning(f"No template for employee {employee.get('name', '')}")
                continue

            variables = {
                **static_vars,
                "employee_name": employee.get("name", ""),
                "company_name": employee.get("company_name", ""),
                "employee_title": employee.get("title", ""),
            }
            message_text = render_template(template, variables)
            subject = static_vars.get("topic", "")

            messages_to_send.append(
                {
                    "profile_url": profile_url,
                    "name": employee.get("name", ""),
                    "message": message_text,
                    "subject": subject,
                }
            )
            message_metadata.append(
                {
                    "profile_url": profile_url,
                    "name": employee.get("name", ""),
                    "company_name": company_name,
                    "company_linkedin_url": employee.get("company_linkedin_url", ""),
                    "role": role,
                }
            )

            # Pre-count per-company for filtering
            company_message_count[company_name] = (
                company_message_count.get(company_name, 0) + 1
            )

        if not messages_to_send:
            logger.info("No messages to send after filtering")
            return {
                "message_results": [],
                "messages_sent_today": messages_sent,
                "current_status": "No messages to send",
            }

        logger.info(f"Sending batch of {len(messages_to_send)} messages")

        # === Phase B: Batch send via single MCP call (one browser) ===
        try:
            mcp_client = LinkedInMCPClientSync()
            batch_results = mcp_client.send_messages_batch(
                messages=messages_to_send,
                email=state["user_credentials"]["email"],
                password=state["user_credentials"]["password"],
                trace_id=trace_id,
            )
        except Exception as e:
            error_msg = f"Batch message sending failed: {str(e)}"
            logger.error(error_msg)
            return {
                "errors": state.get("errors", []) + [error_msg],
                "current_status": "Message sending failed",
            }

        # === Phase C: Process results ===
        message_results = []
        for i, result in enumerate(batch_results):
            meta = message_metadata[i] if i < len(message_metadata) else {}
            role = meta.get("role", "Other")

            # Ensure result is a dict
            if not isinstance(result, dict):
                result = dict(result)

            result["_role"] = role
            message_results.append(result)

            sent = result.get("sent", False)
            self._db.record_message(
                meta.get("profile_url", ""),
                meta.get("name", ""),
                sent,
                result.get("method", ""),
                result.get("error"),
                company_name=meta.get("company_name"),
                company_linkedin_url=meta.get("company_linkedin_url"),
            )
            if sent:
                messages_sent = self._db.increment_daily_quota()

        successful = sum(1 for r in message_results if r.get("sent"))

        return {
            "message_results": message_results,
            "messages_sent_today": messages_sent,
            "current_status": f"Sent {successful}/{len(message_results)} messages",
        }

    # === Phase 1: Search Only ===

    def run_search_only(
        self,
        companies: List[Dict[str, str]],
        user_credentials: Dict[str, str],
        total_limit: Optional[int] = None,
        exclude_companies: Optional[List[str]] = None,
        exclude_profile_urls: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Execute Phase 1: search employees only.

        Args:
            companies: List of filtered company dicts from DB
            user_credentials: LinkedIn credentials {email, password}
            total_limit: Max total employees across all companies
            exclude_companies: LinkedIn URLs of companies to skip
            exclude_profile_urls: LinkedIn URLs of people to skip

        Returns:
            List of employee dicts found
        """
        # Use trace_id from context (set by outreach_service)
        trace_id = get_trace_id()

        logger.info(
            "Starting search-only phase",
            companies_count=len(companies),
        )

        if total_limit is not None:
            logger.info(f"Total employee limit: {total_limit}")

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
            exclude_companies=exclude_companies,
            exclude_profile_urls=exclude_profile_urls,
        )

        final_state = self._search_graph.invoke(initial_state)

        logger.info(
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
        max_per_company: Optional[int] = None,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute Phase 2: send messages with per-employee templates.

        Args:
            employees_with_templates: Employees with _template, _template_vars, _role fields
            user_credentials: LinkedIn credentials {email, password}
            daily_limit: Maximum messages to send
            max_per_company: Maximum messages per company (anti-spam)
            trace_id: Deprecated - trace_id is now read from context

        Returns:
            Final agent state with message_results
        """
        # Use trace_id from context (set by outreach_service)
        trace_id = get_trace_id()

        logger.info(
            "Starting send phase",
            employees_count=len(employees_with_templates),
            daily_limit=daily_limit,
            max_per_company=max_per_company,
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
            max_per_company=max_per_company,
            exclude_companies=None,
            exclude_profile_urls=None,
        )

        final_state = self._send_graph.invoke(initial_state)

        logger.info(
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
        from src.config.trace_context import set_trace_id

        # For legacy full workflow, generate trace_id if not already set
        trace_id = get_trace_id()
        if trace_id == "no-trace":
            trace_id = set_trace_id()

        logger.info(
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
            exclude_companies=None,
            exclude_profile_urls=None,
        )

        final_state = self._full_graph.invoke(initial_state)

        logger.info(
            "Outreach agent completed",
            employees_found=len(final_state.get("employees_found", [])),
            messages_sent=final_state.get("messages_sent_today", 0),
        )

        return final_state
