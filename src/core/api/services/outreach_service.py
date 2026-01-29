"""Service layer for the employee outreach workflow."""

import threading
import uuid

from loguru import logger

from src.config.config_loader import load_config
from src.core.api.schemas.outreach_schemas import (
    OutreachFiltersResponse,
    OutreachRunRequest,
    OutreachRunResponse,
)
from src.core.kafka.producer import TOPIC_OUTREACH_RESULTS, KafkaResultProducer
from src.core.tools.company_db import CompanyDB


class OutreachService:
    """Orchestrates the outreach agent and publishes results to Kafka."""

    def __init__(self, producer: KafkaResultProducer):
        self._producer = producer
        self._config = load_config()

    def get_filters(self) -> OutreachFiltersResponse:
        """Query the SQLite database for available filter values."""
        db = CompanyDB(self._config.outreach.db_path)
        try:
            return OutreachFiltersResponse(
                industries=db.get_unique_values("industry"),
                countries=db.get_unique_values("country"),
                sizes=db.get_unique_values("size"),
                total_companies=db.get_total_count(),
            )
        finally:
            db.close()

    def submit(self, request: OutreachRunRequest) -> str:
        """Submit an outreach workflow. Returns task_id immediately."""
        task_id = str(uuid.uuid4())

        thread = threading.Thread(
            target=self._run,
            args=(task_id, request),
            daemon=True,
        )
        thread.start()

        return task_id

    def _run(self, task_id: str, request: OutreachRunRequest) -> None:
        """Execute the outreach agent and publish results."""
        from src.core.agents.outreach_agent import EmployeeOutreachAgent

        try:
            logger.info("Starting outreach workflow", task_id=task_id)

            # Query filtered companies from SQLite
            db = CompanyDB(self._config.outreach.db_path)
            try:
                companies = db.filter_companies(request.filters)
            finally:
                db.close()

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

            # Override daily limit for warm-up
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

        self._producer.publish(TOPIC_OUTREACH_RESULTS, task_id, response)
