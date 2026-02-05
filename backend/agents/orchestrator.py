"""
Workflow coordination and execution: handoffs, state transitions, WebSocket broadcasts.
"""
import logging
from typing import Any, Optional, TYPE_CHECKING
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.concrete_agents import AGENT_CLASSES
from backend.agents.state import WorkflowState, WorkflowStateManager

if TYPE_CHECKING:
    from backend.agents.websocket_manager import WebSocketManager

logger = logging.getLogger(__name__)

AGENT_WORKFLOW = ["intake", "research", "document", "strategy", "drafting"]


class AgentOrchestrator:
    """Coordinates agent workflow execution and broadcasts status."""

    def __init__(
        self,
        db: AsyncSession,
        case_id: UUID,
        user_id: UUID,
        websocket_manager: Optional["WebSocketManager"] = None,
    ) -> None:
        self._db = db
        self._case_id = case_id
        self._user_id = user_id
        self._ws = websocket_manager

    async def _broadcast_status(
        self,
        agent_name: str,
        status: str,
        reasoning: Optional[str] = None,
        progress: int = 0,
    ) -> None:
        """Send WebSocket update to case subscribers."""
        if self._ws:
            await self._ws.broadcast_agent_status(
                self._case_id,
                agent_name=agent_name,
                status=status,
                reasoning=reasoning,
                progress=progress,
            )

    async def _broadcast_workflow_state(self, state: WorkflowState) -> None:
        """Broadcast full workflow state to case subscribers."""
        if self._ws:
            await self._ws.broadcast_workflow_update(self._case_id, state)

    async def _should_skip_agent(self, agent_name: str, state: WorkflowState) -> bool:
        """Determine if agent should be skipped based on case/workflow state."""
        if state.workflow_status == "failed":
            return True
        # Optionally skip if already completed (for resumption we run only pending)
        return False

    async def execute_workflow(
        self,
        force_restart: bool = False,
        max_retries: Optional[int] = None,
    ) -> WorkflowState:
        """
        Run workflow: initialize state, iterate AGENT_WORKFLOW, run each agent, broadcast, handle retries.
        Supports resumption from last completed agent unless force_restart is True.
        """
        from backend.config import get_settings
        settings = get_settings()
        retries = max_retries if max_retries is not None else getattr(settings, "AGENT_MAX_RETRIES", 3)

        state_manager = WorkflowStateManager(self._db, self._case_id)
        state = await state_manager.get_state()

        if force_restart:
            state.completed_agents = []
            state.agent_results = {}
            state.workflow_status = "pending"
            state.current_agent = None
            state.error = None

        total = len(AGENT_WORKFLOW)
        for i, agent_name in enumerate(AGENT_WORKFLOW):
            if agent_name in state.completed_agents and not force_restart:
                continue
            if await self._should_skip_agent(agent_name, state):
                continue

            agent_cls = AGENT_CLASSES.get(agent_name)
            if not agent_cls:
                logger.warning("Unknown agent name: %s", agent_name)
                continue

            last_error: Optional[Exception] = None
            for attempt in range(retries):
                try:
                    await self._broadcast_status(agent_name, "running", progress=int((i / total) * 100))
                    agent = agent_cls(self._db, self._case_id, self._user_id)
                    run = await agent.run()
                    await self._db.commit()
                    state.completed_agents.append(agent_name)
                    if run.result:
                        state.agent_results[agent_name] = run.result
                    state.current_agent = None
                    progress = int(((i + 1) / total) * 100)
                    await self._broadcast_status(agent_name, "completed", progress=progress)
                    await self._broadcast_workflow_state(state)
                    break
                except Exception as e:
                    last_error = e
                    await self._db.commit()
                    logger.exception("Agent %s attempt %s failed: %s", agent_name, attempt + 1, e)
                    if attempt == retries - 1:
                        state.workflow_status = "failed"
                        state.error = str(e)
                        await self._broadcast_status(agent_name, "failed", reasoning=str(e))
                        await self._broadcast_workflow_state(state)
                        raise
            else:
                if last_error:
                    raise last_error

        state.workflow_status = "completed"
        await self._broadcast_workflow_state(state)
        return state

    async def execute_single_agent(self, agent_name: str) -> Any:
        """Run a single agent and return its AgentRun or result."""
        agent_cls = AGENT_CLASSES.get(agent_name)
        if not agent_cls:
            raise ValueError(f"Unknown agent: {agent_name}")
        await self._broadcast_status(agent_name, "running")
        agent = agent_cls(self._db, self._case_id, self._user_id)
        try:
            run = await agent.run()
            await self._db.commit()
            await self._broadcast_status(agent_name, "completed", progress=100)
        except Exception:
            await self._db.commit()
            raise
        state = await WorkflowStateManager(self._db, self._case_id).get_state()
        await self._broadcast_workflow_state(state)
        return run

    async def get_workflow_status(self) -> WorkflowState:
        """Return current workflow state."""
        state_manager = WorkflowStateManager(self._db, self._case_id)
        return await state_manager.get_state()