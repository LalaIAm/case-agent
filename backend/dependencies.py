"""
Dependency injection utilities for FastAPI routes.
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.database import AsyncSessionLocal

# Use current_active_user from backend.auth.users for protected routes
# Example: from backend.auth.users import current_active_user; then Depends(current_active_user)


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
