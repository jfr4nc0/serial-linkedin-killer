"""SQLAlchemy engine and session factory utilities."""

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from src.core.db.models import Base


def create_db_engine(url: str) -> Engine:
    """Create a SQLAlchemy engine from a connection URL.

    Automatically configures SQLite-specific settings (WAL, busy_timeout)
    when the URL targets SQLite.
    """
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}

    # Configure connection pooling
    pool_kwargs = {}
    if not url.startswith("sqlite"):
        # Full connection pool for non-SQLite databases
        pool_kwargs = {
            "pool_size": 20,
            "max_overflow": 40,
            "pool_pre_ping": True,  # Verify connections before use
            "pool_recycle": 3600,  # Recycle connections after 1 hour
        }
    else:
        # SQLite uses StaticPool for thread safety with check_same_thread=False
        pool_kwargs = {
            "pool_pre_ping": True,
        }

    engine = create_engine(url, connect_args=connect_args, **pool_kwargs)

    # SQLite-specific PRAGMAs
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _set_sqlite_pragmas(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

    Base.metadata.create_all(engine)
    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create a sessionmaker bound to the given engine."""
    return sessionmaker(bind=engine)
