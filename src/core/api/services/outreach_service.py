"""Service layer for the employee outreach workflow."""

import atexit
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from loguru import logger

from src.config.config_loader import load_config
from src.config.trace_context import set_trace_id, trace_context
from src.core.agents.tools.company_db import CompanyDB
from src.core.agents.tools.role_clustering import cluster_employees_by_role
from src.core.api.schemas.outreach_schemas import (
    OutreachFiltersResponse,
    OutreachRunRequest,
    OutreachRunResponse,
    OutreachSearchRequest,
    OutreachSearchResponse,
    OutreachSendRequest,
    OutreachSendResponse,
)
from src.core.api.services.session_store import SessionStore
from src.core.queue.producer import (
    TOPIC_OUTREACH_RESULTS,
    TOPIC_OUTREACH_SEARCH_RESULTS,
    KafkaResultProducer,
)

# Module-level thread pool with bounded workers
_executor: ThreadPoolExecutor | None = None


def _get_executor() -> ThreadPoolExecutor:
    """Get or create the shared thread pool executor."""
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="outreach")
    return _executor


def _shutdown_executor():
    """Shutdown the thread pool on application exit."""
    global _executor
    if _executor is not None:
        _executor.shutdown(wait=True, cancel_futures=False)
        _executor = None


# Register cleanup on exit
atexit.register(_shutdown_executor)


def _log_future_exception(future):
    """Callback to log uncaught exceptions from thread pool futures."""
    exc = future.exception()
    if exc:
        logger.exception(
            "Background task failed with uncaught exception", error=str(exc)
        )


class OutreachService:
    """Orchestrates the outreach agent and publishes results to Kafka."""

    def __init__(
        self,
        producer: KafkaResultProducer,
        session_store: Optional[SessionStore] = None,
    ):
        self._producer = producer
        self._session_store = session_store or SessionStore()
        self._config = load_config()

    def get_filters(self) -> OutreachFiltersResponse:
        """Query the SQLite database for available filter values."""
        with CompanyDB(self._config.db.company_url) as db:
            return OutreachFiltersResponse(
                industries=db.get_unique_values("industry"),
                countries=db.get_unique_values("country"),
                sizes=db.get_unique_values("size"),
                total_companies=db.get_total_count(),
            )

    # === Phase 1: Search & Cluster (async via Kafka) ===

    def submit_search(self, request: OutreachSearchRequest) -> str:
        """Phase 1: Submit search & cluster. Returns task_id, results via Kafka."""
        task_id = str(uuid.uuid4())
        future = _get_executor().submit(self._run_search, task_id, request)
        future.add_done_callback(_log_future_exception)
        return task_id

    def _run_search(self, task_id: str, request: OutreachSearchRequest) -> None:
        """Execute search & cluster and publish results to Kafka."""
        import time

        from src.core.agents.outreach_agent import EmployeeOutreachAgent

        # Set trace context for this entire request (auto-propagates to all logs)
        trace_id = set_trace_id()

        try:
            t_start = time.perf_counter()
            logger.info("Starting search and cluster", task_id=task_id)

            # Filter companies from DB
            with CompanyDB(self._config.db.company_url) as db:
                companies = db.filter_companies(request.filters)

            if request.company_limit and len(companies) > request.company_limit:
                logger.info(
                    "Limiting companies",
                    total_matching=len(companies),
                    company_limit=request.company_limit,
                )
                companies = companies[: request.company_limit]

            if not companies:
                response = OutreachSearchResponse(
                    session_id="",
                    role_groups={},
                    total_employees=0,
                    companies_processed=0,
                    trace_id=trace_id,
                )
                self._producer.publish(TOPIC_OUTREACH_SEARCH_RESULTS, task_id, response)
                return

            # Run search-only phase of the agent
            from src.core.api.app import get_agent_db

            agent = EmployeeOutreachAgent(agent_db=get_agent_db())
            # When segment filtering is active, don't cap during search —
            # the limit is applied after filtering to the target segment.
            search_limit = None if request.segment else request.total_limit
            employees = agent.run_search_only(
                companies=companies,
                user_credentials=request.credentials.model_dump(),
                total_limit=search_limit,
                exclude_companies=request.exclude_companies,
                exclude_profile_urls=request.exclude_profile_urls,
            )

            t_pre_cluster = time.perf_counter()
            logger.info(
                "[TIMING] Pre-clustering",
                elapsed_ms=round((t_pre_cluster - t_start) * 1000, 2),
                employees_count=len(employees),
            )

            # Cluster employees by role using LLM (with progress logging)
            def log_progress(batch: int, total: int, processed: int, total_titles: int):
                logger.info(
                    f"[PROGRESS] LLM clustering: batch {batch}/{total}, "
                    f"{processed}/{total_titles} titles classified"
                )

            clustered = cluster_employees_by_role(
                employees, progress_callback=log_progress
            )

            t_post_cluster = time.perf_counter()
            logger.info(
                "[TIMING] Post-clustering",
                elapsed_ms=round((t_post_cluster - t_pre_cluster) * 1000, 2),
            )

            # Filter by B2C/B2B segment if requested
            if request.segment:
                from src.core.agents.tools.role_clustering import filter_by_segment

                clustered = filter_by_segment(clustered, request.segment)
                employees = [e for group in clustered.values() for e in group]

                # Apply total_limit after segment filtering
                if request.total_limit and len(employees) > request.total_limit:
                    employees = employees[: request.total_limit]
                    emp_urls = {e.get("profile_url") for e in employees}
                    clustered = {
                        k: [e for e in v if e.get("profile_url") in emp_urls]
                        for k, v in clustered.items()
                    }

            # Store only clustered in session (no duplicate employees list)
            t_pre_session = time.perf_counter()
            session_id = self._session_store.create(
                clustered=clustered,
                trace_id=trace_id,
            )
            t_post_session = time.perf_counter()
            logger.info(
                "[TIMING] Session created",
                elapsed_ms=round((t_post_session - t_pre_session) * 1000, 2),
            )

            logger.info(
                "Search and cluster complete",
                task_id=task_id,
                session_id=session_id,
                total_employees=len(employees),
                companies=len(companies),
            )

            t_pre_response = time.perf_counter()
            response = OutreachSearchResponse(
                session_id=session_id,
                role_groups=clustered,
                total_employees=len(employees),
                companies_processed=len(companies),
                trace_id=trace_id,
            )
            t_post_response = time.perf_counter()
            logger.info(
                "[TIMING] Response object created",
                elapsed_ms=round((t_post_response - t_pre_response) * 1000, 2),
            )

        except Exception as e:
            logger.exception("Search and cluster failed", task_id=task_id)
            response = OutreachSearchResponse(
                session_id="",
                role_groups={},
                total_employees=0,
                companies_processed=0,
                trace_id="",
            )
            t_post_response = time.perf_counter()

        t_pre_publish = time.perf_counter()
        self._producer.publish(TOPIC_OUTREACH_SEARCH_RESULTS, task_id, response)
        t_post_publish = time.perf_counter()
        logger.info(
            "[TIMING] Kafka publish (before flush)",
            elapsed_ms=round((t_post_publish - t_pre_publish) * 1000, 2),
        )

        self._producer.flush()
        t_post_flush = time.perf_counter()
        logger.info(
            "[TIMING] Kafka flush complete",
            elapsed_ms=round((t_post_flush - t_post_publish) * 1000, 2),
            total_elapsed_ms=round((t_post_flush - t_start) * 1000, 2),
        )

    # === Phase 2: Send Messages ===

    def submit_send(self, request: OutreachSendRequest) -> str:
        """Phase 2: Submit message sending. Returns task_id, async via Kafka."""
        # Retrieve session
        session = self._session_store.get(request.session_id)
        if not session:
            raise ValueError(f"Session not found or expired: {request.session_id}")

        task_id = str(uuid.uuid4())

        # Submit to thread pool instead of creating unbounded daemon threads
        future = _get_executor().submit(self._run_send, task_id, request, session)
        future.add_done_callback(_log_future_exception)

        # Delete session after use (data is passed to thread)
        self._session_store.delete(request.session_id)

        return task_id

    def _run_send(
        self,
        task_id: str,
        request: OutreachSendRequest,
        session: dict,
    ) -> None:
        """Execute the send phase and publish results to Kafka."""
        from src.core.agents.outreach_agent import EmployeeOutreachAgent

        # Restore trace context from session (propagated from search phase)
        trace_id = session.get("trace_id") or set_trace_id()
        set_trace_id(trace_id)

        try:
            logger.info("Starting send phase", task_id=task_id, trace_id=trace_id)

            # Build list of employees with their templates attached
            employees_with_templates = []
            clustered = session["clustered"]

            # Apply role reassignments from client (fixes LLM misclassifications)
            if request.reassignments:
                for profile_url, new_role in request.reassignments.items():
                    # Find and move the employee
                    for old_role, emps in list(clustered.items()):
                        for emp in emps:
                            if emp.get("profile_url") == profile_url:
                                emps.remove(emp)
                                if new_role not in clustered:
                                    clustered[new_role] = []
                                clustered[new_role].append(emp)
                                logger.info(
                                    "Reassigned employee",
                                    name=emp.get("name"),
                                    old_role=old_role,
                                    new_role=new_role,
                                )
                                break
                        else:
                            continue
                        break

            for role, config in request.selected_groups.items():
                if not config.enabled:
                    continue

                role_employees = clustered.get(role, [])
                for emp in role_employees:
                    employees_with_templates.append(
                        {
                            **emp,
                            "_template": config.message_template,
                            "_template_vars": config.template_variables,
                            "_role": role,
                        }
                    )

            # Filter to selected employees if specified
            if request.selected_employees:
                selected_set = set(request.selected_employees)
                before_count = len(employees_with_templates)
                employees_with_templates = [
                    emp
                    for emp in employees_with_templates
                    if emp.get("profile_url") in selected_set
                ]
                logger.info(
                    f"Filtered to {len(employees_with_templates)} selected employees "
                    f"(from {before_count})"
                )

            if not employees_with_templates:
                response = OutreachSendResponse(
                    task_id=task_id,
                    status="no employees in selected groups",
                    message_results=[],
                    messages_sent=0,
                    results_by_role={},
                    errors=[],
                    trace_id=trace_id,
                )
                self._producer.publish(TOPIC_OUTREACH_RESULTS, task_id, response)
                return

            # Apply warm_up limit
            daily_limit = self._config.outreach.daily_message_limit
            if request.warm_up:
                daily_limit = 10

            from src.core.api.app import get_agent_db

            agent = EmployeeOutreachAgent(agent_db=get_agent_db())
            state = agent.run_send(
                employees_with_templates=employees_with_templates,
                user_credentials=request.credentials.model_dump(),
                daily_limit=daily_limit,
                max_per_company=request.max_per_company,
                trace_id=trace_id,
            )

            # Build results by role
            results_by_role = {}
            for result in state.get("message_results", []):
                role = result.get("_role", "Other")
                if role not in results_by_role:
                    results_by_role[role] = {"sent": 0, "failed": 0}
                if result.get("sent"):
                    results_by_role[role]["sent"] += 1
                else:
                    results_by_role[role]["failed"] += 1

            response = OutreachSendResponse(
                task_id=task_id,
                status=state.get("current_status", "completed"),
                message_results=state.get("message_results", []),
                messages_sent=state.get("messages_sent_today", 0),
                results_by_role=results_by_role,
                errors=state.get("errors", []),
                trace_id=trace_id,
            )

        except Exception as e:
            logger.exception("Send phase failed", task_id=task_id)
            response = OutreachSendResponse(
                task_id=task_id,
                status=f"failed: {e}",
                message_results=[],
                messages_sent=0,
                results_by_role={},
                errors=[str(e)],
                trace_id="",
            )

        self._producer.publish(TOPIC_OUTREACH_RESULTS, task_id, response)

    # === Legacy Single-Phase (backward compatibility) ===

    def submit(self, request: OutreachRunRequest) -> str:
        """Legacy: Submit a single-phase outreach workflow. Returns task_id immediately."""
        task_id = str(uuid.uuid4())

        future = _get_executor().submit(self._run, task_id, request)
        future.add_done_callback(_log_future_exception)

        return task_id

    def _run(self, task_id: str, request: OutreachRunRequest) -> None:
        """Execute the legacy single-phase outreach agent and publish results."""
        from src.core.agents.outreach_agent import EmployeeOutreachAgent

        try:
            logger.info("Starting outreach workflow", task_id=task_id)

            with CompanyDB(self._config.db.company_url) as db:
                companies = db.filter_companies(request.filters)

            if not companies:
                response = OutreachRunResponse(
                    task_id=task_id,
                    status="no companies matched filters",
                    employees_found=[],
                    message_results=[],
                    messages_sent=0,
                    errors=[],
                    trace_id="",
                )
                self._producer.publish(TOPIC_OUTREACH_RESULTS, task_id, response)
                return

            if request.warm_up:
                self._config.outreach.daily_message_limit = 10

            from src.core.api.app import get_agent_db

            agent = EmployeeOutreachAgent(agent_db=get_agent_db())
            credentials = request.credentials.model_dump()

            state = agent.run(
                companies=companies,
                message_template=request.message_template,
                template_variables=request.template_variables,
                user_credentials=credentials,
            )

            response = OutreachRunResponse(
                task_id=task_id,
                status=state.get("current_status", "completed"),
                employees_found=state.get("employees_found", []),
                message_results=state.get("message_results", []),
                messages_sent=state.get("messages_sent_today", 0),
                errors=state.get("errors", []),
                trace_id=state.get("trace_id", ""),
            )

        except Exception as e:
            logger.exception("Outreach workflow failed", task_id=task_id)
            response = OutreachRunResponse(
                task_id=task_id,
                status=f"failed: {e}",
                employees_found=[],
                message_results=[],
                messages_sent=0,
                errors=[str(e)],
                trace_id="",
            )

        self._producer.publish(TOPIC_OUTREACH_RESULTS, task_id, response)
