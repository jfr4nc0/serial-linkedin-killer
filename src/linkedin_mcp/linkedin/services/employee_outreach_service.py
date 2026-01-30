"""Service for orchestrating employee search and message sending on LinkedIn."""

import random
import time
from typing import Dict, List

from src.config.config_loader import load_config
from src.linkedin_mcp.linkedin.graphs.employee_search_graph import EmployeeSearchGraph
from src.linkedin_mcp.linkedin.graphs.message_send_graph import MessageSendGraph
from src.linkedin_mcp.linkedin.interfaces.services import IEmployeeOutreachService
from src.linkedin_mcp.linkedin.model.outreach_types import (
    BatchEmployeeSearchResult,
    CompanySearchRequest,
    EmployeeResult,
    MessageResult,
)
from src.linkedin_mcp.linkedin.utils.logging_config import get_mcp_logger
from src.linkedin_mcp.linkedin.services.browser_manager_service import (
    BrowserManagerService as BrowserManager,
)
from src.linkedin_mcp.linkedin.services.linkedin_auth_service import LinkedInAuthService


class EmployeeOutreachService(IEmployeeOutreachService):
    """Orchestrates authentication, employee search, and message sending."""

    def __init__(self, config_path: str = None):
        self.config = load_config(config_path)
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
    ) -> List[BatchEmployeeSearchResult]:
        """Search employees across multiple companies with a SINGLE browser session."""
        logger = get_mcp_logger()
        try:
            self._ensure_authenticated(user_credentials)

            results = []
            for i, company in enumerate(companies):
                logger.info(
                    f"Searching company {i + 1}/{len(companies)}: {company['company_name']}"
                )
                try:
                    employees = self.employee_search_graph.execute(
                        company["company_linkedin_url"],
                        company["company_name"],
                        company["limit"],
                        self.browser_manager,
                    )
                    results.append(
                        BatchEmployeeSearchResult(
                            company_name=company["company_name"],
                            company_linkedin_url=company["company_linkedin_url"],
                            employees=employees,
                            errors=[],
                        )
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to search {company['company_name']}: {e}"
                    )
                    results.append(
                        BatchEmployeeSearchResult(
                            company_name=company["company_name"],
                            company_linkedin_url=company["company_linkedin_url"],
                            employees=[],
                            errors=[str(e)],
                        )
                    )

                # Delay between companies for anti-detection
                if i < len(companies) - 1:
                    delay = random.uniform(2, 5)
                    logger.info(f"Waiting {delay:.1f}s before next company")
                    time.sleep(delay)

            return results

        except Exception as e:
            raise Exception(f"Batch employee search failed: {str(e)}")

        finally:
            if self.browser_manager:
                self.browser_manager.close_browser()

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
