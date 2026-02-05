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

    # Rules system
    RULES_SIMILARITY_THRESHOLD: float = Field(default=0.7, description="Minimum similarity for rule matching")
    RULES_MAX_RESULTS: int = Field(default=10, description="Default limit for rule search results")

    # Tavily Search Configuration
    TAVILY_SEARCH_DEPTH: str = Field(
        default="basic",
        description="Default search depth: basic, advanced, fast, ultra-fast",
    )
    TAVILY_MAX_RESULTS: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Default max results per search",
    )
    TAVILY_RATE_LIMIT_RPM: int = Field(
        default=100,
        description="Rate limit requests per minute",
    )
    TAVILY_ENABLE_CACHING: bool = Field(
        default=True,
        description="Enable search result caching",
    )
    TAVILY_CACHE_TTL_SECONDS: int = Field(
        default=3600,
        description="Cache time-to-live in seconds",
    )

    # Agent framework
    AGENT_MAX_RETRIES: int = Field(default=3, description="Max retries for failed agents")
    AGENT_TIMEOUT_SECONDS: int = Field(default=300, description="Timeout for agent execution")
    AGENT_MODEL: str = Field(default="gpt-4-turbo-preview", description="OpenAI model for agents")
    AGENT_TEMPERATURE: float = Field(default=0.7, ge=0.0, le=2.0, description="Temperature for agent responses")
    WEBSOCKET_HEARTBEAT_INTERVAL: int = Field(default=30, description="WebSocket ping interval in seconds")

    # Agent-specific
    INTAKE_MAX_QUESTIONS: int = Field(default=5, ge=1, le=20, description="Max clarifying questions per intake")
    RESEARCH_MAX_RULES: int = Field(default=10, ge=1, le=50, description="Max rules to retrieve per research search")
    DOCUMENT_BATCH_SIZE: int = Field(default=10, ge=1, le=50, description="Documents to process per document agent run")
    AGENT_CONTEXT_WINDOW: int = Field(default=12000, ge=1000, le=128000, description="Max characters for OpenAI context")


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance (singleton pattern)."""
    return Settings()
