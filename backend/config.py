"""
Application settings management using Pydantic BaseSettings.
"""
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str = Field(..., description="PostgreSQL connection string")
    OPENAI_API_KEY: str = Field(..., description="OpenAI API key for agents and embeddings")
    TAVILY_API_KEY: str = Field(..., description="Tavily Search API key for research agent")
    SECRET_KEY: str = Field(..., min_length=32, description="Secret key for JWT signing")
    RESET_PASSWORD_TOKEN_SECRET: Optional[str] = Field(
        default=None,
        description="Secret for password-reset tokens; defaults to SECRET_KEY if unset",
    )
    VERIFICATION_TOKEN_SECRET: Optional[str] = Field(
        default=None,
        description="Secret for email verification tokens; defaults to SECRET_KEY if unset",
    )
    FRONTEND_URL: str = Field(default="http://localhost:5173", description="Frontend origin(s) for CORS")
    ENVIRONMENT: str = Field(default="development", description="Environment: development, staging, production")


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance (singleton pattern)."""
    return Settings()
