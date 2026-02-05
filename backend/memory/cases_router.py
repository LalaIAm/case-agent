"""
REST API endpoints for case CRUD and session management.
"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from backend.exceptions import CaseNotFoundError, SessionNotFoundError, UnauthorizedError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.auth.users import current_active_user
from backend.database.models import Case, CaseSession, User
from backend.database.schemas import (
    CaseCreate,
    CaseRead,
    CaseSessionRead,
    CaseSessionSummary,
    CaseSessionUpdate,
    CaseWithRelations,
    DocumentRead,
    MemoryBlockCount,
)
from backend.dependencies import get_db_session
from backend.memory.session_manager import SessionManager
from backend.memory.utils import validate_case_ownership

router = APIRouter(prefix="", tags=["cases"])


@router.post("", response_model=CaseRead, status_code=201)
async def create_case(
    body: CaseCreate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
):
    """Create a new case and first session. Associates with current user, status=draft."""
    case = Case(
        user_id=user.id,
        title=body.title,
        description=body.description,
        status="draft",
    )
    db.add(case)
    await db.flush()
    session = CaseSession(
        case_id=case.id,
        session_number=1,
        status="active",
    )
    db.add(session)
    await db.flush()
    await db.refresh(case)
    return CaseRead.model_validate(case)


@router.get("", response_model=List[CaseRead])
async def list_cases(
    status: str | None = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
):
    """List all cases for the current user, ordered by created_at DESC."""
    stmt = select(Case).where(Case.user_id == user.id)
    if status is not None:
        stmt = stmt.where(Case.status == status)
    stmt = stmt.order_by(Case.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    cases = list(result.scalars().unique().all())
    return [CaseRead.model_validate(c) for c in cases]


@router.get("/{case_id}", response_model=CaseRead)
async def get_case(
    case_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
):
    """Get a single case. Returns 403 if not owned, 404 if not found."""
    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise CaseNotFoundError("Case not found.", case_id=str(case_id))
    if not await validate_case_ownership(db, case_id, user.id):
        raise UnauthorizedError("Not authorized to access this case.")
    return CaseRead.model_validate(case)


@router.get("/{case_id}/details", response_model=CaseWithRelations)
async def get_case_details(
    case_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
):
    """Get case with all relations (sessions, documents)."""
    if not await validate_case_ownership(db, case_id, user.id):
        result = await db.execute(select(Case).where(Case.id == case_id))
        if result.scalar_one_or_none() is None:
            raise CaseNotFoundError("Case not found.", case_id=str(case_id))
        raise UnauthorizedError("Not authorized to access this case.")

    result = await db.execute(
        select(Case)
        .where(Case.id == case_id)
        .options(
            selectinload(Case.sessions),
            selectinload(Case.documents),
        )
    )
    case = result.scalar_one_or_none()
    if not case:
        raise CaseNotFoundError("Case not found.", case_id=str(case_id))

    sessions_sorted = sorted(case.sessions, key=lambda s: s.session_number)
    return CaseWithRelations(
        **CaseRead.model_validate(case).model_dump(),
        sessions=[CaseSessionRead.model_validate(s) for s in sessions_sorted],
        documents=[DocumentRead.model_validate(d) for d in case.documents],
    )


@router.put("/{case_id}", response_model=CaseRead)
async def update_case(
    case_id: UUID,
    body: CaseUpdate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
):
    """Update case. Validates ownership."""
    if not await validate_case_ownership(db, case_id, user.id):
        result = await db.execute(select(Case).where(Case.id == case_id))
        if result.scalar_one_or_none() is None:
            raise CaseNotFoundError("Case not found.", case_id=str(case_id))
        raise UnauthorizedError("Not authorized to update this case.")

    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise CaseNotFoundError("Case not found.", case_id=str(case_id))

    if body.title is not None:
        case.title = body.title
    if body.description is not None:
        case.description = body.description
    if body.status is not None:
        case.status = body.status

    await db.flush()
    await db.refresh(case)
    return CaseRead.model_validate(case)


@router.delete("/{case_id}", status_code=204)
async def delete_case(
    case_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
):
    """Delete case. Cascade deletes sessions, documents, agent_runs, generated_documents."""
    if not await validate_case_ownership(db, case_id, user.id):
        result = await db.execute(select(Case).where(Case.id == case_id))
        if result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Case not found")
        raise HTTPException(status_code=403, detail="Not authorized to delete this case")

    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    await db.delete(case)
    await db.flush()


@router.get("/{case_id}/sessions", response_model=List[CaseSessionRead])
async def list_case_sessions(
    case_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
):
    """List sessions for a case, ordered by session_number."""
    if not await validate_case_ownership(db, case_id, user.id):
        result = await db.execute(select(Case).where(Case.id == case_id))
        if result.scalar_one_or_none() is None:
            raise CaseNotFoundError("Case not found.", case_id=str(case_id))
        raise UnauthorizedError("Not authorized to access this case.")

    result = await db.execute(
        select(CaseSession)
        .where(CaseSession.case_id == case_id)
        .order_by(CaseSession.session_number)
    )
    sessions = list(result.scalars().unique().all())
    return [CaseSessionRead.model_validate(s) for s in sessions]


@router.post("/{case_id}/sessions", response_model=CaseSessionRead, status_code=201)
async def create_session(
    case_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
):
    """Create a new session. Auto-increments session_number, status=active."""
    if not await validate_case_ownership(db, case_id, user.id):
        result = await db.execute(select(Case).where(Case.id == case_id))
        if result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Case not found")
        raise HTTPException(status_code=403, detail="Not authorized to add sessions to this case")

    max_result = await db.execute(
        select(func.coalesce(func.max(CaseSession.session_number), 0)).where(
            CaseSession.case_id == case_id
        )
    )
    max_num = max_result.scalar() or 0
    session = CaseSession(
        case_id=case_id,
        session_number=max_num + 1,
        status="active",
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return CaseSessionRead.model_validate(session)


@router.get("/{case_id}/sessions/{session_id}", response_model=CaseSessionRead)
async def get_session(
    case_id: UUID,
    session_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
):
    """Retrieve a specific session. Validates case ownership."""
    if not await validate_case_ownership(db, case_id, user.id):
        result = await db.execute(select(Case).where(Case.id == case_id))
        if result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Case not found")
        raise HTTPException(status_code=403, detail="Not authorized to access this case")
    result = await db.execute(
        select(CaseSession).where(
            CaseSession.id == session_id,
            CaseSession.case_id == case_id,
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise SessionNotFoundError("Session not found.", session_id=str(session_id))
    return CaseSessionRead.model_validate(session)


@router.put("/{case_id}/sessions/{session_id}", response_model=CaseSessionRead)
async def update_session(
    case_id: UUID,
    session_id: UUID,
    body: CaseSessionUpdate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
):
    """Update session status and completed_at. Validates case ownership."""
    if not await validate_case_ownership(db, case_id, user.id):
        result = await db.execute(select(Case).where(Case.id == case_id))
        if result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Case not found")
        raise HTTPException(status_code=403, detail="Not authorized to update this session")
    manager = SessionManager(db)
    session = await manager.get_session(session_id)
    if not session or session.case_id != case_id:
        raise SessionNotFoundError("Session not found.", session_id=str(session_id))
    updated = await manager.update_session_status(
        session_id,
        status=body.status if body.status is not None else session.status,
        completed_at=body.completed_at,
    )
    return CaseSessionRead.model_validate(updated)


@router.get("/{case_id}/sessions/{session_id}/summary", response_model=CaseSessionSummary)
async def get_session_summary(
    case_id: UUID,
    session_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
):
    """Return session metadata including memory block counts by type."""
    if not await validate_case_ownership(db, case_id, user.id):
        result = await db.execute(select(Case).where(Case.id == case_id))
        if result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Case not found")
        raise HTTPException(status_code=403, detail="Not authorized to access this case")
    manager = SessionManager(db)
    summary_data = await manager.get_session_summary(session_id)
    if not summary_data or summary_data["session"].case_id != case_id:
        raise HTTPException(status_code=404, detail="Session not found")
    session = summary_data["session"]
    counts = [MemoryBlockCount.model_validate(c) for c in summary_data["memory_block_counts"]]
    return CaseSessionSummary(
        **CaseSessionRead.model_validate(session).model_dump(),
        memory_block_counts=counts,
    )


@router.get("/{case_id}/active-session", response_model=CaseSessionRead)
async def get_active_session(
    case_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
):
    """Get the current active session for the case. Returns 404 if none active."""
    if not await validate_case_ownership(db, case_id, user.id):
        result = await db.execute(select(Case).where(Case.id == case_id))
        if result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Case not found")
        raise HTTPException(status_code=403, detail="Not authorized to access this case")
    manager = SessionManager(db)
    session = await manager.get_active_session(case_id)
    if not session:
        raise SessionNotFoundError("No active session for this case.", details={"case_id": str(case_id)})
    return CaseSessionRead.model_validate(session)
