"""
Optional API router for direct Tavily search access. All endpoints require authentication.
"""
import time
from typing import Any

from fastapi import APIRouter, Depends

from backend.auth.users import current_active_user
from backend.database.models import User
from backend.database.schemas import (
    CaseLawSearchRequest,
    PrecedentSearchRequest,
    StatuteSearchRequest,
    TavilySearchRequest,
    TavilySearchResponse,
)
from backend.tools.tavily_search import TavilySearchService

router = APIRouter(prefix="", tags=["tools"])


def _get_tavily_service() -> TavilySearchService:
    return TavilySearchService()


@router.post("/search", response_model=TavilySearchResponse)
async def post_search(
    body: TavilySearchRequest,
    user: User = Depends(current_active_user),
) -> Any:
    """General Tavily search with full parameter control."""
    service = _get_tavily_service()
    start = time.monotonic()
    result = await service.search(
        query=body.query,
        search_depth=body.search_depth,
        max_results=body.max_results,
        include_domains=body.include_domains,
        exclude_domains=body.exclude_domains,
        topic=body.topic,
    )
    elapsed = time.monotonic() - start
    return TavilySearchResponse(
        query=result["query"],
        results=result["results"],
        answer=result.get("answer"),
        search_time=round(elapsed, 3),
    )


@router.post("/search/case-law", response_model=TavilySearchResponse)
async def post_search_case_law(
    body: CaseLawSearchRequest,
    user: User = Depends(current_active_user),
) -> Any:
    """Specialized case law search."""
    service = _get_tavily_service()
    start = time.monotonic()
    results = await service.search_case_law(
        query=body.query,
        jurisdiction=body.jurisdiction,
        max_results=body.max_results,
    )
    elapsed = time.monotonic() - start
    return TavilySearchResponse(
        query=body.query,
        results=results,
        answer=None,
        search_time=round(elapsed, 3),
    )


@router.post("/search/precedents", response_model=TavilySearchResponse)
async def post_search_precedents(
    body: PrecedentSearchRequest,
    user: User = Depends(current_active_user),
) -> Any:
    """Precedent research for conciliation court."""
    service = _get_tavily_service()
    start = time.monotonic()
    results = await service.search_precedents(
        dispute_type=body.dispute_type,
        facts=body.facts,
        jurisdiction=body.jurisdiction,
        max_results=body.max_results,
    )
    elapsed = time.monotonic() - start
    return TavilySearchResponse(
        query=f"{body.dispute_type} precedent: {body.facts[:100]}...",
        results=results,
        answer=None,
        search_time=round(elapsed, 3),
    )


@router.post("/search/statutes", response_model=TavilySearchResponse)
async def post_search_statutes(
    body: StatuteSearchRequest,
    user: User = Depends(current_active_user),
) -> Any:
    """Statute and rule lookup (Minnesota 491A, revisor)."""
    service = _get_tavily_service()
    start = time.monotonic()
    results = await service.search_statutes(
        topic=body.topic,
        statute_reference=body.statute_reference,
        max_results=body.max_results,
    )
    elapsed = time.monotonic() - start
    return TavilySearchResponse(
        query=f"Minnesota Statutes 491A {body.topic} {body.statute_reference or ''}".strip(),
        results=results,
        answer=None,
        search_time=round(elapsed, 3),
    )
