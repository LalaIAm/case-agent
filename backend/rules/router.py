"""
RESTful API endpoints for rules: search, jurisdiction, procedures, hybrid search.
"""
from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.users import current_active_user
from backend.config import get_settings
from backend.database.models import User
from backend.database.schemas import (
    HybridRuleSearch,
    RuleCreate,
    RuleRead,
    RuleSearch,
)
from backend.dependencies import get_db_session

from .rag_store import RuleVectorStore
from .rule_retriever import RuleRetriever

router = APIRouter(prefix="", tags=["rules"])


@router.post("/search")
async def search_rules(
    body: RuleSearch,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
) -> Any:
    """Semantic search over rules. Returns results with similarity scores."""
    settings = get_settings()
    min_similarity = (
        body.min_similarity
        if body.min_similarity is not None
        else settings.RULES_SIMILARITY_THRESHOLD
    )
    retriever = RuleRetriever(db)
    results = await retriever.search_rules(
        query=body.query,
        rule_types=body.rule_types,
        limit=body.limit,
        min_similarity=min_similarity,
    )
    return {
        "results": [
            {"rule": RuleRead.model_validate(r), "similarity": score}
            for r, score in results
        ]
    }


@router.get("/jurisdiction", response_model=List[RuleRead])
async def get_jurisdiction_rules(
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
) -> Any:
    """Return jurisdiction-related rules (statute, jurisdiction metadata)."""
    retriever = RuleRetriever(db)
    rules = await retriever.get_jurisdiction_rules()
    return rules


@router.get("/procedures", response_model=List[RuleRead])
async def get_procedure_rules(
    procedure_type: str | None = Query(None, description="Filter by procedure type"),
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
) -> Any:
    """Return procedure rules, optionally filtered by procedure_type."""
    retriever = RuleRetriever(db)
    rules = await retriever.get_procedure_rules(procedure_type=procedure_type)
    return rules


@router.post("/hybrid-search")
async def hybrid_search_rules(
    body: HybridRuleSearch,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
) -> Dict[str, List[Any]]:
    """Combine static rule keyword search and case law semantic search."""
    retriever = RuleRetriever(db)
    return await retriever.hybrid_search(
        query=body.query,
        include_static=body.include_static,
        include_case_law=body.include_case_law,
        limit=body.limit,
    )


@router.get("/{rule_id}", response_model=RuleRead)
async def get_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
) -> Any:
    """Retrieve a single rule by ID."""
    store = RuleVectorStore(db)
    rule = await store.get_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


@router.post("", response_model=RuleRead, status_code=201)
async def create_rule(
    body: RuleCreate,
    db: AsyncSession = Depends(get_db_session),
    user: User = Depends(current_active_user),
) -> Any:
    """Create a rule (admin/future use)."""
    store = RuleVectorStore(db)
    rule = await store.add_rule(
        rule_type=body.rule_type,
        source=body.source,
        title=body.title,
        content=body.content,
        metadata=body.metadata_,
    )
    return rule
