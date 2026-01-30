"""FastAPI application factory for the core agent API."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from src.core.api.controllers.job_controller import router as job_router
from src.core.api.controllers.outreach_controller import router as outreach_router
from src.core.api.services.job_service import JobService
from src.core.api.services.outreach_service import OutreachService
from src.core.api.services.session_store import SessionStore
from src.core.kafka.producer import KafkaResultProducer

_producer: KafkaResultProducer | None = None
_session_store: SessionStore | None = None
_job_service: JobService | None = None
_outreach_service: OutreachService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _producer, _session_store, _job_service, _outreach_service

    from src.core.utils.logging_config import configure_core_agent_logging

    configure_core_agent_logging()

    logger.info("Initializing Kafka producer, session store, and services")
    _producer = KafkaResultProducer()
    _session_store = SessionStore(ttl=3600)  # 1 hour session TTL
    _job_service = JobService(_producer)
    _outreach_service = OutreachService(_producer, _session_store)

    yield

    logger.info("Shutting down services")
    if _session_store:
        _session_store.clear()
    if _producer:
        _producer.close()

    from src.linkedin_mcp.linkedin.services.browser_manager_service import (
        BrowserManagerService,
    )

    BrowserManagerService.cleanup_all()


def get_job_service() -> JobService:
    return _job_service


def get_outreach_service() -> OutreachService:
    return _outreach_service


app = FastAPI(
    title="Serial Job Applier API",
    description="Core agent API for job application and outreach workflows",
    lifespan=lifespan,
)

app.include_router(job_router)
app.include_router(outreach_router)


@app.get("/health")
def health():
    return {"status": "ok"}
