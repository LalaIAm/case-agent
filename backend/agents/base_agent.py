"""
Abstract base class for all agents: OpenAI integration, AgentRun logging, error handling, timeout.
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models import AgentRun
from backend.memory.memory_manager import MemoryManager

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all workflow agents."""

    def __init__(
        self,
        db: AsyncSession,
        case_id: UUID,
        user_id: UUID,
    ) -> None:
        self._db = db
        self._case_id = case_id
        self._user_id = user_id

    @property
    @abstractmethod
    def agent_name(self) -> str:
        """Subclasses must override with the agent identifier (e.g. 'intake', 'research')."""
        ...

    def _get_openai_client(self) -> AsyncOpenAI:
        """Return configured OpenAI client from backend.config."""
        from backend.config import get_settings
        settings = get_settings()
        return AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    def _get_memory_manager(self) -> MemoryManager:
        """Return MemoryManager instance for this session."""
        return MemoryManager(self._db)

    async def _create_agent_run(self) -> AgentRun:
        """Insert new AgentRun record with status='running'."""
        run = AgentRun(
            case_id=self._case_id,
            agent_name=self.agent_name,
            status="running",
        )
        self._db.add(run)
        await self._db.flush()
        await self._db.refresh(run)
        return run

    async def _update_agent_run(
        self,
        run_id: UUID,
        *,
        status: Optional[str] = None,
        reasoning: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        completed_at: Optional[datetime] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Update AgentRun record with status, reasoning, result, completed_at, error_message."""
        result_query = await self._db.execute(select(AgentRun).where(AgentRun.id == run_id))
        run = result_query.scalar_one_or_none()
        if not run:
            return
        if status is not None:
            run.status = status
        if reasoning is not None:
            run.reasoning = reasoning
        if result is not None:
            run.result = result
        if completed_at is not None:
            run.completed_at = completed_at
        if error_message is not None:
            run.error_message = error_message
        await self._db.flush()

    async def _log_reasoning(self, run_id: UUID, reasoning: str) -> None:
        """Update reasoning field in real-time."""
        await self._update_agent_run(run_id, reasoning=reasoning)

    @abstractmethod
    async def execute(self, agent_run_id: UUID) -> Dict[str, Any]:
        """
        Agent-specific logic. Subclasses implement this.
        Receives agent_run_id for logging; returns result dict to store on AgentRun.
        """
        ...

    async def run(self) -> AgentRun:
        """
        Create AgentRun, call execute() with timeout and try/except, update with success/failure, return AgentRun.
        """
        from backend.config import get_settings
        settings = get_settings()
        timeout_sec = getattr(settings, "AGENT_TIMEOUT_SECONDS", 300)

        run = await self._create_agent_run()
        try:
            result = await asyncio.wait_for(self.execute(run.id), timeout=timeout_sec)
            await self._update_agent_run(
                run.id,
                status="completed",
                result=result,
                completed_at=datetime.now(timezone.utc),
            )
            await self._db.refresh(run)
            return run
        except asyncio.TimeoutError as e:
            logger.warning("Agent %s timed out after %s seconds", self.agent_name, timeout_sec)
            await self._update_agent_run(
                run.id,
                status="failed",
                error_message=f"Timeout after {timeout_sec}s",
                completed_at=datetime.now(timezone.utc),
            )
            await self._db.refresh(run)
            raise
        except Exception as e:
            await self._update_agent_run(
                run.id,
                status="failed",
                error_message=str(e),
                completed_at=datetime.now(timezone.utc),
            )
            await self._db.refresh(run)
            raise
