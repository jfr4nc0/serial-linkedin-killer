import uuid
from typing import Any, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from src.linkedin_mcp.interfaces.agents import IJobApplicationAgent
from src.linkedin_mcp.interfaces.services import IBrowserManager
from src.linkedin_mcp.model.types import ApplicationRequest, CVAnalysis
from src.linkedin_mcp.observability.langfuse_config import (
    get_langfuse_config_for_mcp_langgraph,
)
from src.linkedin_mcp.utils.logging_config import get_mcp_logger


class JobApplicationState(TypedDict):
    applications: List[ApplicationRequest]
    cv_analysis: CVAnalysis
    browser_manager: IBrowserManager
    current_application_index: int
    application_results: List[dict]
    current_application: Optional[ApplicationRequest]
    job_application_agent: IJobApplicationAgent
    errors: List[str]
    trace_id: str  # UUID for tracing this workflow execution


class JobApplicationGraph:
    """LangGraph workflow for LinkedIn job application RPA."""

    def __init__(
        self,
        job_application_agent: IJobApplicationAgent,
        browser_manager: IBrowserManager,
    ):
        self.job_application_agent = job_application_agent
        self.browser_manager = browser_manager
        self.graph = self._create_graph()

    def _create_graph(self) -> StateGraph:
        """Create the job application workflow graph."""
        workflow = StateGraph(JobApplicationState)

        # Add nodes for job application workflow
        workflow.add_node("initialize_agent", self._initialize_agent)
        workflow.add_node("select_next_application", self._select_next_application)
        workflow.add_node("process_application", self._process_application)
        workflow.add_node("record_result", self._record_result)

        # Define the simplified flow
        workflow.set_entry_point("initialize_agent")
        workflow.add_edge("initialize_agent", "select_next_application")

        # Conditional edge to check if there are more applications
        workflow.add_conditional_edges(
            "select_next_application",
            self._has_more_applications,
            {"continue": "process_application", "finish": END},
        )

        workflow.add_edge("process_application", "record_result")
        workflow.add_edge("record_result", "select_next_application")

        # Compile the graph - Langfuse observability is handled during invoke
        logger = get_mcp_logger("graph-compilation")
        logger.info(
            "JobApplicationGraph compiled - observability handled during invoke"
        )
        return workflow.compile()

    def _initialize_agent(self, state: JobApplicationState) -> JobApplicationState:
        """Initialize the job application agent."""
        trace_id = state.get("trace_id", str(uuid.uuid4()))
        logger = get_mcp_logger(trace_id)

        logger.info(
            "Initializing job application agent",
            trace_id=trace_id,
            applications_count=len(state.get("applications", [])),
        )

        return {
            **state,
            "trace_id": trace_id,
            "job_application_agent": self.job_application_agent,
            "browser_manager": self.browser_manager,
            "current_application_index": 0,
        }

    def _select_next_application(
        self, state: JobApplicationState
    ) -> JobApplicationState:
        """Select the next application to process."""
        trace_id = state.get("trace_id", "unknown")
        logger = get_mcp_logger(trace_id)
        current_index = state["current_application_index"]
        total_applications = len(state["applications"])

        if current_index < total_applications:
            current_application = state["applications"][current_index]
            logger.info(
                "Selected next application to process",
                trace_id=trace_id,
                current_index=current_index,
                total_applications=total_applications,
                job_id=current_application.get("job_id", "unknown"),
            )
            return {**state, "current_application": current_application}
        else:
            logger.info(
                "No more applications to process",
                trace_id=trace_id,
                processed_count=current_index,
                total_applications=total_applications,
            )
            return state

    def _process_application(self, state: JobApplicationState) -> JobApplicationState:
        """Process a single job application using the EasyApply agent."""
        trace_id = state.get("trace_id", "unknown")
        logger = get_mcp_logger(trace_id)
        current_app = state["current_application"]
        job_id = current_app.get("job_id", "unknown")

        try:
            logger.info(
                "Starting job application processing",
                trace_id=trace_id,
                job_id=job_id,
                monthly_salary=current_app.get("monthly_salary", 0),
            )

            result = state["job_application_agent"].apply_to_job(
                job_id=current_app["job_id"],
                application_request=current_app,
                cv_analysis=state["cv_analysis"],
                browser_manager=state["browser_manager"],
            )

            logger.info(
                "Job application processing completed",
                trace_id=trace_id,
                job_id=job_id,
                success=result.get("success", False),
                result_keys=(
                    list(result.keys()) if isinstance(result, dict) else "non-dict"
                ),
            )

            return {
                **state,
                "application_results": state["application_results"] + [result],
            }

        except Exception as e:
            logger.error(
                "Job application processing failed",
                trace_id=trace_id,
                job_id=job_id,
                error=str(e),
                error_type=type(e).__name__,
            )

            error_result = {
                "job_id": state["current_application"]["job_id"],
                "success": False,
                "error": f"Application processing failed: {str(e)}",
            }

            return {
                **state,
                "application_results": state["application_results"] + [error_result],
                "errors": state["errors"] + [str(e)],
            }

    def _record_result(self, state: JobApplicationState) -> JobApplicationState:
        """Update the application index to move to next application."""
        return {
            **state,
            "current_application_index": state["current_application_index"] + 1,
        }

    def _has_more_applications(self, state: JobApplicationState) -> str:
        """Check if there are more applications to process."""
        if state["current_application_index"] < len(state["applications"]):
            return "continue"
        return "finish"

    def execute(
        self,
        applications: List[ApplicationRequest],
        cv_analysis: CVAnalysis,
        authenticated_browser_manager: IBrowserManager,
        trace_id: str = None,
    ) -> List[dict]:
        """Execute the job application workflow with pre-authenticated browser."""
        # Generate trace_id if not provided
        if not trace_id:
            trace_id = str(uuid.uuid4())

        logger = get_mcp_logger(trace_id)
        logger.info(
            "Executing job application graph",
            trace_id=trace_id,
            applications_count=len(applications),
        )

        initial_state = JobApplicationState(
            applications=applications,
            cv_analysis=cv_analysis,
            browser_manager=authenticated_browser_manager,
            current_application_index=0,
            application_results=[],
            current_application=None,
            job_application_agent=None,
            errors=[],
            trace_id=trace_id,  # Propagate trace_id through the workflow
        )

        result = self.graph.invoke(initial_state)

        logger.info(
            "Job application graph execution completed",
            trace_id=trace_id,
            results_count=len(result.get("application_results", [])),
            errors_count=len(result.get("errors", [])),
        )

        return result["application_results"]
