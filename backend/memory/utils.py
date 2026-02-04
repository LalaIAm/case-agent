"""
Helper functions for memory: session resolution, ownership checks, formatting, cleanup.
"""
from typing import List
from uuid import UUID

from sqlalchemy import func, select

from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models import Case, CaseSession, MemoryBlock


async def get_or_create_session(db: AsyncSession, case_id: UUID) -> CaseSession:
    """Get the active session for the case, or create a new one with incremented session_number."""
    # Get max session_number for this case
    result = await db.execute(
        select(func.coalesce(func.max(CaseSession.session_number), 0)).where(
            CaseSession.case_id == case_id
        )
    )
    max_num = result.scalar() or 0
    # Check for existing active session
    result = await db.execute(
        select(CaseSession).where(
            CaseSession.case_id == case_id,
            CaseSession.status == "active",
        ).order_by(CaseSession.session_number.desc()).limit(1)
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing
    session = CaseSession(case_id=case_id, session_number=max_num + 1, status="active")
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return session


async def validate_case_ownership(
    db: AsyncSession, case_id: UUID, user_id: UUID
) -> bool:
    """Return True if the user owns the case."""
    result = await db.execute(
        select(Case).where(Case.id == case_id, Case.user_id == user_id)
    )
    return result.scalar_one_or_none() is not None


async def validate_session_ownership(
    db: AsyncSession, session_id: UUID, user_id: UUID
) -> bool:
    """Return True if the user owns the case associated with the session."""
    result = await db.execute(
        select(CaseSession)
        .join(Case, CaseSession.case_id == Case.id)
        .where(CaseSession.id == session_id, Case.user_id == user_id)
    )
    return result.scalar_one_or_none() is not None


def format_memory_context(blocks: List[MemoryBlock]) -> str:
    """Format memory blocks into readable text for agent consumption (group by type, add headers)."""
    by_type: dict[str, List[MemoryBlock]] = {}
    for b in blocks:
        by_type.setdefault(b.block_type, []).append(b)
    lines = []
    for block_type in ("fact", "evidence", "strategy", "rule", "question"):
        if block_type not in by_type:
            continue
        lines.append(f"## {block_type.title()}")
        for block in by_type[block_type]:
            lines.append(f"- {block.content}")
        lines.append("")
    return "\n".join(lines).strip()


def extract_key_facts(blocks: List[MemoryBlock]) -> List[str]:
    """Extract and deduplicate fact content from fact blocks."""
    seen = set()
    facts: List[str] = []
    for b in blocks:
        if b.block_type != "fact":
            continue
        c = b.content.strip()
        if c and c not in seen:
            seen.add(c)
            facts.append(c)
    return facts


async def cleanup_old_sessions(
    db: AsyncSession, case_id: UUID, keep_recent: int = 5
) -> None:
    """Archive or delete old sessions beyond the retention limit (by session_number descending)."""
    result = await db.execute(
        select(CaseSession)
        .where(CaseSession.case_id == case_id)
        .order_by(CaseSession.session_number.desc())
    )
    sessions = list(result.scalars().all())
    if len(sessions) <= keep_recent:
        return
    to_archive = sessions[keep_recent:]
    for s in to_archive:
        s.status = "archived"
    await db.flush()
