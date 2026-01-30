"""Service layer for the employee outreach workflow."""

import threading
import uuid
from typing import Optional

from loguru import logger

from src.config.config_loader import load_config
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
from src.core.kafka.producer import TOPIC_OUTREACH_RESULTS, KafkaResultProducer
from src.core.tools.company_db import CompanyDB
from src.core.tools.role_clustering import cluster_employees_by_role


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
        with CompanyDB(self._config.outreach.db_path) as db:
            return OutreachFiltersResponse(
                industries=db.get_unique_values("industry"),
                countries=db.get_unique_values("country"),
                sizes=db.get_unique_values("size"),
                total_companies=db.get_total_count(),
            )

    # === Phase 1: Search & Cluster ===

    def search_and_cluster(
        self, request: OutreachSearchRequest
    ) -> OutreachSearchResponse:
        """Phase 1: Search employees and cluster by role. Synchronous."""
        from src.core.agents.outreach_agent import EmployeeOutreachAgent

        trace_id = str(uuid.uuid4())
        logger.info("Starting search and cluster", trace_id=trace_id)

        # Filter companies from DB
        with CompanyDB(self._config.outreach.db_path) as db:
            companies = db.filter_companies(request.filters)

        if not companies:
            return OutreachSearchResponse(
                session_id="",
                role_groups={},
                total_employees=0,
                companies_processed=0,
                trace_id=trace_id,
            )

        # Run search-only phase of the agent
        agent = None
        try:
            agent = EmployeeOutreachAgent()
            employees = agent.run_search_only(
                companies=companies,
                user_credentials=request.credentials.model_dump(),
                total_limit=request.total_limit,
            )
        finally:
            del agent

        # Cluster employees by role using LLM
        clustered = cluster_employees_by_role(employees)

        # Store in session for Phase 2
        session_id = self._session_store.create(
            employees=employees,
            clustered=clustered,
            companies=companies,
            trace_id=trace_id,
        )

        logger.info(
            "Search and cluster complete",
            trace_id=trace_id,
            session_id=session_id,
            total_employees=len(employees),
            companies=len(companies),
        )

        return OutreachSearchResponse(
            session_id=session_id,
            role_groups=clustered,
            total_employees=len(employees),
            companies_processed=len(companies),
            trace_id=trace_id,
        )

    # === Phase 2: Send Messages ===

    def submit_send(self, request: OutreachSendRequest) -> str:
        """Phase 2: Submit message sending. Returns task_id, async via Kafka."""
        # Retrieve session
        session = self._session_store.get(request.session_id)
        if not session:
            raise ValueError(f"Session not found or expired: {request.session_id}")

        task_id = str(uuid.uuid4())

        thread = threading.Thread(
            target=self._run_send,
            args=(task_id, request, session),
            name=f"outreach-send-{task_id[:8]}",
            daemon=True,
        )
        thread.start()

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

        agent = None
        try:
            trace_id = session.get("trace_id", str(uuid.uuid4()))
            logger.info("Starting send phase", task_id=task_id, trace_id=trace_id)

            # Build list of employees with their templates attached
            employees_with_templates = []
            clustered = session["clustered"]

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

            agent = EmployeeOutreachAgent()
            state = agent.run_send(
                employees_with_templates=employees_with_templates,
                user_credentials=request.credentials.model_dump(),
                daily_limit=daily_limit,
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
        finally:
            del agent

        self._producer.publish(TOPIC_OUTREACH_RESULTS, task_id, response)

    # === Legacy Single-Phase (backward compatibility) ===

    def submit(self, request: OutreachRunRequest) -> str:
        """Legacy: Submit a single-phase outreach workflow. Returns task_id immediately."""
        task_id = str(uuid.uuid4())

        thread = threading.Thread(
            target=self._run,
            args=(task_id, request),
            name=f"outreach-{task_id[:8]}",
            daemon=True,
        )
        thread.start()

        return task_id

    def _run(self, task_id: str, request: OutreachRunRequest) -> None:
        """Execute the legacy single-phase outreach agent and publish results."""
        from src.core.agents.outreach_agent import EmployeeOutreachAgent

        agent = None
        try:
            logger.info("Starting outreach workflow", task_id=task_id)

            with CompanyDB(self._config.outreach.db_path) as db:
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

            agent = EmployeeOutreachAgent()
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
        finally:
            del agent

        self._producer.publish(TOPIC_OUTREACH_RESULTS, task_id, response)
