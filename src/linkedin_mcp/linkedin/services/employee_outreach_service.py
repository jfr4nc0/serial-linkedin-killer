"""Service for orchestrating employee search and message sending on LinkedIn."""

import random
import time
from typing import Dict, List

from src.config.config_loader import load_config
from src.linkedin_mcp.linkedin.graphs.employee_search_graph import EmployeeSearchGraph
from src.linkedin_mcp.linkedin.graphs.message_send_graph import MessageSendGraph
from src.linkedin_mcp.linkedin.interfaces.services import IEmployeeOutreachService
from src.linkedin_mcp.linkedin.model.outreach_types import EmployeeResult, MessageResult
from src.linkedin_mcp.linkedin.services.browser_manager_service import (
    BrowserManagerService as BrowserManager,
)
from src.linkedin_mcp.linkedin.services.linkedin_auth_service import LinkedInAuthService


class EmployeeOutreachService(IEmployeeOutreachService):
    """Orchestrates authentication, employee search, and message sending."""

    def __init__(self, config_path: str = None):
        self.config = load_config(config_path)
        self.browser_manager = BrowserManager()
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
