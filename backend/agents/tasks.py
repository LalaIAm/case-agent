"""
Background task execution for agent workflow and single-agent runs.
"""
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import AsyncSessionLocal
from backend.agents.orchestrator import AgentOrchestrator

logger = logging.getLogger(__name__)


async def execute_workflow_background(
    case_id: UUID,
    user_id: UUID,
    websocket_manager=None,
    force_restart: bool = False,
) -> None:
    """
    Create a new database session, run full workflow via AgentOrchestrator, close session.
    """
    async with AsyncSessionLocal() as session:
        try:
            orchestrator = AgentOrchestrator(
                db=session,
                case_id=case_id,
                user_id=user_id,
                websocket_manager=websocket_manager,
            )
            await orchestrator.execute_workflow(force_restart=force_restart)
            await session.commit()
        except Exception as e:
            logger.exception("Background workflow failed for case_id=%s: %s", case_id, e)
            await session.rollback()
            raise
        finally:
            await session.close()


async def execute_agent_background(
    case_id: UUID,
    user_id: UUID,
    agent_name: str,
    websocket_manager=None,
) -> None:
    """
    Create a new database session, run single agent via AgentOrchestrator, close session.
    """
    async with AsyncSessionLocal() as session:
        try:
            orchestrator = AgentOrchestrator(
                db=session,
                case_id=case_id,
                user_id=user_id,
                websocket_manager=websocket_manager,
            )
            await orchestrator.execute_single_agent(agent_name)
            await session.commit()
        except Exception as e:
            logger.exception(
                "Background agent %s failed for case_id=%s: %s",
                agent_name,
                case_id,
                e,
            )
            await session.rollback()
            raise
        finally:
            await session.close()
