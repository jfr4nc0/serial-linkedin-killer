from typing import Dict, List

from src.config.config_loader import load_config
from src.linkedin_mcp.linkedin.graphs.job_search_graph import JobSearchGraph
from src.linkedin_mcp.linkedin.interfaces.services import IJobSearchService
from src.linkedin_mcp.linkedin.model.types import JobResult
from src.linkedin_mcp.linkedin.services.browser_manager_service import (
    BrowserManagerService as BrowserManager,
)
from src.linkedin_mcp.linkedin.services.linkedin_auth_service import LinkedInAuthService


class JobSearchService(IJobSearchService):
    """Service responsible for orchestrating complete LinkedIn job search workflow."""

    def __init__(self, config_path: str = None):
        self.config = load_config(config_path)
        # Create concrete implementations with config
        self.browser_manager = BrowserManager(
            headless=self.config.browser.headless,
            use_undetected=self.config.browser.use_undetected,
            browser_type=self.config.browser.browser_type,
            chrome_version=self.config.browser.chrome_version,
            chrome_binary_path=self.config.browser.chrome_binary_path,
        )

        # Inject dependencies into the graph
        self.search_graph = JobSearchGraph(browser_manager=self.browser_manager)
        self.auth_service = LinkedInAuthService()

    def search_jobs(
        self,
        job_title: str,
        location: str,
        limit: int,
        user_credentials: Dict[str, str],
    ) -> List[JobResult]:
        """
        Search for jobs on LinkedIn - handles authentication and search workflow.

        Args:
            job_title: The job title to search for
            location: The location to search in
            limit: Maximum number of jobs to collect
            user_credentials: User authentication credentials (email, password)

        Returns:
            List of jobs with id_job and job_description
        """
        # Extract credentials
        email = user_credentials.get("email")
        password = user_credentials.get("password")

        if not email or not password:
            raise ValueError("Email and password are required in user_credentials")

        try:
            # Step 1: Initialize browser (use injected dependency)
            self.browser_manager.start_browser()

            # Step 2: Authenticate with LinkedIn
            auth_result = self.auth_service.authenticate(
                email, password, self.browser_manager
            )

            if not auth_result["authenticated"]:
                raise Exception(
                    f"Authentication failed: {auth_result.get('error', 'Unknown error')}"
                )

            # Step 3: Execute job search workflow
            raw_results = self.search_graph.execute(
                job_title,
                location,
                True,
                limit,
                self.browser_manager,  # Default to easy_apply=True
            )

            # Step 4: Return job results (already in JobResult format)
            return raw_results

        except Exception as e:
            # Log error or handle as needed
            raise Exception(f"Job search failed: {str(e)}")

        finally:
            # Step 5: Cleanup browser resources
            if self.browser_manager:
                self.browser_manager.close_browser()
