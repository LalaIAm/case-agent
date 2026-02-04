"""
Core memory management: CRUD, semantic search, and block relationships.
"""
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database.models import CaseSession, MemoryBlock

from .embeddings import EmbeddingService


class MemoryManager:
    """Manages memory blocks: create, read, update, delete, and semantic search."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._embedding_service = EmbeddingService()

    async def create_memory_block(
        self,
        session_id: UUID,
        block_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MemoryBlock:
        """Create a memory block, generate embedding, and persist."""
        embedding = await self._embedding_service.generate_embedding(content)
        block = MemoryBlock(
            session_id=session_id,
            block_type=block_type,
            content=content.strip(),
            embedding=embedding,
            metadata_=metadata or {},
        )
        self._session.add(block)
        await self._session.flush()
        await self._session.refresh(block)
        return block

    async def get_memory_block(self, block_id: UUID) -> Optional[MemoryBlock]:
        """Retrieve a single memory block by ID."""
        result = await self._session.execute(
            select(MemoryBlock).where(MemoryBlock.id == block_id)
        )
        return result.scalar_one_or_none()

    async def get_session_blocks(
        self,
        session_id: UUID,
        block_types: Optional[List[str]] = None,
    ) -> List[MemoryBlock]:
        """Get all memory blocks for a session, optionally filtered by type."""
        stmt = select(MemoryBlock).where(MemoryBlock.session_id == session_id)
        if block_types:
            stmt = stmt.where(MemoryBlock.block_type.in_(block_types))
        stmt = stmt.order_by(MemoryBlock.created_at.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update_memory_block(
        self,
        block_id: UUID,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[MemoryBlock]:
        """Update block content and metadata, regenerate embedding."""
        block = await self.get_memory_block(block_id)
        if not block:
            return None
        block.content = content.strip()
        if metadata is not None:
            block.metadata_ = metadata
        block.embedding = await self._embedding_service.generate_embedding(block.content)
        await self._session.flush()
        await self._session.refresh(block)
        return block

    async def delete_memory_block(self, block_id: UUID) -> bool:
        """Hard delete a memory block."""
        block = await self.get_memory_block(block_id)
        if not block:
            return False
        await self._session.delete(block)
        await self._session.flush()
        return True

    async def search_similar_blocks(
        self,
        query: str,
        session_id: Optional[UUID] = None,
        case_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        block_types: Optional[List[str]] = None,
        limit: int = 10,
        min_similarity_threshold: Optional[float] = None,
    ) -> List[Tuple[MemoryBlock, float]]:
        """
        Semantic search using pgvector cosine similarity.
        Returns blocks ordered by similarity (1 - cosine distance), highest first.
        Scope by session_id, case_id, or user_id. When session_id/case_id are absent,
        user_id is used to scope to memory_blocks belonging to that user's cases
        (join memory_blocks -> case_sessions -> cases, filter cases.user_id).
        """
        query_embedding = await self._embedding_service.generate_embedding(query)
        qv = str(query_embedding)
        params: Dict[str, Any] = {"qv": qv, "limit": limit}
        if case_id is not None:
            sql = """
                SELECT mb.id, mb.session_id, mb.block_type, mb.content, mb.embedding, mb.metadata_, mb.created_at,
                       (1 - (mb.embedding <=> CAST(:qv AS vector))) AS similarity
                FROM public.memory_blocks mb
                JOIN public.case_sessions cs ON cs.id = mb.session_id AND cs.case_id = :case_id
                WHERE mb.embedding IS NOT NULL
            """
            params["case_id"] = str(case_id)
            if session_id is not None:
                sql += " AND mb.session_id = :session_id"
                params["session_id"] = str(session_id)
        elif session_id is not None:
            sql = """
                SELECT id, session_id, block_type, content, embedding, metadata_, created_at,
                       (1 - (embedding <=> CAST(:qv AS vector))) AS similarity
                FROM public.memory_blocks
                WHERE embedding IS NOT NULL AND session_id = :session_id
            """
            params["session_id"] = str(session_id)
        elif user_id is not None:
            sql = """
                SELECT mb.id, mb.session_id, mb.block_type, mb.content, mb.embedding, mb.metadata_, mb.created_at,
                       (1 - (mb.embedding <=> CAST(:qv AS vector))) AS similarity
                FROM public.memory_blocks mb
                JOIN public.case_sessions cs ON cs.id = mb.session_id
                JOIN public.cases c ON c.id = cs.case_id AND c.user_id = :user_id
                WHERE mb.embedding IS NOT NULL
            """
            params["user_id"] = str(user_id)
        else:
            return []
        if block_types:
            col = "mb.block_type" if (case_id is not None or user_id is not None) else "block_type"
            sql += f" AND {col} = ANY(:block_types)"
            params["block_types"] = block_types
        if min_similarity_threshold is not None:
            alias = "mb." if (case_id is not None or user_id is not None) else ""
            sql += f" AND (1 - ({alias}embedding <=> CAST(:qv AS vector))) >= :min_sim"
            params["min_sim"] = min_similarity_threshold
        alias = "mb." if (case_id is not None or user_id is not None) else ""
        sql += f" ORDER BY {alias}embedding <=> CAST(:qv AS vector) ASC LIMIT :limit"

        result = await self._session.execute(text(sql), params)
        rows = result.mappings().all()
        blocks_with_scores: List[Tuple[MemoryBlock, float]] = []
        for row in rows:
            bid = row["id"]
            block = await self.get_memory_block(bid)
            if block:
                blocks_with_scores.append((block, float(row["similarity"])))
        return blocks_with_scores

    async def get_case_context(
        self,
        case_id: UUID,
        block_types: Optional[List[str]] = None,
        limit: int = 50,
    ) -> List[MemoryBlock]:
        """Retrieve memory blocks across all sessions for a case, newest first."""
        stmt = (
            select(MemoryBlock)
            .join(CaseSession, MemoryBlock.session_id == CaseSession.id)
            .where(CaseSession.case_id == case_id)
        )
        if block_types:
            stmt = stmt.where(MemoryBlock.block_type.in_(block_types))
        stmt = stmt.order_by(MemoryBlock.created_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().unique().all())

    def _get_related_block_ids(self, block: MemoryBlock) -> List[UUID]:
        """Extract related block IDs from metadata."""
        if not block.metadata_ or not isinstance(block.metadata_, dict):
            return []
        related = block.metadata_.get("related_blocks")
        if not isinstance(related, list):
            return []
        ids = []
        for r in related:
            if isinstance(r, str):
                try:
                    ids.append(UUID(r))
                except ValueError:
                    pass
            elif isinstance(r, UUID):
                ids.append(r)
        return ids

    async def link_blocks(self, block_id: UUID, related_block_ids: List[UUID]) -> Optional[MemoryBlock]:
        """Store related block IDs in metadata for the given block."""
        block = await self.get_memory_block(block_id)
        if not block:
            return None
        meta = dict(block.metadata_) if block.metadata_ else {}
        meta["related_blocks"] = [str(u) for u in related_block_ids]
        block.metadata_ = meta
        await self._session.flush()
        await self._session.refresh(block)
        return block

    async def get_related_blocks(self, block_id: UUID) -> List[MemoryBlock]:
        """Return memory blocks linked from the given block's metadata."""
        block = await self.get_memory_block(block_id)
        if not block:
            return []
        ids = self._get_related_block_ids(block)
        if not ids:
            return []
        result = await self._session.execute(
            select(MemoryBlock).where(MemoryBlock.id.in_(ids))
        )
        return list(result.scalars().all())
