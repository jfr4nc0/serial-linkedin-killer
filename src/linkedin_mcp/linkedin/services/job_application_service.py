import uuid
from typing import Dict, List

from src.config.config_loader import load_config
from src.linkedin_mcp.linkedin.agents.easy_apply_agent import EasyApplyAgent
from src.linkedin_mcp.linkedin.graphs.job_application_graph import JobApplicationGraph
from src.linkedin_mcp.linkedin.interfaces.services import IJobApplicationService
from src.linkedin_mcp.linkedin.model.types import (
    ApplicationRequest,
    ApplicationResult,
    CVAnalysis,
)
from src.linkedin_mcp.linkedin.observability.langfuse_config import create_mcp_trace
from src.linkedin_mcp.linkedin.services.browser_manager_service import (
    BrowserManagerService as BrowserManager,
)
from src.linkedin_mcp.linkedin.services.linkedin_auth_service import LinkedInAuthService
from src.linkedin_mcp.linkedin.utils.logging_config import get_mcp_logger


class JobApplicationService(IJobApplicationService):
    """Service responsible for orchestrating complete LinkedIn job application workflow."""

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
        self.job_application_agent = EasyApplyAgent()

        # Inject dependencies into the graph
        self.application_graph = JobApplicationGraph(
            job_application_agent=self.job_application_agent,
            browser_manager=self.browser_manager,
        )
        self.auth_service = LinkedInAuthService()

    def apply_to_jobs(
        self,
        applications: List[ApplicationRequest],
        cv_analysis: CVAnalysis,
        user_credentials: Dict[str, str],
    ) -> List[ApplicationResult]:
        """
        Apply to multiple jobs using LinkedIn's easy apply with AI-powered form handling.

        Args:
            applications: List of application requests with job_id and monthly_salary
            cv_analysis: Structured CV analysis data for AI form filling
            user_credentials: User authentication credentials (email, password)

        Returns:
            List of application results with id_job, success status, and optional error message
        """
        # Create main trace for this job application workflow
        trace_id = str(uuid.uuid4())

        # Create Langfuse trace for full workflow
        langfuse_trace = create_mcp_trace(
            name="linkedin_job_application_workflow",
            trace_id=trace_id,
            metadata={
                "applications_count": len(applications),
                "email": user_credentials.get("email", "unknown"),
                "workflow_type": "job_application",
            },
        )

        logger = get_mcp_logger(trace_id)
        logger.info(
            "Starting LinkedIn job application workflow",
            applications_count=len(applications),
            email=user_credentials.get("email", "unknown"),
        )

        # Extract credentials
        email = user_credentials.get("email")
        password = user_credentials.get("password")

        if not email or not password:
            error_msg = "Email and password are required in user_credentials"
            logger.error("Invalid credentials", error=error_msg)
            raise ValueError(error_msg)

        try:
            # Step 1: Initialize browser
            logger.info("Starting job application workflow")
            print("\n🚀 Starting LinkedIn Job Application Workflow")
            logger.info("Initializing browser")
            self.browser_manager.start_browser()

            # Step 2: Authenticate with LinkedIn
            logger.info("Authenticating with LinkedIn", email=email)
            auth_result = self.auth_service.authenticate(
                email, password, self.browser_manager
            )

            if not auth_result["authenticated"]:
                raise Exception(
                    f"Authentication failed: {auth_result.get('error', 'Unknown error')}"
                )

            # Step 3: Execute job application workflow with AI form handling
            logger.info("Starting job application graph execution")
            raw_results = self.application_graph.execute(
                applications, cv_analysis, self.browser_manager, trace_id=trace_id
            )

            # Step 4: Convert to ApplicationResult format
            return [
                ApplicationResult(
                    id_job=result["job_id"],
                    success=result["success"],
                    error=result.get("error"),
                )
                for result in raw_results
            ]

        except Exception as e:
            # Return error results for all jobs
            return [
                ApplicationResult(
                    id_job=application["job_id"],
                    success=False,
                    error=f"Application workflow failed: {str(e)}",
                )
                for application in applications
            ]

        finally:
            # Step 5: Cleanup browser resources
            if self.browser_manager:
                self.browser_manager.close_browser()
