"""SQLAlchemy-based company dataset storage for efficient querying of large datasets."""

from typing import Dict, List, Union

import pandas as pd
from loguru import logger
from sqlalchemy import Engine, func, select

from src.core.db.engine import create_db_engine, create_session_factory
from src.core.db.models import Company

_FILTERABLE_COLUMNS = {
    "industry": Company.industry,
    "country": Company.country,
    "size": Company.size,
}


class CompanyDB:
    """SQLAlchemy wrapper for querying the company dataset."""

    def __init__(self, engine_or_url: Union[Engine, str]):
        if isinstance(engine_or_url, str):
            self._engine = create_db_engine(engine_or_url)
        else:
            self._engine = engine_or_url
        self._session_factory = create_session_factory(self._engine)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def import_csv(
        self,
        csv_path: str,
        batch_size: int = 10_000,
        on_progress: callable = None,
    ) -> int:
        """Import a CSV file into the database in chunks.

        Uses pandas to_sql for efficient bulk loading.
        """
        # Drop and recreate table
        Company.__table__.drop(self._engine, checkfirst=True)
        Company.__table__.create(self._engine, checkfirst=True)

        total = 0
        reader = pd.read_csv(
            csv_path,
            dtype=str,
            on_bad_lines="skip",
            chunksize=batch_size,
        )

        for chunk in reader:
            chunk = chunk.fillna("")
            chunk.to_sql(
                "companies",
                self._engine,
                if_exists="append",
                index=False,
            )
            total += len(chunk)

            if on_progress:
                on_progress(total)

        logger.info("CSV import complete", rows=total)
        return total

    def get_unique_values(self, column: str) -> List[str]:
        """Return sorted distinct non-empty values for a column."""
        if column not in _FILTERABLE_COLUMNS:
            raise ValueError(f"Column '{column}' is not filterable")

        col = _FILTERABLE_COLUMNS[column]
        with self._session_factory() as session:
            rows = session.query(col).filter(col != "").distinct().order_by(col).all()
            return [row[0] for row in rows]

    def get_total_count(self) -> int:
        """Return total number of companies."""
        with self._session_factory() as session:
            return session.query(func.count(Company.id)).scalar() or 0

    def filter_companies(self, filters: Dict[str, List[str]]) -> List[dict]:
        """Filter companies by column values (case-insensitive)."""
        with self._session_factory() as session:
            query = session.query(Company)

            for column, values in filters.items():
                if not values or column not in _FILTERABLE_COLUMNS:
                    continue
                col = _FILTERABLE_COLUMNS[column]
                lower_values = [v.lower().strip() for v in values]
                query = query.filter(func.lower(func.trim(col)).in_(lower_values))

            rows = query.all()
            return [
                {c.name: getattr(row, c.name) for c in Company.__table__.columns}
                for row in rows
            ]

    def close(self):
        """Dispose the engine."""
        self._engine.dispose()
