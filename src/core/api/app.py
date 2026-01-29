"""FastAPI application factory for the core agent API."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from src.core.api.controllers.job_controller import router as job_router
from src.core.api.controllers.outreach_controller import router as outreach_router
from src.core.api.services.job_service import JobService
from src.core.api.services.outreach_service import OutreachService
from src.core.kafka.producer import KafkaResultProducer

_producer: KafkaResultProducer | None = None
_job_service: JobService | None = None
_outreach_service: OutreachService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _producer, _job_service, _outreach_service

    logger.info("Initializing Kafka producer and services")
    _producer = KafkaResultProducer()
    _job_service = JobService(_producer)
    _outreach_service = OutreachService(_producer)

    yield

    logger.info("Shutting down Kafka producer")
    if _producer:
        _producer.close()


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
