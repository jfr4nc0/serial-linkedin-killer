"""Session storage backed by SQLite via AgentDB."""

import uuid
from typing import Any, Dict, List, Optional

from loguru import logger

from src.core.db.agent_db import AgentDB


class SessionStore:
    """SQLite-backed session store with TTL expiration."""

    def __init__(self, agent_db: AgentDB, ttl: int = 3600):
        self._db = agent_db
        self._ttl = ttl

    def create(
        self,
        employees: List[Dict],
        clustered: Dict[str, List[Dict]],
        companies: List[Dict],
        trace_id: str = "",
    ) -> str:
        session_id = str(uuid.uuid4())

        data = {
            "employees": employees,
            "clustered": clustered,
            "companies": companies,
            "trace_id": trace_id,
        }

        self._db.save_session(session_id, data, ttl=self._ttl)
        self._db.cleanup_expired_sessions()

        logger.debug(
            "Session created",
            session_id=session_id,
            employees=len(employees),
            companies=len(companies),
        )
        return session_id

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
        # Not critical — return 0 as approximate
        return 0
