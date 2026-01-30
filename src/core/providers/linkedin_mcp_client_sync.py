import asyncio
import threading
from typing import Any, Dict, List, Optional, Union

from src.core.model import ApplicationRequest, ApplicationResult, CVAnalysis, JobResult
from src.core.providers.linkedin_mcp_client import LinkedInMCPClient


class LinkedInMCPClientSync:
    """
    Synchronous wrapper for the LinkedInMCPClient.
    Uses a single persistent event loop in a background thread
    to avoid event loop churn from asyncio.run().
    """

    _loop: asyncio.AbstractEventLoop = None
    _thread: threading.Thread = None
    _lock = threading.Lock()

    @classmethod
    def _get_loop(cls) -> asyncio.AbstractEventLoop:
        """Get or create a persistent event loop running in a daemon thread."""
        with cls._lock:
            if cls._loop is None or cls._loop.is_closed():
                cls._loop = asyncio.new_event_loop()
                cls._thread = threading.Thread(
                    target=cls._loop.run_forever,
                    daemon=True,
                    name="mcp-event-loop",
                )
                cls._thread.start()
            return cls._loop

    def __init__(self, server_host: str = None, server_port: int = None):
        self.client = LinkedInMCPClient()

    def _run(self, coro):
        """Run a coroutine on the persistent event loop and wait for the result."""
        loop = self._get_loop()
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result()

    def search_jobs(
        self,
        job_title: str,
        location: str,
        easy_apply: bool,
        email: str,
        password: str,
        limit: int = 50,
        trace_id: str = None,
    ) -> List[JobResult]:
        """Synchronous wrapper for search_jobs."""

        async def _search():
            async with self.client as client:
                return await client.search_jobs(
                    job_title, location, easy_apply, email, password, limit, trace_id
                )

        return self._run(_search())

    def search_employees(
        self,
        company_linkedin_url: str,
        company_name: str,
        email: str,
        password: str,
        limit: int = 10,
        trace_id: str = None,
    ) -> List[Dict[str, Any]]:
        """Synchronous wrapper for search_employees."""

        async def _search():
            async with self.client as client:
                return await client.search_employees(
                    company_linkedin_url, company_name, email, password, limit, trace_id
                )

        return self._run(_search())

    def send_message(
        self,
        employee_profile_url: str,
        employee_name: str,
        message: str,
        email: str,
        password: str,
        trace_id: str = None,
    ) -> Dict[str, Any]:
        """Synchronous wrapper for send_message."""

        async def _send():
            async with self.client as client:
                return await client.send_message(
                    employee_profile_url,
                    employee_name,
                    message,
                    email,
                    password,
                    trace_id,
                )

        return self._run(_send())

    def search_employees_batch(
        self,
        companies: List[Dict[str, Any]],
        email: str,
        password: str,
        total_limit: int = None,
        trace_id: str = None,
    ) -> List[Dict[str, Any]]:
        """Synchronous wrapper for search_employees_batch."""

        async def _search():
            async with self.client as client:
                return await client.search_employees_batch(
                    companies, email, password, total_limit, trace_id
                )

        return self._run(_search())

    def easy_apply_for_jobs(
        self,
        applications: List[ApplicationRequest],
        cv_analysis: Union[CVAnalysis, Dict[str, Any]],
        email: str,
        password: str,
        trace_id: str = None,
    ) -> List[ApplicationResult]:
        """Synchronous wrapper for easy_apply_for_jobs."""

        async def _apply():
            async with self.client as client:
                return await client.easy_apply_for_jobs(
                    applications, cv_analysis, email, password, trace_id
                )

        return self._run(_apply())
