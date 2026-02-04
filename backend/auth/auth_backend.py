"""
JWT authentication backend for FastAPI-Users.
"""
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)

from backend.config import get_settings

settings = get_settings()


def get_jwt_strategy() -> JWTStrategy:
    """Return JWT strategy with SECRET_KEY and 1-hour token lifetime."""
    return JWTStrategy(
        secret=settings.SECRET_KEY,
        lifetime_seconds=3600,
    )


bearer_transport = BearerTransport(tokenUrl="/api/auth/login")

auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)
