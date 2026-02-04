"""
Dependency injection utilities for FastAPI routes.
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.database import AsyncSessionLocal


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async database session with automatic commit/rollback."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_current_user():
    """
    Placeholder: Current authenticated user dependency.
    To be implemented in Phase 3 with FastAPI-Users.
    """
    raise NotImplementedError("Current user dependency will be implemented in Phase 3")
