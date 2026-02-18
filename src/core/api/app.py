"""FastAPI application factory for the core agent API."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from src.config.config_loader import load_config
from src.core.api.controllers.campaign_controller import router as campaign_router
from src.core.api.controllers.job_controller import router as job_router
from src.core.api.controllers.oauth_controller import router as oauth_router
from src.core.api.controllers.outreach_controller import router as outreach_router
from src.core.api.services.campaign_service import CampaignService
from src.core.api.services.content_generation_service import ContentGenerationService
from src.core.api.services.job_service import JobService
from src.core.api.services.outreach_service import OutreachService
from src.core.api.services.session_store import SessionStore
from src.core.db.agent_db import AgentDB
from src.core.queue.producer import KafkaResultProducer

_producer: KafkaResultProducer | None = None
_agent_db: AgentDB | None = None
_session_store: SessionStore | None = None
_job_service: JobService | None = None
_outreach_service: OutreachService | None = None
_campaign_service: CampaignService | None = None
_content_generation_service: ContentGenerationService | None = None


def get_agent_db() -> AgentDB:
    return _agent_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _producer, _agent_db, _session_store, _job_service, _outreach_service, _campaign_service, _content_generation_service

    from src.core.utils.logging_config import configure_core_agent_logging

    configure_core_agent_logging()

    config = load_config()
    logger.info("Initializing database, Kafka producer, and services")
    _agent_db = AgentDB(config.db.url)
    _producer = KafkaResultProducer()

    # Ensure all Kafka topics exist at startup
    from src.core.queue.config import ensure_topics

    ensure_topics()

    # Check LinkedIn OAuth token health on startup
    try:
        from src.core.providers.linkedin_api_client import LinkedInAPIClient
        li_client = LinkedInAPIClient(_agent_db._engine)
        token_health = li_client.check_token_health()
        if token_health["warning"]:
            logger.warning(token_health["warning"])
        elif not token_health["valid"]:
            logger.info("LinkedIn API: No OAuth token configured. Visit /api/oauth/linkedin/authorize to authenticate.")
    except Exception as e:
        logger.debug(f"LinkedIn token health check skipped: {e}")

    _session_store = SessionStore(agent_db=_agent_db, ttl=3600)
    _job_service = JobService(_producer)
    _outreach_service = OutreachService(_producer, _session_store)
    _campaign_service = CampaignService(_agent_db._engine)
    _content_generation_service = ContentGenerationService(_agent_db._engine)

    yield

    logger.info("Shutting down services")
    if _session_store:
        _session_store.clear()
    if _producer:
        _producer.close()

    from src.linkedin_mcp.services.browser_manager_service import BrowserManagerService

    BrowserManagerService.cleanup_all()


def get_job_service() -> JobService:
    return _job_service


def get_outreach_service() -> OutreachService:
    return _outreach_service


def get_campaign_service() -> CampaignService:
    return _campaign_service


def get_content_generation_service() -> ContentGenerationService:
    return _content_generation_service


app = FastAPI(
    title="Serial Job Applier API",
    description="Core agent API for job application and outreach workflows",
    lifespan=lifespan,
)

app.include_router(job_router)
app.include_router(outreach_router)
app.include_router(oauth_router)
app.include_router(campaign_router)


@app.get("/health")
def health():
    return {"status": "ok"}
