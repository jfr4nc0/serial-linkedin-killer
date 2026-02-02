"""Service layer for the job application workflow."""

import atexit
import gc
import uuid
from concurrent.futures import ThreadPoolExecutor

from loguru import logger

from src.config.config_loader import load_config
from src.core.api.schemas.job_schemas import JobApplyRequest, JobApplyResponse
from src.core.queue.producer import TOPIC_JOB_RESULTS, KafkaResultProducer

# Module-level thread pool with bounded workers
_executor: ThreadPoolExecutor | None = None


def _get_executor() -> ThreadPoolExecutor:
    """Get or create the shared thread pool executor."""
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="job-apply")
    return _executor


def _shutdown_executor():
    """Shutdown the thread pool on application exit."""
    global _executor
    if _executor is not None:
        _executor.shutdown(wait=True, cancel_futures=False)
        _executor = None


# Register cleanup on exit
atexit.register(_shutdown_executor)


class JobService:
    """Orchestrates the job application agent and publishes results to Kafka."""

    def __init__(self, producer: KafkaResultProducer):
        self._producer = producer
        self._config = load_config()

    def submit(self, request: JobApplyRequest) -> str:
        """Submit a job application workflow. Returns task_id immediately."""
        task_id = str(uuid.uuid4())

        # Submit to thread pool instead of creating unbounded daemon threads
        _get_executor().submit(self._run, task_id, request)

        return task_id

    def _run(self, task_id: str, request: JobApplyRequest) -> None:
        """Execute the job application agent and publish results."""
        from src.core.agent import JobApplicationAgent

        agent = None
        try:
            logger.info("Starting job application workflow", task_id=task_id)

            agent = JobApplicationAgent(
                server_host=self._config.mcp_server.host,
                server_port=self._config.mcp_server.port,
            )

            job_searches = [s.model_dump() for s in request.job_searches]
            credentials = request.credentials.model_dump()

            state = agent.run(
                job_searches=job_searches,
                user_credentials=credentials,
                cv_data_path=request.cv_data_path,
            )

            response = JobApplyResponse(
                task_id=task_id,
                status=state.get("current_status", "completed"),
                total_jobs_found=state.get("total_jobs_found", 0),
                total_filtered=len(state.get("filtered_jobs", [])),
                total_applied=state.get("total_jobs_applied", 0),
                all_found_jobs=state.get("all_found_jobs", []),
                filtered_jobs=state.get("filtered_jobs", []),
                application_results=state.get("application_results", []),
                cv_analysis=state.get("cv_analysis", {}),
                errors=state.get("errors", []),
                trace_id=state.get("trace_id", ""),
            )

        except Exception as e:
            logger.exception("Job application workflow failed", task_id=task_id)
            response = JobApplyResponse(
                task_id=task_id,
                status=f"failed: {e}",
                total_jobs_found=0,
                total_filtered=0,
                total_applied=0,
                all_found_jobs=[],
                filtered_jobs=[],
                application_results=[],
                cv_analysis={},
                errors=[str(e)],
                trace_id="",
            )
        finally:
            del agent
            gc.collect()

        self._producer.publish(TOPIC_JOB_RESULTS, task_id, response)
