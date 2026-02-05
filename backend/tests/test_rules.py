"""
Unit tests for rules layer: static rules, RuleVectorStore, RuleRetriever, and rules API.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app


# --- Static rules ---


def test_get_static_rule_found():
    """Test retrieving a specific static rule by ID."""
    from backend.rules.static_rules import get_static_rule

    rule = get_static_rule("jurisdiction_monetary_general")
    assert rule is not None
    assert rule["title"] == "Monetary limit - general"
    assert "20,000" in rule["content"]
    assert rule["source"] == "MN Stat. § 491A.01"


def test_get_static_rule_not_found():
    """Test get_static_rule returns None for unknown ID."""
    from backend.rules.static_rules import get_static_rule

    assert get_static_rule("nonexistent_id") is None


def test_get_rules_by_category():
    """Test get_rules_by_category returns all rules in category."""
    from backend.rules.static_rules import get_rules_by_category

    rules = get_rules_by_category("jurisdiction")
    assert len(rules) >= 1
    for r in rules:
        assert "source" in r
        assert r["category"] == "jurisdiction"


def test_get_rules_by_category_invalid():
    """Test get_rules_by_category returns empty list for unknown category."""
    from backend.rules.static_rules import get_rules_by_category

    assert get_rules_by_category("invalid_category") == []


def test_search_static_rules():
    """Test keyword search across static rules."""
    from backend.rules.static_rules import search_static_rules

    results = search_static_rules("jurisdiction")
    assert len(results) >= 1
    results = search_static_rules("20,000")
    assert len(results) >= 1


def test_search_static_rules_empty_query():
    """Test search with empty query returns empty list."""
    from backend.rules.static_rules import search_static_rules

    assert search_static_rules("") == []
    assert search_static_rules("   ") == []


# --- RuleVectorStore (mocked) ---


@pytest.mark.asyncio
async def test_rule_vector_store_add_rule_creates_with_embedding():
    """Test add_rule creates a rule with embedding."""
    mock_embedding = [0.1] * 1536
    with patch("backend.rules.rag_store.EmbeddingService") as MockES:
        mock_instance = MagicMock()
        mock_instance.generate_embedding = AsyncMock(return_value=mock_embedding)
        MockES.return_value = mock_instance

        from backend.database.models import Rule
        from backend.rules.rag_store import RuleVectorStore

        session = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        added_rule = Rule(
            id=None,
            rule_type="statute",
            source="MN Stat. § 491A.01",
            title="Test",
            content="Test content",
            embedding=mock_embedding,
            metadata_={},
        )

        def add_side_effect(obj):
            obj.id = added_rule.id

        session.add = MagicMock()
        session.refresh = AsyncMock(side_effect=lambda obj: setattr(obj, "id", "00000000-0000-0000-0000-000000000001"))

        store = RuleVectorStore(session)
        rule = await store.add_rule(
            rule_type="statute",
            source="MN Stat. § 491A.01",
            title="Test",
            content="Test content",
        )
        assert rule.rule_type == "statute"
        assert rule.content == "Test content"
        mock_instance.generate_embedding.assert_called_once_with("Test content")


@pytest.mark.asyncio
async def test_rule_vector_store_add_rules_batch():
    """Test add_rules_batch handles multiple rules with batch embedding."""
    mock_embeddings = [[0.1] * 1536, [0.2] * 1536]
    with patch("backend.rules.rag_store.EmbeddingService") as MockES:
        mock_instance = MagicMock()
        mock_instance.generate_embeddings = AsyncMock(return_value=mock_embeddings)
        MockES.return_value = mock_instance

        from backend.rules.rag_store import RuleVectorStore

        session = AsyncMock()
        session.flush = AsyncMock()
        session.add = MagicMock()
        session.refresh = AsyncMock()

        store = RuleVectorStore(session)
        rules = [
            {"rule_type": "statute", "source": "S1", "title": "T1", "content": "C1"},
            {"rule_type": "procedure", "source": "S2", "title": "T2", "content": "C2"},
        ]
        created = await store.add_rules_batch(rules)
        assert len(created) == 2
        mock_instance.generate_embeddings.assert_called_once()


# --- RuleRetriever (mocked) ---


@pytest.mark.asyncio
async def test_rule_retriever_hybrid_search_static():
    """Test hybrid_search includes static results when include_static True."""
    with patch("backend.rules.rule_retriever.RuleRetriever.search_rules", new_callable=AsyncMock, return_value=[]):
        from backend.rules.rule_retriever import RuleRetriever

        session = AsyncMock()
        retriever = RuleRetriever(session)
        result = await retriever.hybrid_search(
            query="jurisdiction",
            include_static=True,
            include_case_law=False,
            limit=10,
        )
        assert "static_rules" in result
        assert "case_law" in result
        assert len(result["static_rules"]) >= 1
        assert result["case_law"] == []


# --- API ---


@pytest.mark.asyncio
async def test_rules_search_requires_auth():
    """Test that rules search endpoint requires authentication."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            "/api/rules/search",
            json={"query": "jurisdiction", "limit": 5},
        )
        assert r.status_code == 401


@pytest.mark.asyncio
async def test_rules_jurisdiction_requires_auth():
    """Test that rules jurisdiction endpoint requires authentication."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/rules/jurisdiction")
        assert r.status_code == 401


@pytest.mark.asyncio
async def test_rules_hybrid_search_requires_auth():
    """Test that rules hybrid-search endpoint requires authentication."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            "/api/rules/hybrid-search",
            json={"query": "filing", "include_static": True, "include_case_law": False},
        )
        assert r.status_code == 401


@pytest.mark.asyncio
async def test_rules_get_requires_auth():
    """Test that get rule by ID requires authentication."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/rules/00000000-0000-0000-0000-000000000001")
        assert r.status_code == 401
