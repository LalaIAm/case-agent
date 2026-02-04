"""
Dependency injection utilities for FastAPI routes.
"""
from backend.config import get_settings


def get_db_session():
    """
    Placeholder: Database session dependency.
    To be implemented in Phase 2 with async SQLAlchemy session.
    """
    raise NotImplementedError("Database session will be implemented in Phase 2")


def get_current_user():
    """
    Placeholder: Current authenticated user dependency.
    To be implemented in Phase 3 with FastAPI-Users.
    """
    raise NotImplementedError("Current user dependency will be implemented in Phase 3")
