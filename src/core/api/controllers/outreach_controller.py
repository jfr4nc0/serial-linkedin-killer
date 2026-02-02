"""Controller for employee outreach endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from src.core.api.schemas.common import TaskResponse
from src.core.api.schemas.outreach_schemas import (
    OutreachFiltersResponse,
    OutreachRunRequest,
    OutreachSearchRequest,
    OutreachSendRequest,
)
from src.core.api.services.outreach_service import OutreachService

router = APIRouter(prefix="/api/outreach", tags=["outreach"])


def get_outreach_service() -> OutreachService:
    from src.core.api.app import get_outreach_service as _get

    return _get()


@router.get("/filters", response_model=OutreachFiltersResponse)
def get_filters(
    service: OutreachService = Depends(get_outreach_service),
) -> OutreachFiltersResponse:
    """Get available filter values (industries, countries, sizes) from the company dataset."""
    return service.get_filters()


@router.post("/run", response_model=TaskResponse)
def run_outreach(
    request: OutreachRunRequest,
    service: OutreachService = Depends(get_outreach_service),
) -> TaskResponse:
    """Legacy: Submit a single-phase outreach workflow. Returns a task_id for tracking via Kafka."""
    task_id = service.submit(request)
    return TaskResponse(task_id=task_id)


@router.post("/search", response_model=TaskResponse)
def search_employees(
    request: OutreachSearchRequest,
    service: OutreachService = Depends(get_outreach_service),
) -> TaskResponse:
    """Phase 1: Submit search & cluster. Returns task_id, results via Kafka."""
    task_id = service.submit_search(request)
    return TaskResponse(task_id=task_id)


@router.post("/send", response_model=TaskResponse)
def send_messages(
    request: OutreachSendRequest,
    service: OutreachService = Depends(get_outreach_service),
) -> TaskResponse:
    """Phase 2: Send messages to selected role groups. Returns task_id, results via Kafka."""
    try:
        task_id = service.submit_send(request)
        return TaskResponse(task_id=task_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
