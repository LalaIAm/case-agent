"""
RESTful API endpoints for memory blocks and semantic search.
"""
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.users import current_active_user
from backend.database.models import User
from backend.database.schemas import MemoryBlockCreate, MemoryBlockRead, MemoryBlockSearch, MemoryBlockUpdate
from backend.dependencies import get_db_session

from .memory_manager import MemoryManager
from .utils import validate_case_ownership, validate_session_ownership

router = APIRouter(prefix="", tags=["memory"])


@router.post("/blocks", response_model=MemoryBlockRead, status_code=201)
async def create_memory_block(
    body: MemoryBlockCreate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
) -> Any:
    """Create a memory block. User must own the case associated with the session."""
    if not await validate_session_ownership(db, body.session_id, user.id):
        raise HTTPException(status_code=403, detail="Not authorized to add blocks to this session")
    manager = MemoryManager(db)
    block = await manager.create_memory_block(
        session_id=body.session_id,
        block_type=body.block_type,
        content=body.content,
        metadata=body.metadata_,
    )
    return block


@router.get("/blocks/{block_id}", response_model=MemoryBlockRead)
async def get_memory_block(
    block_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
) -> Any:
    """Retrieve a single memory block. User must own the session."""
    manager = MemoryManager(db)
    block = await manager.get_memory_block(block_id)
    if not block:
        raise HTTPException(status_code=404, detail="Memory block not found")
    if not await validate_session_ownership(db, block.session_id, user.id):
        raise HTTPException(status_code=403, detail="Not authorized to access this block")
    return block


@router.get("/sessions/{session_id}/blocks", response_model=List[MemoryBlockRead])
async def get_session_blocks(
    session_id: UUID,
    block_types: Optional[List[str]] = Query(None, description="Filter by block types"),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
) -> Any:
    """Get all memory blocks for a session. User must own the session."""
    if not await validate_session_ownership(db, session_id, user.id):
        raise HTTPException(status_code=403, detail="Not authorized to access this session")
    manager = MemoryManager(db)
    blocks = await manager.get_session_blocks(session_id, block_types=block_types)
    return blocks


@router.put("/blocks/{block_id}", response_model=MemoryBlockRead)
async def update_memory_block(
    block_id: UUID,
    body: MemoryBlockUpdate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
) -> Any:
    """Update block content and metadata. User must own the session."""
    manager = MemoryManager(db)
    block = await manager.get_memory_block(block_id)
    if not block:
        raise HTTPException(status_code=404, detail="Memory block not found")
    if not await validate_session_ownership(db, block.session_id, user.id):
        raise HTTPException(status_code=403, detail="Not authorized to update this block")
    updated = await manager.update_memory_block(
        block_id, content=body.content, metadata=body.metadata_
    )
    return updated


@router.delete("/blocks/{block_id}", status_code=204)
async def delete_memory_block(
    block_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
) -> None:
    """Delete a memory block. User must own the session."""
    manager = MemoryManager(db)
    block = await manager.get_memory_block(block_id)
    if not block:
        raise HTTPException(status_code=404, detail="Memory block not found")
    if not await validate_session_ownership(db, block.session_id, user.id):
        raise HTTPException(status_code=403, detail="Not authorized to delete this block")
    await manager.delete_memory_block(block_id)


@router.post("/search")
async def search_memory(
    body: MemoryBlockSearch,
    session_id: Optional[UUID] = Query(None, description="Scope search to this session"),
    case_id: Optional[UUID] = Query(None, description="Scope search to this case (all sessions)"),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
) -> Any:
    """
    Semantic search over memory blocks. Scope by session_id or case_id, or omit both
    to search only within the current user's cases. Returns blocks with similarity scores.
    """
    if session_id is not None and not await validate_session_ownership(db, session_id, user.id):
        raise HTTPException(status_code=403, detail="Not authorized to search this session")
    if case_id is not None and not await validate_case_ownership(db, case_id, user.id):
        raise HTTPException(status_code=403, detail="Not authorized to search this case")
    manager = MemoryManager(db)
    blocks_with_scores = await manager.search_similar_blocks(
        query=body.query,
        session_id=session_id,
        case_id=case_id,
        user_id=user.id if session_id is None and case_id is None else None,
        block_types=body.block_types,
        limit=body.limit,
    )
    return {
        "results": [
            {"block": MemoryBlockRead.model_validate(b), "similarity": score}
            for b, score in blocks_with_scores
        ]
    }


@router.get("/sessions/{session_id}/context", response_model=List[MemoryBlockRead])
async def get_session_context(
    session_id: UUID,
    block_types: Optional[List[str]] = Query(None, description="Filter by block types"),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
) -> Any:
    """Retrieve all memory blocks for a session (session-specific context). User must own the session."""
    if not await validate_session_ownership(db, session_id, user.id):
        raise HTTPException(status_code=403, detail="Not authorized to access this session")
    manager = MemoryManager(db)
    blocks = await manager.get_session_blocks(session_id, block_types=block_types)
    return [MemoryBlockRead.model_validate(b) for b in blocks]


@router.get("/cases/{case_id}/context", response_model=List[MemoryBlockRead])
async def get_case_context(
    case_id: UUID,
    block_types: Optional[List[str]] = Query(None, description="Filter by block types"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
) -> Any:
    """Multi-session context retrieval for a case. User must own the case."""
    if not await validate_case_ownership(db, case_id, user.id):
        raise HTTPException(status_code=403, detail="Not authorized to access this case")
    manager = MemoryManager(db)
    blocks = await manager.get_case_context(case_id, block_types=block_types, limit=limit)
    return blocks
