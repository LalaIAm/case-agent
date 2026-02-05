"""
State management for agent workflow: AgentState enum, WorkflowState, WorkflowStateManager.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models import AgentRun


class AgentState(str, Enum):
    """Agent run status values."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowState:
    """Current state of a case workflow."""

    case_id: UUID
    current_agent: Optional[str] = None
    completed_agents: List[str] = field(default_factory=list)
    agent_results: Dict[str, Any] = field(default_factory=dict)
    workflow_status: str = "pending"
    error: Optional[str] = None


class WorkflowStateManager:
    """Manages workflow state derived from AgentRun records."""

    def __init__(self, db: AsyncSession, case_id: UUID) -> None:
        self._db = db
        self._case_id = case_id

    async def get_state(self) -> WorkflowState:
        """Retrieve current workflow state from AgentRun records."""
        result = await self._db.execute(
            select(AgentRun)
            .where(AgentRun.case_id == self._case_id)
            .order_by(AgentRun.started_at.asc())
        )
        runs = list(result.scalars().unique().all())
        completed: List[str] = []
        agent_results: Dict[str, Any] = {}
        current_agent: Optional[str] = None
        workflow_status = "pending"
        error: Optional[str] = None

        for run in runs:
            if run.status == "running":
                current_agent = run.agent_name
                workflow_status = "running"
                break
            if run.status == "completed":
                completed.append(run.agent_name)
                if run.result:
                    agent_results[run.agent_name] = run.result
            elif run.status == "failed":
                workflow_status = "failed"
                error = run.error_message or "Agent failed"
                break

        # Only set "completed" when all workflow agents have completed successfully
        if workflow_status == "pending":
            from backend.agents.orchestrator import AGENT_WORKFLOW

            all_workflow_completed = all(
                agent_name in completed for agent_name in AGENT_WORKFLOW
            )
            if all_workflow_completed:
                workflow_status = "completed"

        return WorkflowState(
            case_id=self._case_id,
            current_agent=current_agent,
            completed_agents=completed,
            agent_results=agent_results,
            workflow_status=workflow_status,
            error=error,
        )

    async def update_state(self, state: WorkflowState) -> None:
        """Update workflow state (persisted via AgentRun records; this is for in-memory sync)."""
        # State is derived from AgentRun; no separate table. This method can be used
        # to drive updates that eventually write AgentRun rows elsewhere.
        pass

    async def mark_agent_complete(self, agent_name: str, result: Optional[Dict[str, Any]] = None) -> None:
        """Record agent completion (actual persistence is done in BaseAgent.run)."""
        # Completion is recorded when AgentRun is updated in BaseAgent. This method
        # can be used to ensure state consistency after an external update.
        pass

    async def get_agent_result(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve specific agent's result from latest completed run."""
        result = await self._db.execute(
            select(AgentRun)
            .where(
                AgentRun.case_id == self._case_id,
                AgentRun.agent_name == agent_name,
                AgentRun.status == "completed",
            )
            .order_by(AgentRun.completed_at.desc())
            .limit(1)
        )
        run = result.scalar_one_or_none()
        return run.result if run else None

    async def is_workflow_complete(self) -> bool:
        """Check if all agents in the workflow have finished (completed or failed)."""
        state = await self.get_state()
        return state.workflow_status in ("completed", "failed")
