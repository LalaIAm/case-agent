"""
Alembic environment configuration for async migrations with pgvector support.
"""
import asyncio
import os
import sys

from alembic import context
from sqlalchemy import pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Add project root to path so backend imports work when running from backend/
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.database.models import Base

config = context.config
target_metadata = Base.metadata


def get_url() -> str:
    """Get database URL from environment (migrations require only DATABASE_URL, not full app settings)."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is required for Alembic migrations. "
            "Set it in the environment or in alembic.ini under [alembic] sqlalchemy.url."
        )
    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode: generate SQL script only."""
    url = config.get_main_option("sqlalchemy.url") or get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with the given connection."""
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine and enable pgvector."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = config.get_main_option("sqlalchemy.url") or get_url()
    # Ensure async driver: replace postgresql:// with postgresql+asyncpg://
    url = configuration["sqlalchemy.url"]
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        configuration["sqlalchemy.url"] = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        # Enable pgvector extension before running migrations
        await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await connection.commit()
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (async)."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
