"""In-memory session storage for two-phase outreach workflow."""

import threading
import time
import uuid
from typing import Any, Dict, List, Optional

from loguru import logger


class SessionStore:
    """Thread-safe in-memory session store with TTL expiration."""

    def __init__(self, ttl: int = 3600):
        """Initialize session store.

        Args:
            ttl: Session time-to-live in seconds (default: 1 hour).
        """
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._ttl = ttl

    def create(
        self,
        employees: List[Dict],
        clustered: Dict[str, List[Dict]],
        companies: List[Dict],
        trace_id: str = "",
    ) -> str:
        """Create a new session with search results.

        Args:
            employees: All employees found.
            clustered: Employees grouped by role category.
            companies: Companies that were searched.
            trace_id: Trace ID for logging correlation.

        Returns:
            New session_id.
        """
        session_id = str(uuid.uuid4())
        now = time.time()

        with self._lock:
            # Clean up expired sessions opportunistically
            self._cleanup_expired_locked()

            self._sessions[session_id] = {
                "employees": employees,
                "clustered": clustered,
                "companies": companies,
                "trace_id": trace_id,
                "created_at": now,
                "expires_at": now + self._ttl,
            }

        logger.debug(
            "Session created",
            session_id=session_id,
            employees=len(employees),
            companies=len(companies),
        )
        return session_id

    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data by ID.

        Args:
            session_id: Session identifier.

        Returns:
            Session data dict or None if not found/expired.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return None

            # Check expiration
            if time.time() > session["expires_at"]:
                del self._sessions[session_id]
                logger.debug("Session expired", session_id=session_id)
                return None

            return session

    def delete(self, session_id: str) -> bool:
        """Delete a session.

        Args:
            session_id: Session identifier.

        Returns:
            True if session was deleted, False if not found.
        """
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                logger.debug("Session deleted", session_id=session_id)
                return True
            return False

    def _cleanup_expired_locked(self) -> int:
        """Remove expired sessions. Must be called with lock held.

        Returns:
            Number of sessions removed.
        """
        now = time.time()
        expired = [
            sid for sid, data in self._sessions.items() if now > data["expires_at"]
        ]
        for sid in expired:
            del self._sessions[sid]

        if expired:
            logger.debug("Cleaned up expired sessions", count=len(expired))

        return len(expired)

    def clear(self) -> None:
        """Remove all sessions."""
        with self._lock:
            self._sessions.clear()

    def count(self) -> int:
        """Return number of active sessions."""
        with self._lock:
            return len(self._sessions)
