"""
Unit tests for Tavily Search: singleton client, search, legal methods, parsing, rate limiting, caching, errors, API.
"""
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

# Minimal settings for service init when mocking (avoids MagicMock for new Tavily config attrs).
TAVILY_MOCK_SETTINGS = {
    "TAVILY_API_KEY": "test",
    "TAVILY_RATE_LIMIT_RPM": 100,
    "TAVILY_SEARCH_DEPTH": "basic",
    "TAVILY_MAX_RESULTS": 5,
    "TAVILY_ENABLE_CACHING": False,
    "TAVILY_CACHE_TTL_SECONDS": 3600,
}

MOCK_TAVILY_RESPONSE = {
    "query": "Minnesota conciliation court jurisdiction",
    "results": [
        {
            "title": "Minnesota Conciliation Court Overview",
            "url": "https://www.mncourts.gov/conciliation",
            "content": "Conciliation court handles claims up to $20,000...",
            "score": 0.95,
            "published_date": "2024-01-15",
        }
    ],
    "answer": "Minnesota conciliation courts have jurisdiction over...",
}


# --- Client Initialization ---


def test_tavily_client_singleton():
    """Verify _get_tavily_client() returns same instance."""
    with patch("backend.tools.tavily_search.get_settings") as get_settings:
        get_settings.return_value = MagicMock(TAVILY_API_KEY="test-key")
        from backend.tools.tavily_search import _get_tavily_client

        _get_tavily_client.cache_clear()
        c1 = _get_tavily_client()
        c2 = _get_tavily_client()
        assert c1 is c2
        _get_tavily_client.cache_clear()


def test_tavily_client_uses_api_key():
    """Verify API key loaded from settings."""
    with patch("backend.tools.tavily_search.get_settings") as get_settings:
        get_settings.return_value = MagicMock(TAVILY_API_KEY="test-key-123")
        from backend.tools.tavily_search import _get_tavily_client

        _get_tavily_client.cache_clear()
        with patch("backend.tools.tavily_search.TavilyClient") as TavilyClient:
            _get_tavily_client()
            TavilyClient.assert_called_once_with(api_key="test-key-123")
        _get_tavily_client.cache_clear()


# --- Basic Search ---


@pytest.mark.asyncio
async def test_search_success():
    """Mock successful search response, verify result structure."""
    async def noop():
        pass

    with patch("backend.tools.tavily_search.get_settings") as get_settings:
        get_settings.return_value = MagicMock(**TAVILY_MOCK_SETTINGS)
        with patch("backend.tools.tavily_search._get_tavily_client") as get_client:
            mock_client = MagicMock()
            mock_client.search = MagicMock(return_value=MOCK_TAVILY_RESPONSE)
            get_client.return_value = mock_client
            from backend.tools.tavily_search import TavilySearchService

            service = TavilySearchService()
            service._rate_limiter.check_rate_limit = noop
            result = await service.search(query="Minnesota conciliation court jurisdiction", max_results=5)
            assert result["query"] == MOCK_TAVILY_RESPONSE["query"]
            assert len(result["results"]) == 1
            assert result["results"][0]["title"] == "Minnesota Conciliation Court Overview"
            assert result["answer"] == MOCK_TAVILY_RESPONSE["answer"]


@pytest.mark.asyncio
async def test_search_with_parameters():
    """Test all parameter combinations (domains, depth, max_results)."""
    with patch("backend.tools.tavily_search.get_settings") as get_settings:
        get_settings.return_value = MagicMock(**TAVILY_MOCK_SETTINGS)
        with patch("backend.tools.tavily_search._get_tavily_client") as get_client:
            mock_client = MagicMock()
            mock_client.search = MagicMock(return_value={"query": "q", "results": [], "answer": None})
            get_client.return_value = mock_client
            from backend.tools.tavily_search import TavilySearchService

            service = TavilySearchService()
            async def noop():
                pass
            service._rate_limiter.check_rate_limit = noop
            await service.search(
                query="test",
                search_depth="advanced",
                max_results=10,
                include_domains=["law.cornell.edu"],
                exclude_domains=["spam.com"],
                topic="general",
            )
            call_kwargs = mock_client.search.call_args[1]
            assert call_kwargs["query"] == "test"
            assert call_kwargs["search_depth"] == "advanced"
            assert call_kwargs["max_results"] == 10
            assert call_kwargs["include_domains"] == ["law.cornell.edu"]
            assert call_kwargs["exclude_domains"] == ["spam.com"]


@pytest.mark.asyncio
async def test_search_include_raw_content_passes_boolean():
    """Verify include_raw_content is passed as boolean to Tavily client, not string."""
    async def noop():
        pass

    with patch("backend.tools.tavily_search.get_settings") as get_settings:
        get_settings.return_value = MagicMock(**TAVILY_MOCK_SETTINGS)
        with patch("backend.tools.tavily_search._get_tavily_client") as get_client:
            mock_client = MagicMock()
            mock_client.search = MagicMock(return_value={"query": "q", "results": [], "answer": None})
            get_client.return_value = mock_client
            from backend.tools.tavily_search import TavilySearchService

            service = TavilySearchService()
            service._rate_limiter.check_rate_limit = noop
            await service.search(query="test", include_raw_content=True)

            call_kwargs = mock_client.search.call_args[1]
            assert call_kwargs["include_raw_content"] is True
            assert isinstance(call_kwargs["include_raw_content"], bool)


@pytest.mark.asyncio
async def test_search_empty_query_raises():
    """Verify ValueError for empty query."""
    with patch("backend.tools.tavily_search.get_settings") as get_settings:
        get_settings.return_value = MagicMock(**TAVILY_MOCK_SETTINGS)
        from backend.tools.tavily_search import TavilySearchService

        service = TavilySearchService()
        with pytest.raises(ValueError, match="empty"):
            await service.search(query="   ")


@pytest.mark.asyncio
async def test_search_retry_on_failure():
    """Mock API failure then success, verify retry logic."""
    with patch("backend.tools.tavily_search.get_settings") as get_settings:
        get_settings.return_value = MagicMock(**TAVILY_MOCK_SETTINGS)
        with patch("backend.tools.tavily_search._get_tavily_client") as get_client:
            mock_client = MagicMock()
            mock_client.search = MagicMock(
                side_effect=[Exception("timeout"), MOCK_TAVILY_RESPONSE]
            )
            get_client.return_value = mock_client
            from backend.tools.tavily_search import TavilySearchService

            service = TavilySearchService()
            async def noop():
                pass
            service._rate_limiter.check_rate_limit = noop
            result = await service.search(query="retry me")
            assert result["query"] == MOCK_TAVILY_RESPONSE["query"]
            assert mock_client.search.call_count == 2


@pytest.mark.asyncio
async def test_search_max_retries_exceeded():
    """Mock persistent failures, verify exception raised."""
    with patch("backend.tools.tavily_search.get_settings") as get_settings:
        get_settings.return_value = MagicMock(**TAVILY_MOCK_SETTINGS)
        with patch("backend.tools.tavily_search._get_tavily_client") as get_client:
            mock_client = MagicMock()
            mock_client.search = MagicMock(side_effect=Exception("API down"))
            get_client.return_value = mock_client
            from backend.tools.tavily_search import TavilyAPIError, TavilySearchService

            service = TavilySearchService()
            async def noop():
                pass
            service._rate_limiter.check_rate_limit = noop
            with pytest.raises(TavilyAPIError):
                await service.search(query="fail")


# --- Config-driven defaults ---


@pytest.mark.asyncio
async def test_search_uses_config_defaults_for_search_depth_and_max_results():
    """When search_depth and max_results are omitted, client is called with values from get_settings()."""
    async def noop():
        pass

    settings = {**TAVILY_MOCK_SETTINGS, "TAVILY_SEARCH_DEPTH": "advanced", "TAVILY_MAX_RESULTS": 10, "TAVILY_ENABLE_CACHING": False}
    with patch("backend.tools.tavily_search.get_settings") as get_settings:
        get_settings.return_value = MagicMock(**settings)
        with patch("backend.tools.tavily_search._get_tavily_client") as get_client:
            mock_client = MagicMock()
            mock_client.search = MagicMock(return_value={"query": "q", "results": [], "answer": None})
            get_client.return_value = mock_client
            from backend.tools.tavily_search import TavilySearchService

            service = TavilySearchService()
            service._rate_limiter.check_rate_limit = noop
            await service.search(query="test")
        call_kwargs = mock_client.search.call_args[1]
        assert call_kwargs["search_depth"] == "advanced"
        assert call_kwargs["max_results"] == 10


# --- Caching ---


@pytest.mark.asyncio
async def test_search_cache_hit_when_caching_enabled():
    """With TAVILY_ENABLE_CACHING=True, two identical requests result in a single client.search call."""
    async def noop():
        pass

    settings = {**TAVILY_MOCK_SETTINGS, "TAVILY_ENABLE_CACHING": True, "TAVILY_CACHE_TTL_SECONDS": 3600}
    with patch("backend.tools.tavily_search.get_settings") as get_settings:
        get_settings.return_value = MagicMock(**settings)
        with patch("backend.tools.tavily_search._get_tavily_client") as get_client:
            mock_client = MagicMock()
            mock_client.search = MagicMock(return_value={"query": "cached", "results": [], "answer": None})
            get_client.return_value = mock_client
            from backend.tools.tavily_search import TavilySearchService

            service = TavilySearchService()
            service._rate_limiter.check_rate_limit = noop
            await service.search(query="same query")
            await service.search(query="same query")
        assert mock_client.search.call_count == 1


@pytest.mark.asyncio
async def test_search_no_cache_when_caching_disabled():
    """With TAVILY_ENABLE_CACHING=False, two identical requests result in two client.search calls."""
    async def noop():
        pass

    with patch("backend.tools.tavily_search.get_settings") as get_settings:
        get_settings.return_value = MagicMock(**TAVILY_MOCK_SETTINGS)
        with patch("backend.tools.tavily_search._get_tavily_client") as get_client:
            mock_client = MagicMock()
            mock_client.search = MagicMock(return_value={"query": "q", "results": [], "answer": None})
            get_client.return_value = mock_client
            from backend.tools.tavily_search import TavilySearchService

            service = TavilySearchService()
            service._rate_limiter.check_rate_limit = noop
            await service.search(query="same query")
            await service.search(query="same query")
        assert mock_client.search.call_count == 2


# --- Specialized Searches ---


@pytest.mark.asyncio
async def test_search_case_law():
    """Verify query enhancement and domain filtering."""
    with patch("backend.tools.tavily_search.get_settings") as get_settings:
        get_settings.return_value = MagicMock(**TAVILY_MOCK_SETTINGS)
        with patch("backend.tools.tavily_search._get_tavily_client") as get_client:
            mock_client = MagicMock()
            mock_client.search = MagicMock(return_value={"query": "q", "results": [], "answer": None})
            get_client.return_value = mock_client
            from backend.tools.tavily_search import TavilySearchService

            service = TavilySearchService()
            async def noop():
                pass
            service._rate_limiter.check_rate_limit = noop
            await service.search_case_law(query="breach of contract", jurisdiction="Minnesota")
        call_kwargs = mock_client.search.call_args[1]
        assert "breach of contract" in call_kwargs["query"]
        assert "Minnesota" in call_kwargs["query"]
        assert "case law" in call_kwargs["query"]
        assert "law.cornell.edu" in call_kwargs["include_domains"]


@pytest.mark.asyncio
async def test_search_precedents():
    """Verify dispute type integration."""
    with patch("backend.tools.tavily_search.get_settings") as get_settings:
        get_settings.return_value = MagicMock(**TAVILY_MOCK_SETTINGS)
        with patch("backend.tools.tavily_search._get_tavily_client") as get_client:
            mock_client = MagicMock()
            mock_client.search = MagicMock(return_value={"query": "q", "results": [], "answer": None})
            get_client.return_value = mock_client
            from backend.tools.tavily_search import TavilySearchService

            service = TavilySearchService()
            async def noop():
                pass
            service._rate_limiter.check_rate_limit = noop
            await service.search_precedents(dispute_type="landlord-tenant", facts="security deposit not returned")
        call_kwargs = mock_client.search.call_args[1]
        assert "landlord-tenant" in call_kwargs["query"]
        assert "precedent" in call_kwargs["query"]
        assert "security deposit" in call_kwargs["query"]


@pytest.mark.asyncio
async def test_get_search_context_forwards_params():
    """Verify get_search_context forwards search_depth, max_results, include_domains to client."""
    async def noop():
        pass

    with patch("backend.tools.tavily_search.get_settings") as get_settings:
        get_settings.return_value = MagicMock(**TAVILY_MOCK_SETTINGS)
        with patch("backend.tools.tavily_search._get_tavily_client") as get_client:
            mock_client = MagicMock()
            mock_client.get_search_context = MagicMock(return_value="Context string from Tavily")
            get_client.return_value = mock_client
            from backend.tools.tavily_search import TavilySearchService

            service = TavilySearchService()
            service._rate_limiter.check_rate_limit = noop
            result = await service.get_search_context(
                query="Minnesota small claims",
                search_depth="advanced",
                max_results=10,
                include_domains=["law.cornell.edu", "mn.gov"],
            )
            assert result == "Context string from Tavily"
            call_kwargs = mock_client.get_search_context.call_args[1]
            assert call_kwargs["query"] == "Minnesota small claims"
            assert call_kwargs["search_depth"] == "advanced"
            assert call_kwargs["max_results"] == 10
            assert call_kwargs["include_domains"] == ["law.cornell.edu", "mn.gov"]


@pytest.mark.asyncio
async def test_get_search_context_fallback_when_client_lacks_params():
    """When client.get_search_context raises TypeError, fall back to search() with params."""
    async def noop():
        pass

    with patch("backend.tools.tavily_search.get_settings") as get_settings:
        get_settings.return_value = MagicMock(**TAVILY_MOCK_SETTINGS)
        with patch("backend.tools.tavily_search._get_tavily_client") as get_client:
            mock_client = MagicMock()
            mock_client.get_search_context = MagicMock(side_effect=TypeError("unexpected keyword"))
            mock_client.search = MagicMock(
                return_value={
                    "query": "test query",
                    "results": [
                        {
                            "title": "Result",
                            "url": "https://example.com",
                            "content": "Content here.",
                            "score": 0.9,
                        }
                    ],
                    "answer": None,
                }
            )
            get_client.return_value = mock_client
            from backend.tools.tavily_search import TavilySearchService

            service = TavilySearchService()
            service._rate_limiter.check_rate_limit = noop
            result = await service.get_search_context(
                query="test query",
                search_depth="advanced",
                max_results=8,
                include_domains=["law.cornell.edu"],
            )
            assert "## Search Results" in result
            assert "### Result" in result
            assert "Source:" in result
            assert "Content here" in result
            call_kwargs = mock_client.search.call_args[1]
            assert call_kwargs["query"] == "test query"
            assert call_kwargs["search_depth"] == "advanced"
            assert call_kwargs["max_results"] == 8
            assert call_kwargs["include_domains"] == ["law.cornell.edu"]


@pytest.mark.asyncio
async def test_research_legal_topic_honors_params():
    """Verify research_legal_topic passes max_results, search_depth, include_domains to get_search_context."""
    async def noop():
        pass

    with patch("backend.tools.tavily_search.get_settings") as get_settings:
        get_settings.return_value = MagicMock(**TAVILY_MOCK_SETTINGS)
        with patch("backend.tools.tavily_search._get_tavily_client") as get_client:
            mock_client = MagicMock()
            mock_client.get_search_context = MagicMock(return_value="Legal context")
            get_client.return_value = mock_client
            from backend.tools.tavily_search import TavilySearchService

            service = TavilySearchService()
            service._rate_limiter.check_rate_limit = noop
            result = await service.research_legal_topic(
                topic="jurisdiction limits",
                context="conciliation court",
                max_results=15,
            )
            assert result == "Legal context"
            call_kwargs = mock_client.get_search_context.call_args[1]
            assert "jurisdiction limits" in call_kwargs["query"]
            assert "conciliation court" in call_kwargs["query"]
            assert call_kwargs["max_results"] == 15
            assert call_kwargs["search_depth"] == "basic"
            assert call_kwargs["include_domains"] == service.LEGAL_DOMAINS


@pytest.mark.asyncio
async def test_search_statutes():
    """Verify Minnesota-specific domain filtering."""
    with patch("backend.tools.tavily_search.get_settings") as get_settings:
        get_settings.return_value = MagicMock(**TAVILY_MOCK_SETTINGS)
        with patch("backend.tools.tavily_search._get_tavily_client") as get_client:
            mock_client = MagicMock()
            mock_client.search = MagicMock(return_value={"query": "q", "results": [], "answer": None})
            get_client.return_value = mock_client
            from backend.tools.tavily_search import TavilySearchService

            service = TavilySearchService()
            async def noop():
                pass
            service._rate_limiter.check_rate_limit = noop
            await service.search_statutes(topic="jurisdiction", statute_reference="491A.01")
        call_kwargs = mock_client.search.call_args[1]
        assert "491A" in call_kwargs["query"]
        assert "www.revisor.mn.gov" in call_kwargs["include_domains"]


# --- Result Processing ---


def test_parse_search_result():
    """Verify field extraction and normalization."""
    from backend.tools.tavily_search import parse_search_result

    raw = {
        "title": "  Test Title  ",
        "url": "https://example.com",
        "content": "A" * 600 + ".",
        "score": 0.8,
        "published_date": "2024-01-01",
    }
    out = parse_search_result(raw)
    assert out["title"] == "Test Title"
    assert out["url"] == "https://example.com"
    assert out["score"] == 0.8
    assert len(out["content"]) <= 503
    assert out["published_date"] == "2024-01-01"


def test_filter_by_relevance():
    """Verify score filtering and keyword boosting."""
    from backend.tools.tavily_search import filter_by_relevance

    results = [
        {"content": "Plaintiff filed a claim.", "score": 0.9},
        {"content": "Weather today.", "score": 0.6},
        {"content": "Random text.", "score": 0.3},
    ]
    filtered = filter_by_relevance(results, min_score=0.5)
    assert len(filtered) == 2
    assert filtered[0].get("relevance_score", 0) >= filtered[1].get("relevance_score", 0)


def test_deduplicate_results():
    """Verify duplicate URL removal."""
    from backend.tools.tavily_search import deduplicate_results

    results = [
        {"url": "https://same.com/page1", "content": "A"},
        {"url": "https://same.com/page1", "content": "B"},
        {"url": "https://other.com/x", "content": "C"},
    ]
    deduped = deduplicate_results(results)
    urls = [r["url"] for r in deduped]
    assert len(deduped) == 2
    assert "https://same.com/page1" in urls
    assert "https://other.com/x" in urls


# --- Error Handling ---


@pytest.mark.asyncio
async def test_rate_limit_error():
    """Mock rate limit response, verify TavilyRateLimitError."""
    with patch("backend.tools.tavily_search.get_settings") as get_settings:
        get_settings.return_value = MagicMock(**TAVILY_MOCK_SETTINGS)
        from backend.tools.tavily_search import TavilyRateLimitError, TavilySearchService

        service = TavilySearchService()
        with patch.object(service._rate_limiter, "check_rate_limit") as check:
            async def raise_rate():
                raise TavilyRateLimitError("Rate limited", retry_after_seconds=30.0)
            check.side_effect = raise_rate
            with pytest.raises(TavilyRateLimitError) as exc_info:
                await service.search(query="test")
            assert exc_info.value.retry_after_seconds == 30.0


def test_api_error_handling():
    """Custom exceptions are subclasses of TavilySearchError."""
    from backend.tools.tavily_search import TavilyAPIError, TavilyRateLimitError, TavilySearchError

    assert issubclass(TavilyRateLimitError, TavilySearchError)
    assert issubclass(TavilyAPIError, TavilySearchError)


# --- Rate Limiting ---


@pytest.mark.asyncio
async def test_rate_limiter_allows_under_limit():
    """Verify requests allowed under RPM limit."""
    from backend.tools.tavily_search import TavilyRateLimiter

    limiter = TavilyRateLimiter(rpm=100)
    for _ in range(3):
        await limiter.check_rate_limit()


@pytest.mark.asyncio
async def test_rate_limiter_blocks_over_limit():
    """Verify blocking when limit exceeded."""
    from backend.tools.tavily_search import TavilyRateLimiter, TavilyRateLimitError

    limiter = TavilyRateLimiter(rpm=2)
    await limiter.check_rate_limit()
    await limiter.check_rate_limit()
    with pytest.raises(TavilyRateLimitError):
        await limiter.check_rate_limit()


@pytest.mark.asyncio
async def test_rate_limiter_resets_after_minute():
    """Verify time-based reset: after clearing old timestamps, requests allowed again."""
    from backend.tools.tavily_search import TavilyRateLimiter, TavilyRateLimitError

    limiter = TavilyRateLimiter(rpm=1)
    await limiter.check_rate_limit()
    with pytest.raises(TavilyRateLimitError):
        await limiter.check_rate_limit()
    # Simulate 60+ seconds passing by clearing old timestamps
    limiter._timestamps.clear()
    await limiter.check_rate_limit()
    # One more should work
    limiter._timestamps.clear()
    await limiter.check_rate_limit()


# --- API Endpoints ---


@pytest.mark.asyncio
async def test_search_endpoint_requires_auth():
    """Verify 401 without authentication."""
    with patch("backend.config.get_settings") as get_settings:
        get_settings.return_value = MagicMock(
            DATABASE_URL="postgresql://u:p@localhost/db",
            OPENAI_API_KEY="test",
            TAVILY_API_KEY="test",
            SECRET_KEY="x" * 32,
            FRONTEND_URL="http://localhost:5173",
            ENVIRONMENT="development",
            TAVILY_RATE_LIMIT_RPM=100,
        )
        from backend.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post(
                "/api/tools/search",
                json={"query": "test", "max_results": 5},
            )
            assert r.status_code == 401


@pytest.mark.asyncio
async def test_case_law_endpoint_requires_auth():
    """Case law endpoint requires auth."""
    with patch("backend.config.get_settings") as get_settings:
        get_settings.return_value = MagicMock(
            DATABASE_URL="postgresql://u:p@localhost/db",
            OPENAI_API_KEY="test",
            TAVILY_API_KEY="test",
            SECRET_KEY="x" * 32,
            FRONTEND_URL="http://localhost:5173",
            ENVIRONMENT="development",
            TAVILY_RATE_LIMIT_RPM=100,
        )
        from backend.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post(
                "/api/tools/search/case-law",
                json={"query": "breach", "jurisdiction": "Minnesota"},
            )
            assert r.status_code == 401


@pytest.mark.asyncio
async def test_precedents_endpoint_requires_auth():
    """Precedents endpoint requires auth."""
    with patch("backend.config.get_settings") as get_settings:
        get_settings.return_value = MagicMock(
            DATABASE_URL="postgresql://u:p@localhost/db",
            OPENAI_API_KEY="test",
            TAVILY_API_KEY="test",
            SECRET_KEY="x" * 32,
            FRONTEND_URL="http://localhost:5173",
            ENVIRONMENT="development",
            TAVILY_RATE_LIMIT_RPM=100,
        )
        from backend.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post(
                "/api/tools/search/precedents",
                json={"dispute_type": "contract", "facts": "payment not received"},
            )
            assert r.status_code == 401


@pytest.mark.asyncio
async def test_statutes_endpoint_requires_auth():
    """Statutes endpoint requires auth."""
    with patch("backend.config.get_settings") as get_settings:
        get_settings.return_value = MagicMock(
            DATABASE_URL="postgresql://u:p@localhost/db",
            OPENAI_API_KEY="test",
            TAVILY_API_KEY="test",
            SECRET_KEY="x" * 32,
            FRONTEND_URL="http://localhost:5173",
            ENVIRONMENT="development",
            TAVILY_RATE_LIMIT_RPM=100,
        )
        from backend.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post(
                "/api/tools/search/statutes",
                json={"topic": "jurisdiction"},
            )
            assert r.status_code == 401


def test_format_search_results_for_agent():
    """Agent formatter produces markdown sections."""
    from backend.tools.tavily_search import format_search_results_for_agent

    results = [
        {"title": "Page", "url": "https://x.com", "content": "Excerpt", "citation": "123"},
    ]
    text = format_search_results_for_agent(results)
    assert "## Search Results" in text
    assert "### Page" in text
    assert "Source:" in text
    assert "Citation:" in text


def test_summarize_search_results():
    """Summarizer returns bullet points."""
    from backend.tools.tavily_search import summarize_search_results

    results = [
        {"content": "First key point. Rest of sentence."},
        {"content": "Second point."},
    ]
    summary = summarize_search_results(results, max_chars=300)
    assert "- " in summary
    assert "First key point" in summary or "First" in summary
