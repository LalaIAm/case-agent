"""
REST and SSE endpoints for the conversational case advisor.
"""
import asyncio
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from backend.agents.advisor import ConversationalAdvisor
from backend.agents.tasks import execute_agent_background, execute_workflow_background
from backend.agents.socketio_manager import socketio_manager
from backend.auth.users import current_active_user
from backend.database.models import ConversationMessage, User
from backend.database.schemas import ConversationMessageRead
from backend.dependencies import get_db_session
from backend.memory.utils import validate_case_ownership

router = APIRouter(prefix="/cases", tags=["advisor"])


class AdvisorMessageBody(BaseModel):
    message: str
    include_context: bool = True


class ReanalyzeBody(BaseModel):
    agent_name: Optional[str] = None


async def _sse_stream(
    case_id: UUID,
    user_id: UUID,
    message: str,
    include_context: bool,
):
    """Generator yielding SSE events for streaming response.
    Persistence (commit) is done inside ConversationalAdvisor.generate_response_stream
    using the same session passed here.
    """
    from backend.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        advisor = ConversationalAdvisor(db, case_id, user_id)
        try:
            async for chunk in advisor.generate_response_stream(
                user_message=message, include_context=include_context
            ):
                yield {"data": chunk}
        except Exception as e:
            await db.rollback()
            yield {"data": f"[Error: {e!s}]"}
            raise


@router.post("/{case_id}/advisor/message")
async def post_advisor_message(
    case_id: UUID,
    body: AdvisorMessageBody,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
) -> StreamingResponse:
    """Stream assistant response via SSE. Validates case ownership."""
    if not await validate_case_ownership(db, case_id, user.id):
        raise HTTPException(status_code=403, detail="Not authorized to access this case")
    return EventSourceResponse(
        _sse_stream(case_id, user.id, body.message, body.include_context)
    )


@router.get("/{case_id}/advisor/history", response_model=List[ConversationMessageRead])
async def get_advisor_history(
    case_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
) -> Any:
    """Return conversation history for the case, newest first."""
    if not await validate_case_ownership(db, case_id, user.id):
        raise HTTPException(status_code=403, detail="Not authorized to access this case")
    stmt = (
        select(ConversationMessage)
        .where(ConversationMessage.case_id == case_id)
        .order_by(ConversationMessage.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    messages = list(result.scalars().unique().all())
    return [ConversationMessageRead.model_validate(m) for m in messages]


@router.post("/{case_id}/advisor/reanalyze")
async def post_advisor_reanalyze(
    case_id: UUID,
    body: ReanalyzeBody,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
) -> Any:
    """Trigger agent re-analysis. Optional agent_name runs single agent; otherwise full workflow."""
    if not await validate_case_ownership(db, case_id, user.id):
        raise HTTPException(status_code=403, detail="Not authorized to access this case")
    advisor = ConversationalAdvisor(db, case_id, user.id)
    result = await advisor.trigger_reanalysis(agent_name=body.agent_name)
    if body.agent_name:
        coro = execute_agent_background(
            case_id, user.id, body.agent_name, socketio_manager
        )
    else:
        coro = execute_workflow_background(case_id, user.id, socketio_manager)
    background_tasks.add_task(asyncio.create_task, coro)
    return result


@router.get("/{case_id}/advisor/suggestions")
async def get_advisor_suggestions(
    case_id: UUID,
    limit: int = Query(5, ge=1, le=10),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
) -> List[str]:
    """Return suggested questions from memory blocks of type 'question' for this case."""
    if not await validate_case_ownership(db, case_id, user.id):
        raise HTTPException(status_code=403, detail="Not authorized to access this case")
    advisor = ConversationalAdvisor(db, case_id, user.id)
    return await advisor.get_suggested_questions(limit=limit)


@router.delete("/{case_id}/advisor/history")
async def delete_advisor_history(
    case_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
) -> Any:
    """Clear conversation history for the case."""
    if not await validate_case_ownership(db, case_id, user.id):
        raise HTTPException(status_code=403, detail="Not authorized to access this case")
    await db.execute(delete(ConversationMessage).where(ConversationMessage.case_id == case_id))
    await db.commit()
    return {"status": "ok", "message": "Conversation history cleared"}
