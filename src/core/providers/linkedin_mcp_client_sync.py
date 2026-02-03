import asyncio
import threading
from typing import Any, Dict, List, Optional, Union

from loguru import logger

from src.core.model import ApplicationRequest, ApplicationResult, CVAnalysis, JobResult
from src.core.providers.linkedin_mcp_client import LinkedInMCPClient


class LinkedInMCPClientSync:
    """
    Synchronous wrapper for the LinkedInMCPClient.
    Uses a single persistent event loop in a background thread
    and keeps the async client connection open to avoid per-call overhead.
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
        self._client = LinkedInMCPClient()
        self._connected_client = None
        self._connect_lock = threading.Lock()

    def _get_connected_client(self) -> LinkedInMCPClient:
        """Get or create a persistent connected client (lazy init)."""
        if self._connected_client is not None:
            return self._connected_client

        with self._connect_lock:
            if self._connected_client is not None:
                return self._connected_client

            loop = self._get_loop()
            future = asyncio.run_coroutine_threadsafe(self._client.__aenter__(), loop)
            self._connected_client = future.result()
            return self._connected_client

    def _run(self, coro):
        """Run a coroutine on the persistent event loop and wait for the result."""
        loop = self._get_loop()
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result()

    def close(self):
        """Close the persistent connection."""
        if self._connected_client is not None:
            try:
                loop = self._get_loop()
                future = asyncio.run_coroutine_threadsafe(
                    self._client.__aexit__(None, None, None), loop
                )
                future.result(timeout=5)
            except Exception:
                pass
            self._connected_client = None

    def __del__(self):
        self.close()

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
        client = self._get_connected_client()
        return self._run(
            client.search_jobs(
                job_title, location, easy_apply, email, password, limit, trace_id
            )
        )

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
        client = self._get_connected_client()
        return self._run(
            client.search_employees(
                company_linkedin_url, company_name, email, password, limit, trace_id
            )
        )

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
        client = self._get_connected_client()
        return self._run(
            client.send_message(
                employee_profile_url,
                employee_name,
                message,
                email,
                password,
                trace_id,
            )
        )

    def search_employees_batch(
        self,
        companies: List[Dict[str, Any]],
        email: str,
        password: str,
        total_limit: int = None,
        trace_id: str = None,
        exclude_companies: List[str] = None,
        exclude_profile_urls: List[str] = None,
        batch_id: str = None,
    ) -> Dict[str, Any]:
        """Synchronous wrapper for search_employees_batch.

        Returns summary dict. Actual results are in the shared DB keyed by batch_id.
        """
        client = self._get_connected_client()
        return self._run(
            client.search_employees_batch(
                companies,
                email,
                password,
                total_limit,
                trace_id,
                exclude_companies=exclude_companies,
                exclude_profile_urls=exclude_profile_urls,
                batch_id=batch_id,
            )
        )

    def easy_apply_for_jobs(
        self,
        applications: List[ApplicationRequest],
        cv_analysis: Union[CVAnalysis, Dict[str, Any]],
        email: str,
        password: str,
        trace_id: str = None,
    ) -> List[ApplicationResult]:
        """Synchronous wrapper for easy_apply_for_jobs."""
        client = self._get_connected_client()
        return self._run(
            client.easy_apply_for_jobs(
                applications, cv_analysis, email, password, trace_id
            )
        )
