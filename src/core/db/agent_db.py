"""SQLAlchemy-based persistence for sessions, job applications, messages, and daily quotas."""

import json
import time
from datetime import date
from typing import Any, Dict, Optional, Union

from sqlalchemy import Engine

from src.core.db.engine import create_db_engine, create_session_factory
from src.core.db.models import (
    DailyQuota,
    JobApplication,
    MessageSent,
    SearchResult,
    SessionModel,
)


class AgentDB:
    """Thread-safe database layer for agent state persistence."""

    def __init__(self, engine_or_url: Union[Engine, str]):
        if isinstance(engine_or_url, str):
            self._engine = create_db_engine(engine_or_url)
        else:
            self._engine = engine_or_url
        self._session_factory = create_session_factory(self._engine)

    # --- Sessions ---

    def save_session(self, session_id: str, data: Dict[str, Any], ttl: int = 3600):
        now = time.time()
        with self._session_factory() as session:
            session.merge(
                SessionModel(
                    session_id=session_id,
                    data=json.dumps(data, default=str),
                    created_at=now,
                    expires_at=now + ttl,
                )
            )
            session.commit()

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._session_factory() as session:
            row = session.get(SessionModel, session_id)
            if not row:
                return None
            if time.time() > row.expires_at:
                session.delete(row)
                session.commit()
                return None
            return json.loads(row.data)

    def delete_session(self, session_id: str) -> bool:
        with self._session_factory() as session:
            row = session.get(SessionModel, session_id)
            if not row:
                return False
            session.delete(row)
            session.commit()
            return True

    def cleanup_expired_sessions(self) -> int:
        with self._session_factory() as session:
            result = (
                session.query(SessionModel)
                .filter(SessionModel.expires_at < time.time())
                .delete()
            )
            session.commit()
            return result

    # --- Job Applications ---

    def record_application(self, job_id: str, success: bool, error: str = None):
        with self._session_factory() as session:
            session.merge(
                JobApplication(
                    job_id=job_id,
                    applied_at=time.time(),
                    success=int(success),
                    error=error,
                )
            )
            session.commit()

    def was_already_applied(self, job_id: str) -> bool:
        with self._session_factory() as session:
            row = (
                session.query(JobApplication)
                .filter(
                    JobApplication.job_id == job_id,
                    JobApplication.success == 1,
                )
                .first()
            )
            return row is not None

    def get_applied_job_ids(self) -> set:
        """Return all successfully applied job IDs."""
        with self._session_factory() as session:
            rows = (
                session.query(JobApplication.job_id)
                .filter(JobApplication.success == 1)
                .all()
            )
            return {row[0] for row in rows}

    # --- Messages ---

    def record_message(
        self,
        employee_profile_url: str,
        employee_name: str,
        success: bool,
        method: str = None,
        error: str = None,
    ):
        with self._session_factory() as session:
            session.merge(
                MessageSent(
                    employee_profile_url=employee_profile_url,
                    employee_name=employee_name,
                    sent_at=time.time(),
                    success=int(success),
                    method=method,
                    error=error,
                )
            )
            session.commit()

    def was_already_messaged(self, employee_profile_url: str) -> bool:
        with self._session_factory() as session:
            row = (
                session.query(MessageSent)
                .filter(
                    MessageSent.employee_profile_url == employee_profile_url,
                    MessageSent.success == 1,
                )
                .first()
            )
            return row is not None

    def get_messaged_profile_urls(self) -> set:
        """Return all successfully messaged profile URLs."""
        with self._session_factory() as session:
            rows = (
                session.query(MessageSent.employee_profile_url)
                .filter(MessageSent.success == 1)
                .all()
            )
            return {row[0] for row in rows}

    # --- Daily Quota ---

    def get_daily_quota(self) -> int:
        today = date.today().isoformat()
        with self._session_factory() as session:
            row = session.get(DailyQuota, today)
            return row.count if row else 0

    def increment_daily_quota(self) -> int:
        today = date.today().isoformat()
        with self._session_factory() as session:
            row = session.get(DailyQuota, today)
            if row:
                row.count += 1
            else:
                row = DailyQuota(date=today, count=1)
                session.add(row)
            session.commit()
            return row.count

    # --- Search Results ---

    def save_search_results(
        self,
        batch_id: str,
        company_name: str,
        company_linkedin_url: str,
        employees: list,
    ) -> None:
        """Bulk insert employees for a company into search_results."""
        with self._session_factory() as session:
            for emp in employees:
                session.add(
                    SearchResult(
                        batch_id=batch_id,
                        company_name=company_name,
                        company_linkedin_url=company_linkedin_url,
                        employee_name=emp.get("name", ""),
                        employee_title=emp.get("title", ""),
                        employee_profile_url=emp.get("profile_url", ""),
                        created_at=time.time(),
                    )
                )
            session.commit()

    def get_search_results(self, batch_id: str) -> list:
        """Read all employees for a batch_id, returned as list of dicts."""
        with self._session_factory() as session:
            rows = (
                session.query(SearchResult)
                .filter(SearchResult.batch_id == batch_id)
                .all()
            )
            return [
                {
                    "company_name": r.company_name,
                    "company_linkedin_url": r.company_linkedin_url,
                    "name": r.employee_name,
                    "title": r.employee_title,
                    "profile_url": r.employee_profile_url,
                }
                for r in rows
            ]

    def delete_search_results(self, batch_id: str) -> int:
        """Delete all search results for a batch_id."""
        with self._session_factory() as session:
            count = (
                session.query(SearchResult)
                .filter(SearchResult.batch_id == batch_id)
                .delete()
            )
            session.commit()
            return count
