"""
Database utility functions for initialization, health checks, and pgvector setup.
"""
from sqlalchemy import text

from backend.database.engine import engine
from backend.database.models import Base


async def init_db() -> None:
    """Initialize database: create tables if they do not exist (for testing)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def check_db_connection() -> bool:
    """Verify database connectivity. Returns True if connection succeeds."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def enable_pgvector() -> None:
    """Ensure pgvector extension is enabled in the database."""
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))


async def create_vector_indexes() -> None:
    """Create vector similarity indexes if they do not exist."""
    async with engine.begin() as conn:
        await conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_memory_blocks_embedding
                ON public.memory_blocks
                USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)
                """
            )
        )
        await conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS ix_documents_embedding
                ON public.documents
                USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)
                """
            )
        )