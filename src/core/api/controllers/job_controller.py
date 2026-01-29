"""Controller for job application endpoints."""

from fastapi import APIRouter, Depends

from src.core.api.schemas.common import TaskResponse
from src.core.api.schemas.job_schemas import JobApplyRequest
from src.core.api.services.job_service import JobService

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def get_job_service() -> JobService:
    from src.core.api.app import get_job_service as _get

    return _get()


@router.post("/apply", response_model=TaskResponse)
def apply_jobs(
    request: JobApplyRequest,
    service: JobService = Depends(get_job_service),
) -> TaskResponse:
    """Submit a job application workflow. Returns a task_id for tracking via Kafka."""
    task_id = service.submit(request)
    return TaskResponse(task_id=task_id)
