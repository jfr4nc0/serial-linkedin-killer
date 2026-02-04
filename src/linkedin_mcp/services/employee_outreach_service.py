"""Service for orchestrating employee search and message sending on LinkedIn."""

import random
import time
from typing import Dict, List

from loguru import logger

from src.config.config_loader import load_config
from src.config.trace_context import set_trace_id
from src.linkedin_mcp.graphs.employee_search_graph import EmployeeSearchGraph
from src.linkedin_mcp.graphs.message_send_graph import MessageSendGraph
from src.linkedin_mcp.interfaces.services import IEmployeeOutreachService
from src.linkedin_mcp.model.outreach_types import (
    BatchEmployeeSearchResult,
    CompanySearchRequest,
    EmployeeResult,
    MessageResult,
)
from src.linkedin_mcp.services.browser_manager_service import (
    BrowserManagerService as BrowserManager,
)
from src.linkedin_mcp.services.linkedin_auth_service import LinkedInAuthService


class EmployeeOutreachService(IEmployeeOutreachService):
    """Orchestrates authentication, employee search, and message sending."""

    def __init__(self, config_path: str = None, session_factory=None):
        self.config = load_config(config_path)
        self._session_factory = session_factory
        self.browser_manager = BrowserManager(
            headless=self.config.browser.headless,
            use_undetected=self.config.browser.use_undetected,
            browser_type=self.config.browser.browser_type,
            chrome_version=self.config.browser.chrome_version,
            chrome_binary_path=self.config.browser.chrome_binary_path,
        )
        self.employee_search_graph = EmployeeSearchGraph(
            browser_manager=self.browser_manager
        )
        self.message_send_graph = MessageSendGraph(browser_manager=self.browser_manager)
        self.auth_service = LinkedInAuthService()

    def _ensure_authenticated(self, user_credentials: Dict[str, str]) -> None:
        """Start browser and authenticate if needed."""
        self.browser_manager.start_browser()

        auth_result = self.auth_service.authenticate(
            user_credentials["email"],
            user_credentials["password"],
            self.browser_manager,
        )

        if not auth_result["authenticated"]:
            raise Exception(
                f"Authentication failed: {auth_result.get('error', 'Unknown error')}"
            )

    def search_employees(
        self,
        company_linkedin_url: str,
        company_name: str,
        limit: int,
        user_credentials: Dict[str, str],
    ) -> List[EmployeeResult]:
        """Search for employees at a company on LinkedIn."""
        try:
            self._ensure_authenticated(user_credentials)

            return self.employee_search_graph.execute(
                company_linkedin_url,
                company_name,
                limit,
                self.browser_manager,
            )

        except Exception as e:
            raise Exception(f"Employee search failed: {str(e)}")

        finally:
            if self.browser_manager:
                self.browser_manager.close_browser()

    def search_employees_batch(
        self,
        companies: List[CompanySearchRequest],
        user_credentials: Dict[str, str],
        total_limit: int = None,
        exclude_companies: List[str] = None,
        exclude_profile_urls: List[str] = None,
        batch_id: str = None,
        trace_id: str = None,
    ) -> dict:
        """Search employees across multiple companies with a SINGLE browser session.

        Args:
            companies: List of company search requests
            user_credentials: LinkedIn credentials
            total_limit: Optional max total employees across all companies.
                         When set, stops searching once this many employees are collected.
            trace_id: Trace ID for distributed tracing (propagated from caller).
        """
        # Set trace context for this request (auto-propagates to all logs)
        if trace_id:
            set_trace_id(trace_id)

        exclude_companies_set = set(exclude_companies or [])
        exclude_urls_set = set(exclude_profile_urls or [])
        try:
            self._ensure_authenticated(user_credentials)

            results = []
            total_collected = 0
            for i, company in enumerate(companies):
                # Skip excluded companies
                if company["company_linkedin_url"] in exclude_companies_set:
                    logger.info(f"Skipping excluded company: {company['company_name']}")
                    continue
                # Check total limit before searching next company
                if total_limit is not None and total_collected >= total_limit:
                    logger.info(
                        f"Total limit reached ({total_collected}/{total_limit}), "
                        f"skipping remaining {len(companies) - i} companies"
                    )
                    break

                # Adjust per-company limit if total_limit would be exceeded
                company_limit = company["limit"]
                if total_limit is not None:
                    company_limit = min(company_limit, total_limit - total_collected)

                logger.info(
                    f"Searching company {i + 1}/{len(companies)}: {company['company_name']} "
                    f"(limit: {company_limit})"
                )
                try:
                    employees = self.employee_search_graph.execute(
                        company["company_linkedin_url"],
                        company["company_name"],
                        company_limit,
                        self.browser_manager,
                    )
                    # Filter out already-messaged employees
                    if exclude_urls_set:
                        before = len(employees)
                        employees = [
                            e
                            for e in employees
                            if e.get("profile_url", "") not in exclude_urls_set
                        ]
                        if before != len(employees):
                            logger.info(
                                f"Filtered {before - len(employees)} already-messaged employees from {company['company_name']}"
                            )
                    total_collected += len(employees)
                    # Write to shared DB if session_factory available
                    if self._session_factory and batch_id and employees:
                        from src.core.db.models import SearchResult

                        with self._session_factory() as db_session:
                            for emp in employees:
                                db_session.add(
                                    SearchResult(
                                        batch_id=batch_id,
                                        company_name=company["company_name"],
                                        company_linkedin_url=company[
                                            "company_linkedin_url"
                                        ],
                                        employee_name=emp.get("name", ""),
                                        employee_title=emp.get("title", ""),
                                        employee_profile_url=emp.get("profile_url", ""),
                                        created_at=time.time(),
                                    )
                                )
                            db_session.commit()
                    results.append(
                        BatchEmployeeSearchResult(
                            company_name=company["company_name"],
                            company_linkedin_url=company["company_linkedin_url"],
                            employees=employees,
                            errors=[],
                        )
                    )
                except Exception as e:
                    logger.error(f"Failed to search {company['company_name']}: {e}")
                    results.append(
                        BatchEmployeeSearchResult(
                            company_name=company["company_name"],
                            company_linkedin_url=company["company_linkedin_url"],
                            employees=[],
                            errors=[str(e)],
                        )
                    )

                # Brief delay between companies for anti-detection
                if i < len(companies) - 1:
                    delay = random.uniform(0.5, 1)
                    time.sleep(delay)

            return {
                "batch_id": batch_id or "",
                "total_employees": total_collected,
                "companies_processed": len(results),
            }

        except Exception as e:
            raise Exception(f"Batch employee search failed: {str(e)}")

        finally:
            if self.browser_manager:
                self.browser_manager.close_browser()

    # Bounded thread pool for background searches (max 2 concurrent browser sessions)
    _search_executor = None
    _search_executor_lock = __import__("threading").Lock()

    @classmethod
    def _get_search_executor(cls):
        if cls._search_executor is None:
            with cls._search_executor_lock:
                if cls._search_executor is None:
                    from concurrent.futures import ThreadPoolExecutor

                    cls._search_executor = ThreadPoolExecutor(
                        max_workers=2, thread_name_prefix="mcp-search"
                    )
        return cls._search_executor

    def submit_search_batch(
        self,
        companies: List[CompanySearchRequest],
        user_credentials: Dict[str, str],
        batch_id: str,
        trace_id: str = "",
        total_limit: int = None,
        exclude_companies: List[str] = None,
        exclude_profile_urls: List[str] = None,
    ) -> dict:
        """Return batch_id immediately, run search in bounded thread pool.

        When done, publishes MCPSearchComplete to Kafka.
        """
        from src.core.queue.config import TOPIC_MCP_SEARCH_COMPLETE
        from src.core.queue.producer import KafkaResultProducer
        from src.core.queue.schemas import MCPSearchComplete

        # Set trace context for this request
        if trace_id:
            set_trace_id(trace_id)

        def _run():
            # Re-set trace context in background thread (contextvars are thread-local)
            if trace_id:
                set_trace_id(trace_id)

            try:
                summary = self.search_employees_batch(
                    companies,
                    user_credentials,
                    total_limit=total_limit,
                    exclude_companies=exclude_companies,
                    exclude_profile_urls=exclude_profile_urls,
                    batch_id=batch_id,
                    trace_id=trace_id,
                )
                complete = MCPSearchComplete(
                    batch_id=batch_id,
                    status="completed",
                    total_employees=summary["total_employees"],
                    companies_processed=summary["companies_processed"],
                    trace_id=trace_id,
                )
            except Exception as e:
                logger.error(f"Background search failed: {e}")
                complete = MCPSearchComplete(
                    batch_id=batch_id,
                    status="failed",
                    total_employees=0,
                    companies_processed=0,
                    error=str(e),
                    trace_id=trace_id,
                )
            producer = KafkaResultProducer()
            producer.publish(TOPIC_MCP_SEARCH_COMPLETE, batch_id, complete)
            producer.flush()
            logger.info(
                f"Published MCPSearchComplete for batch {batch_id}: {complete.status}"
            )

        self._get_search_executor().submit(_run)
        logger.info(f"Submitted batch search {batch_id} to thread pool")
        return {"batch_id": batch_id}

    def send_message(
        self,
        employee_profile_url: str,
        employee_name: str,
        message: str,
        user_credentials: Dict[str, str],
    ) -> MessageResult:
        """Send a message or connection request to an employee."""
        try:
            self._ensure_authenticated(user_credentials)

            result = self.message_send_graph.execute(
                employee_profile_url,
                employee_name,
                message,
                self.browser_manager,
            )

            # Random delay between messages for anti-detection
            delay = random.uniform(
                self.config.outreach.delay_between_messages_min,
                self.config.outreach.delay_between_messages_max,
            )
            time.sleep(delay)

            return result

        except Exception as e:
            return MessageResult(
                employee_profile_url=employee_profile_url,
                employee_name=employee_name,
                sent=False,
                method="",
                error=str(e),
            )

        finally:
            if self.browser_manager:
                self.browser_manager.close_browser()
