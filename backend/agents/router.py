"""
REST API endpoints for agent execution and status.
"""
import asyncio
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.users import current_active_user
from backend.database.models import AgentRun, Case, User
from backend.database.schemas import (
    AgentExecuteRequest,
    AgentRunRead,
    AgentStatusResponse,
    WorkflowStateResponse,
)
from backend.dependencies import get_db_session
from backend.memory.utils import validate_case_ownership

from backend.agents.state import WorkflowStateManager
from .orchestrator import AGENT_WORKFLOW, AgentOrchestrator
from .tasks import execute_agent_background, execute_workflow_background
from .utils import calculate_workflow_progress

router = APIRouter(prefix="/agents", tags=["agents"])


from backend.agents.socketio_manager import socketio_manager as _ws_manager


def _get_websocket_manager():
    """Return singleton Socket.IO manager for agent status broadcasts."""
    return _ws_manager


@router.post("/execute")
async def execute_agents(
    body: AgentExecuteRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
) -> Any:
    """
    Execute full workflow or single agent. Validates case ownership.
    If agent_name is provided, run that agent only; otherwise run full workflow.
    Long-running execution is scheduled as a background task.
    """
    if not await validate_case_ownership(db, body.case_id, user.id):
        raise HTTPException(status_code=403, detail="Not authorized to run agents for this case")
    ws = _get_websocket_manager()
    if body.agent_name is not None:
        coro = execute_agent_background(body.case_id, user.id, body.agent_name, ws)
        background_tasks.add_task(asyncio.create_task, coro)
        return {"status": "accepted", "message": f"Agent {body.agent_name} started", "case_id": str(body.case_id)}
    coro = execute_workflow_background(body.case_id, user.id, ws, body.force_restart)
    background_tasks.add_task(asyncio.create_task, coro)
    return {"status": "accepted", "message": "Workflow started", "case_id": str(body.case_id)}


@router.get("/status/{case_id}", response_model=AgentStatusResponse)
async def get_agent_status(
    case_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
) -> Any:
    """Return current workflow state and all AgentRun records for the case with progress percentage."""
    if not await validate_case_ownership(db, case_id, user.id):
        raise HTTPException(status_code=403, detail="Not authorized to access this case")
    state_manager = WorkflowStateManager(db, case_id)
    state = await state_manager.get_state()
    result = await db.execute(
        select(AgentRun).where(AgentRun.case_id == case_id).order_by(AgentRun.started_at.desc())
    )
    runs = list(result.scalars().unique().all())
    progress = calculate_workflow_progress(runs)
    return AgentStatusResponse(
        case_id=case_id,
        current_agent=state.current_agent,
        workflow_status=state.workflow_status,
        progress_percentage=progress,
        agent_runs=[AgentRunRead.model_validate(r) for r in runs],
    )


@router.get("/runs/{run_id}", response_model=AgentRunRead)
async def get_agent_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
) -> Any:
    """Retrieve a specific AgentRun by ID. User must own the case."""
    result = await db.execute(
        select(AgentRun).where(AgentRun.id == run_id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Agent run not found")
    if not await validate_case_ownership(db, run.case_id, user.id):
        raise HTTPException(status_code=403, detail="Not authorized to access this run")
    return run


@router.get("/cases/{case_id}/runs", response_model=List[AgentRunRead])
async def list_agent_runs(
    case_id: UUID,
    agent_name: Optional[str] = Query(None, description="Filter by agent name"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
) -> Any:
    """List AgentRun records for a case with optional filters and pagination."""
    if not await validate_case_ownership(db, case_id, user.id):
        raise HTTPException(status_code=403, detail="Not authorized to access this case")
    stmt = select(AgentRun).where(AgentRun.case_id == case_id)
    if agent_name is not None:
        stmt = stmt.where(AgentRun.agent_name == agent_name)
    if status is not None:
        stmt = stmt.where(AgentRun.status == status)
    stmt = stmt.order_by(AgentRun.started_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    runs = list(result.scalars().unique().all())
    return [AgentRunRead.model_validate(r) for r in runs]


@router.get("/workflow/{case_id}", response_model=WorkflowStateResponse)
async def get_workflow_status(
    case_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
) -> Any:
    """Return workflow state: completed_agents, pending_agents, current_agent, overall_status."""
    if not await validate_case_ownership(db, case_id, user.id):
        raise HTTPException(status_code=403, detail="Not authorized to access this case")
    orchestrator = AgentOrchestrator(db, case_id, user.id)
    state = await orchestrator.get_workflow_status()
    completed = set(state.completed_agents)
    pending = [a for a in AGENT_WORKFLOW if a not in completed]
    return WorkflowStateResponse(
        case_id=case_id,
        completed_agents=state.completed_agents,
        pending_agents=pending,
        current_agent=state.current_agent,
        overall_status=state.workflow_status,
    )
