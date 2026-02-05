"""Pytest configuration for backend tests."""
import os


def _set_default_env() -> None:
    """Ensure required settings are available during test collection."""
    defaults = {
        "DATABASE_URL": "postgresql://test:test@localhost:5432/test_db",
        "OPENAI_API_KEY": "test-openai-key",
        "TAVILY_API_KEY": "test-tavily-key",
        "SECRET_KEY": "x" * 32,
        "ENVIRONMENT": "test",
        "FRONTEND_URL": "http://localhost:5173",
    }
    for key, value in defaults.items():
        os.environ.setdefault(key, value)


_set_default_env()
