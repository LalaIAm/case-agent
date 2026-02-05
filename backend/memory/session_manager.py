"""
Session lifecycle and state: active session resolution, status updates, summaries.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models import CaseSession, MemoryBlock


class SessionManager:
    """Handles session lifecycle and state for a case."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_session(self, session_id: UUID) -> Optional[CaseSession]:
        """Retrieve a single session by ID."""
        result = await self._session.execute(
            select(CaseSession).where(CaseSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def get_active_session(self, case_id: UUID) -> Optional[CaseSession]:
        """Find the most recent active session for a case."""
        result = await self._session.execute(
            select(CaseSession)
            .where(
                CaseSession.case_id == case_id,
                CaseSession.status == "active",
            )
            .order_by(CaseSession.session_number.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def update_session_status(
        self,
        session_id: UUID,
        status: str,
        completed_at: Optional[datetime] = None,
    ) -> Optional[CaseSession]:
        """Update session status and optionally set completion timestamp."""
        session = await self.get_session(session_id)
        if not session:
            return None
        session.status = status
        if completed_at is not None:
            session.completed_at = completed_at
        await self._session.flush()
        await self._session.refresh(session)
        return session

    async def get_session_summary(
        self, session_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Return session metadata with counts of memory blocks by type.
        Returns dict with session info plus memory_block_counts and total_blocks.
        """
        session = await self.get_session(session_id)
        if not session:
            return None

        stmt = (
            select(MemoryBlock.block_type, func.count(MemoryBlock.id).label("count"))
            .where(MemoryBlock.session_id == session_id)
            .group_by(MemoryBlock.block_type)
        )
        result = await self._session.execute(stmt)
        rows = result.all()
        counts = [{"block_type": row[0], "count": row[1]} for row in rows]
        total_blocks = sum(c["count"] for c in counts)

        return {
            "session": session,
            "memory_block_counts": counts,
            "total_blocks": total_blocks,
        }

    async def restore_session_context(
        self,
        session_id: UUID,
        block_types: Optional[List[str]] = None,
    ) -> List[MemoryBlock]:
        """Delegate to MemoryManager.get_session_blocks for context restoration."""
        from backend.memory.memory_manager import MemoryManager

        manager = MemoryManager(self._session)
        return await manager.get_session_blocks(session_id, block_types=block_types)
