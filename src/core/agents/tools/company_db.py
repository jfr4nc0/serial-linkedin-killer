"""SQLite-based company dataset storage for efficient querying of large datasets."""

import sqlite3
from typing import Dict, List

import pandas as pd
from loguru import logger

_FILTERABLE_COLUMNS = ("industry", "country", "size")

_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
    id TEXT,
    name TEXT,
    industry TEXT,
    country TEXT,
    locality TEXT,
    region TEXT,
    size TEXT,
    linkedin_url TEXT,
    website TEXT,
    founded TEXT
)
"""


class CompanyDB:
    """SQLite wrapper for querying the company dataset."""

    def __init__(self, db_path: str):
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row

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
        """Import a CSV file into SQLite in chunks.

        Args:
            csv_path: Path to the CSV file.
            batch_size: Rows per chunk.
            on_progress: Optional callback(rows_imported) called per chunk.

        Returns:
            Total rows imported.
        """
        cur = self._conn.cursor()

        # Drop and recreate for a clean import
        cur.execute("DROP TABLE IF EXISTS companies")
        cur.execute(_TABLE_SCHEMA)
        self._conn.commit()

        total = 0
        reader = pd.read_csv(
            csv_path,
            dtype=str,
            on_bad_lines="skip",
            chunksize=batch_size,
        )

        for chunk in reader:
            chunk = chunk.fillna("")
            records = chunk.to_records(index=False)
            columns = list(chunk.columns)
            placeholders = ", ".join(["?"] * len(columns))
            col_names = ", ".join(columns)

            cur.executemany(
                f"INSERT INTO companies ({col_names}) VALUES ({placeholders})",
                [tuple(row) for row in records],
            )
            total += len(chunk)

            if on_progress:
                on_progress(total)

        # Create indexes on filterable columns
        for col in _FILTERABLE_COLUMNS:
            cur.execute(f"CREATE INDEX IF NOT EXISTS idx_{col} ON companies ({col})")

        self._conn.commit()
        logger.info("CSV import complete", rows=total, db_path=self._db_path)
        return total

    def get_unique_values(self, column: str) -> List[str]:
        """Return sorted distinct non-empty values for a column."""
        if column not in _FILTERABLE_COLUMNS:
            raise ValueError(f"Column '{column}' is not filterable")

        cur = self._conn.execute(
            f"SELECT DISTINCT {column} FROM companies "
            f"WHERE {column} != '' ORDER BY {column}"
        )
        return [row[0] for row in cur.fetchall()]

    def get_total_count(self) -> int:
        """Return total number of companies."""
        cur = self._conn.execute("SELECT COUNT(*) FROM companies")
        return cur.fetchone()[0]

    def filter_companies(self, filters: Dict[str, List[str]]) -> List[dict]:
        """Filter companies by column values (case-insensitive).

        Args:
            filters: Mapping of column name to accepted values.
                     Empty list means no filter on that column.

        Returns:
            List of company dicts matching all filters.
        """
        clauses = []
        params = []

        for column, values in filters.items():
            if not values or column not in _FILTERABLE_COLUMNS:
                continue
            placeholders = ", ".join(["?"] * len(values))
            clauses.append(f"LOWER(TRIM({column})) IN ({placeholders})")
            params.extend(v.lower().strip() for v in values)

        query = "SELECT * FROM companies"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)

        cur = self._conn.execute(query, params)
        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]

    def close(self):
        """Close the database connection."""
        self._conn.close()
