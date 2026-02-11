"""Session storage backed by SQLite via AgentDB."""

import time
import uuid
from typing import Any, Dict, List, Optional

from loguru import logger

from src.core.db.agent_db import AgentDB

# Periodic cleanup: at most once every 5 minutes
_last_cleanup: float = 0.0
_CLEANUP_INTERVAL = 300.0


class SessionStore:
    """SQLite-backed session store with TTL expiration."""

    def __init__(self, agent_db: AgentDB, ttl: int = 3600):
        self._db = agent_db
        self._ttl = ttl

    def create(
        self,
        clustered: Dict[str, List[Dict]],
        trace_id: str = "",
    ) -> str:
        session_id = str(uuid.uuid4())

        # Only store clustered (employees can be reconstructed from it)
        data = {
            "clustered": clustered,
            "trace_id": trace_id,
        }

        self._db.save_session(session_id, data, ttl=self._ttl)
        self._maybe_cleanup()

        total = sum(len(v) for v in clustered.values())
        logger.debug(
            "Session created",
            session_id=session_id,
            employees=total,
        )
        return session_id

    def _maybe_cleanup(self) -> None:
        """Run cleanup at most once per interval to avoid O(n^2) scans."""
        global _last_cleanup
        now = time.time()
        if now - _last_cleanup > _CLEANUP_INTERVAL:
            _last_cleanup = now
            self._db.cleanup_expired_sessions()

    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        data = self._db.get_session(session_id)
        if not data:
            logger.debug("Session not found or expired", session_id=session_id)
            return None
        return data

    def delete(self, session_id: str) -> bool:
        deleted = self._db.delete_session(session_id)
        if deleted:
            logger.debug("Session deleted", session_id=session_id)
        return deleted

    def clear(self) -> None:
        self._db.cleanup_expired_sessions()

    def count(self) -> int:
        return 0
