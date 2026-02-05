"""Alembic migration environment configuration.

Supports multiple database providers (SQLite, PostgreSQL) with
automatic dialect detection and SQLite batch mode for ALTER TABLE.
"""

from logging.config import fileConfig

from sqlalchemy import pool

from alembic import context

# Import models and config
from src.config.config_loader import load_config
from src.core.db.models import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
alembic_config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if alembic_config.config_file_name is not None:
    fileConfig(alembic_config.config_file_name)

# Load application config to get database URL
app_config = load_config()

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata


def get_url() -> str:
    """Get database URL from application config."""
    return app_config.db.url


def is_sqlite(url: str) -> bool:
    """Check if the database URL is for SQLite."""
    return url.startswith("sqlite")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=is_sqlite(url),  # Required for SQLite ALTER TABLE
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    from sqlalchemy import create_engine

    url = get_url()

    # Configure engine based on database type
    if is_sqlite(url):
        # SQLite configuration
        connectable = create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=pool.StaticPool,
        )
    else:
        # PostgreSQL/other databases
        connectable = create_engine(
            url,
            poolclass=pool.NullPool,
        )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=is_sqlite(url),  # Required for SQLite ALTER TABLE
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
