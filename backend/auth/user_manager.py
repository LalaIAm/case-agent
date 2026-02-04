"""
FastAPI-Users user manager with JWT-backed authentication.
"""
import logging
from typing import Optional, Union
from uuid import UUID

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, UUIDIDMixin, exceptions
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.database.models import User
from backend.database.schemas import UserCreate
from backend.dependencies import get_db_session

try:
    from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
except ImportError:
    from fastapi_users.db.sqlalchemy import SQLAlchemyUserDatabase  # type: ignore

logger = logging.getLogger(__name__)


async def get_user_db(session: AsyncSession = Depends(get_db_session)):
    """Provide SQLAlchemy user database adapter for FastAPI-Users."""
    yield SQLAlchemyUserDatabase(session, User)


class UserManager(UUIDIDMixin, BaseUserManager[User, UUID]):
    """User manager with password validation and lifecycle hooks."""

    @property
    def reset_password_token_secret(self) -> str:
        settings = get_settings()
        return settings.RESET_PASSWORD_TOKEN_SECRET or settings.SECRET_KEY

    @property
    def verification_token_secret(self) -> str:
        settings = get_settings()
        return settings.VERIFICATION_TOKEN_SECRET or settings.SECRET_KEY

    async def validate_password(
        self, password: str, user: Union[UserCreate, User]
    ) -> None:
        """Enforce password rules (min length 8, per backend/database/schemas.py)."""
        if len(password) < 8:
            raise exceptions.InvalidPasswordException(
                reason="Password must be at least 8 characters"
            )

    async def on_after_register(self, user: User, request: Optional[Request] = None) -> None:
        """Post-registration: logging and welcome email placeholder."""
        logger.info("User %s registered. Welcome email placeholder.", user.id)

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ) -> None:
        """Post forgot-password: password reset flow placeholder."""
        logger.info("Password reset requested for %s. Token placeholder.", user.email)


async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    """Dependency that yields UserManager instance."""
    yield UserManager(user_db)
