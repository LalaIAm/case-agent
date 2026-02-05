"""
REST API endpoints for case CRUD and session management.
"""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.auth.users import current_active_user
from backend.database.models import Case, CaseSession, User
from backend.database.schemas import (
    CaseCreate,
    CaseRead,
    CaseSessionRead,
    CaseUpdate,
    CaseWithRelations,
    DocumentRead,
)
from backend.dependencies import get_db_session
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
        raise HTTPException(status_code=404, detail="Case not found")
    if not await validate_case_ownership(db, case_id, user.id):
        raise HTTPException(status_code=403, detail="Not authorized to access this case")
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
            raise HTTPException(status_code=404, detail="Case not found")
        raise HTTPException(status_code=403, detail="Not authorized to access this case")

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
        raise HTTPException(status_code=404, detail="Case not found")

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
            raise HTTPException(status_code=404, detail="Case not found")
        raise HTTPException(status_code=403, detail="Not authorized to update this case")

    result = await db.execute(select(Case).where(Case.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

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
            raise HTTPException(status_code=404, detail="Case not found")
        raise HTTPException(status_code=403, detail="Not authorized to access this case")

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
