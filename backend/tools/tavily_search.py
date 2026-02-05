"""
Tavily Search integration for legal research: singleton client, retry logic, async support,
specialized legal search methods, result parsing, rate limiting, caching, and agent-friendly formatting.
"""
import asyncio
import functools
import html
import logging
import re
import time
from collections import deque
from typing import Any, Callable, Dict, List, Optional, Tuple

from tavily import TavilyClient

from backend.config import get_settings

logger = logging.getLogger(__name__)

# --- Custom Exceptions ---


class TavilySearchError(Exception):
    """Base exception for Tavily search operations."""

    pass


class TavilyRateLimitError(TavilySearchError):
    """Raised when Tavily rate limit is exceeded. Includes retry-after seconds."""

    def __init__(self, message: str, retry_after_seconds: float = 0.0):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class TavilyAPIError(TavilySearchError):
    """Raised for Tavily API failures (bad request, server error, etc.)."""

    pass


# --- Singleton Client ---


@functools.lru_cache(maxsize=1)
def _get_tavily_client() -> TavilyClient:
    """Return a cached TavilyClient instance (singleton)."""
    settings = get_settings()
    return TavilyClient(api_key=settings.TAVILY_API_KEY)


# --- Rate Limiter ---


class TavilyRateLimiter:
    """
    In-memory rate limiter for Tavily API calls.
    Tracks request timestamps and enforces configurable RPM.
    """

    def __init__(self, rpm: int = 100):
        self._rpm = rpm
        self._timestamps: deque[float] = deque(maxlen=rpm)

    async def check_rate_limit(self) -> None:
        """
        Ensure we are under the rate limit. If over limit, raises TavilyRateLimitError
        with retry_after_seconds.
        """
        import time

        now = time.monotonic()
        # Drop timestamps older than 60 seconds
        while self._timestamps and now - self._timestamps[0] >= 60.0:
            self._timestamps.popleft()
        if len(self._timestamps) >= self._rpm:
            wait = 60.0 - (now - self._timestamps[0])
            if wait > 0:
                raise TavilyRateLimitError(
                    f"Tavily rate limit exceeded ({self._rpm} RPM). Retry after {wait:.0f}s.",
                    retry_after_seconds=wait,
                )
            self._timestamps.popleft()
        self._timestamps.append(now)


# --- Error Handler Decorator ---


def handle_tavily_errors(f: Callable[..., Any]) -> Callable[..., Any]:
    """Wrap search methods to catch and transform exceptions, log context, re-raise as custom exceptions."""

    @functools.wraps(f)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await f(*args, **kwargs)
        except (TavilySearchError, ValueError):
            raise
        except Exception as e:
            logger.exception(
                "Tavily search error: %s (query=%s, kwargs=%s)",
                e,
                kwargs.get("query", getattr(args[0], "_last_query", "")),
                {k: v for k, v in kwargs.items() if k != "query"},
            )
            if "rate" in str(e).lower() or "limit" in str(e).lower() or "429" in str(e):
                raise TavilyRateLimitError(str(e)) from e
            raise TavilyAPIError(str(e)) from e

    return wrapper


# --- In-memory search cache ---


def _search_cache_key(
    query: str,
    search_depth: str,
    max_results: int,
    topic: str,
    include_domains: Optional[List[str]],
    exclude_domains: Optional[List[str]],
    include_answer: bool,
    include_raw_content: bool,
) -> Tuple[Any, ...]:
    """Build a hashable cache key from search parameters."""
    return (
        query.strip(),
        search_depth,
        max_results,
        topic,
        tuple(include_domains) if include_domains else (),
        tuple(exclude_domains) if exclude_domains else (),
        include_answer,
        include_raw_content,
    )


def _context_cache_key(
    query: str,
    max_tokens: int,
    search_depth: str,
    max_results: int,
    include_domains: Optional[List[str]],
) -> Tuple[Any, ...]:
    """Build a hashable cache key for get_search_context parameters."""
    return (
        query.strip(),
        max_tokens,
        search_depth,
        max_results,
        tuple(include_domains) if include_domains else (),
    )


class _TavilySearchCache:
    """Simple TTL-based in-memory cache for search results (query + params -> result)."""

    def __init__(self, ttl_seconds: int) -> None:
        self._ttl = ttl_seconds
        self._store: Dict[Tuple[Any, ...], Tuple[Dict[str, Any], float]] = {}

    def get(self, key: Tuple[Any, ...]) -> Optional[Dict[str, Any]]:
        entry = self._store.get(key)
        if not entry:
            return None
        result, expiry = entry
        if time.monotonic() > expiry:
            del self._store[key]
            return None
        return result

    def set(self, key: Tuple[Any, ...], value: Dict[str, Any]) -> None:
        self._store[key] = (value, time.monotonic() + self._ttl)

    def get_context(self, key: Tuple[Any, ...]) -> Optional[str]:
        """Get cached context string (stored as dict with 'context' key for uniformity)."""
        entry = self._store.get(key)
        if not entry:
            return None
        payload, expiry = entry
        if time.monotonic() > expiry:
            del self._store[key]
            return None
        return payload.get("context")

    def set_context(self, key: Tuple[Any, ...], context: str) -> None:
        self._store[key] = ({"context": context}, time.monotonic() + self._ttl)


# --- Result Parsing and Filtering ---


def parse_search_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract and normalize fields from a single Tavily result dict.
    Cleans HTML entities, truncates content to ~500 chars at sentence boundary.
    """
    title = result.get("title") or ""
    url = result.get("url") or ""
    content = result.get("content") or ""
    score = float(result.get("score", 0.0))
    published_date = result.get("published_date")

    # Clean HTML entities and extra whitespace
    content = html.unescape(content)
    content = re.sub(r"\s+", " ", content).strip()
    if len(content) > 500:
        last_period = content[:500].rfind(".")
        content = content[: last_period + 1] if last_period > 200 else content[:497] + "..."

    return {
        "title": title.strip(),
        "url": url.strip(),
        "content": content,
        "score": score,
        "published_date": published_date,
    }


def filter_by_relevance(
    results: List[Dict[str, Any]],
    min_score: float = 0.5,
    keywords: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Filter results by relevance score and optionally boost by legal keywords.
    Sorts by score descending.
    """
    legal_terms = keywords or [
        "plaintiff",
        "defendant",
        "claim",
        "judgment",
        "conciliation court",
    ]
    filtered = [r for r in results if float(r.get("score", 0)) >= min_score]
    for r in filtered:
        content_lower = (r.get("content") or "").lower()
        if any(term in content_lower for term in legal_terms):
            r["relevance_score"] = float(r.get("score", 0)) * 1.1
        else:
            r["relevance_score"] = float(r.get("score", 0))
    filtered.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
    return filtered


def deduplicate_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate URLs and merge similar content from same domain."""
    seen_urls: set[str] = set()
    seen_domains: Dict[str, List[Dict[str, Any]]] = {}
    out: List[Dict[str, Any]] = []

    for r in results:
        url = (r.get("url") or "").strip()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        try:
            from urllib.parse import urlparse

            domain = urlparse(url).netloc or url
        except Exception:
            domain = url
        if domain not in seen_domains:
            seen_domains[domain] = []
        seen_domains[domain].append(r)

    for domain, group in seen_domains.items():
        if len(group) == 1:
            out.append(group[0])
        else:
            # Merge: keep first, append content from others from same domain
            merged = {**group[0]}
            contents = [merged.get("content", "")]
            for g in group[1:]:
                contents.append(g.get("content", ""))
            merged["content"] = " ".join(c for c in contents if c).strip()[:800]
            out.append(merged)
    return out


# --- Agent Helpers ---


def format_search_results_for_agent(results: List[Dict[str, Any]]) -> str:
    """
    Format search results as markdown for LLM context injection.
    Sections: ## Search Results, ### [Title], Source: [URL], Content: [excerpt], relevance/citations.
    """
    lines = ["## Search Results"]
    for r in results:
        title = r.get("title", "Untitled")
        url = r.get("url", "")
        content = r.get("content", "")
        score = r.get("relevance_score") or r.get("score", 0)
        citation = r.get("citation") or ""
        lines.append(f"### {title}")
        lines.append(f"Source: {url}")
        if citation:
            lines.append(f"Citation: {citation}")
        lines.append(f"Relevance: {score:.2f}")
        lines.append(f"Content: {content}")
        lines.append("")
    return "\n".join(lines).strip()


def summarize_search_results(
    results: List[Dict[str, Any]],
    focus_area: Optional[str] = None,
    max_chars: int = 500,
) -> str:
    """
    Extract key points from top results into a bullet-point summary.
    Optional focus_area to emphasize. Returns concise text (max ~500 chars) for agent memory.
    """
    bullets: List[str] = []
    for r in results[:5]:
        content = (r.get("content") or "").strip()
        if not content:
            continue
        # First sentence or first 120 chars as point
        first = content.split(".")[0].strip() + "." if "." in content else content[:120]
        if first and first not in bullets:
            bullets.append(first)
    summary = "\n".join(f"- {b}" for b in bullets[:10])
    if focus_area:
        summary = f"Focus: {focus_area}\n{summary}"
    if len(summary) > max_chars:
        summary = summary[: max_chars - 3] + "..."
    return summary


# --- TavilySearchService ---


class TavilySearchService:
    """
    Singleton-backed Tavily search service with retry logic, async wrappers,
    caching, and specialized legal research methods.
    """

    DEFAULT_TOPIC = "general"
    LEGAL_DOMAINS = [
        "law.cornell.edu",
        "justia.com",
        "casetext.com",
        "courtlistener.com",
        "mn.gov",
    ]

    def __init__(self) -> None:
        self._client = _get_tavily_client()
        settings = get_settings()
        self._rate_limiter = TavilyRateLimiter(rpm=settings.TAVILY_RATE_LIMIT_RPM)
        self._default_search_depth = settings.TAVILY_SEARCH_DEPTH
        self._default_max_results = settings.TAVILY_MAX_RESULTS
        self._cache_enabled = settings.TAVILY_ENABLE_CACHING
        self._cache_ttl_seconds = settings.TAVILY_CACHE_TTL_SECONDS
        self._search_cache: Optional[_TavilySearchCache] = (
            _TavilySearchCache(self._cache_ttl_seconds) if self._cache_enabled else None
        )
        self._last_query: str = ""

    def _map_tavily_exception(self, e: Exception) -> None:
        """Map Tavily/HTTP exceptions to our custom exceptions."""
        err_msg = str(e).lower()
        if "rate" in err_msg or "limit" in err_msg or "429" in err_msg:
            raise TavilyRateLimitError(str(e)) from e
        raise TavilyAPIError(str(e)) from e

    @handle_tavily_errors
    async def search(
        self,
        query: str,
        search_depth: Optional[str] = None,
        max_results: Optional[int] = None,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        include_answer: bool = False,
        include_raw_content: bool = False,
        topic: str = "general",
    ) -> Dict[str, Any]:
        """
        Run a Tavily search with retry and async wrapper.
        Returns dict: {"query": str, "results": List[dict], "answer": str | None}.
        Defaults for search_depth and max_results come from config (TAVILY_SEARCH_DEPTH, TAVILY_MAX_RESULTS).
        """
        query = (query or "").strip()
        if not query:
            raise ValueError("query cannot be empty")
        self._last_query = query

        if search_depth is None:
            search_depth = self._default_search_depth
        if max_results is None:
            max_results = self._default_max_results

        cache_key = _search_cache_key(
            query, search_depth, max_results, topic,
            include_domains, exclude_domains, include_answer, include_raw_content,
        )
        if self._search_cache:
            cached = self._search_cache.get(cache_key)
            if cached is not None:
                return cached

        await self._rate_limiter.check_rate_limit()

        max_retries = 3
        base_delay = 1.0
        last_error: Optional[Exception] = None

        kwargs: Dict[str, Any] = {
            "query": query,
            "search_depth": search_depth,
            "max_results": max_results,
            "topic": topic,
            "include_answer": include_answer,
        }
        if include_domains:
            kwargs["include_domains"] = include_domains
        if exclude_domains:
            kwargs["exclude_domains"] = exclude_domains
        if include_raw_content:
            kwargs["include_raw_content"] = True

        def _search_sync() -> Dict[str, Any]:
            return self._client.search(**kwargs)

        for attempt in range(max_retries):
            try:
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(None, _search_sync)
                result = {
                    "query": response.get("query", query),
                    "results": response.get("results", []),
                    "answer": response.get("answer"),
                }
                if self._search_cache:
                    self._search_cache.set(cache_key, result)
                return result
            except Exception as e:
                last_error = e
                try:
                    from tavily.errors import UsageLimitExceededError

                    if isinstance(e, UsageLimitExceededError):
                        raise TavilyRateLimitError(str(e)) from e
                except ImportError:
                    pass
                if attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)
                    await asyncio.sleep(delay)
                else:
                    self._map_tavily_exception(e)
        raise last_error or TavilyAPIError("Search failed after retries")

    def _get_search_context_fallback(
        self,
        query: str,
        search_depth: str,
        max_results: int,
        include_domains: Optional[List[str]],
    ) -> str:
        """
        Fallback when TavilyClient.get_search_context does not support search params:
        run search() and format results into a context string.
        """
        kwargs: Dict[str, Any] = {
            "query": query,
            "search_depth": search_depth,
            "max_results": max_results,
        }
        if include_domains:
            kwargs["include_domains"] = include_domains
        response = self._client.search(**kwargs)
        results = response.get("results", [])
        parsed = [parse_search_result(r) for r in results]
        return format_search_results_for_agent(parsed)

    @handle_tavily_errors
    async def get_search_context(
        self,
        query: str,
        max_tokens: int = 4000,
        search_depth: Optional[str] = None,
        max_results: Optional[int] = None,
        include_domains: Optional[List[str]] = None,
    ) -> str:
        """
        Get token-limited search context string for RAG/agent consumption.
        Defaults for search_depth and max_results come from config.
        Forwards search_depth, max_results, and include_domains to Tavily.
        If the client lacks support for these params, falls back to search() + format.
        """
        query = (query or "").strip()
        if not query:
            raise ValueError("query cannot be empty")
        self._last_query = query

        if search_depth is None:
            search_depth = self._default_search_depth
        if max_results is None:
            max_results = self._default_max_results

        context_cache_key = _context_cache_key(
            query, max_tokens, search_depth, max_results, include_domains,
        )
        if self._search_cache:
            cached = self._search_cache.get_context(context_cache_key)
            if cached is not None:
                return cached

        await self._rate_limiter.check_rate_limit()

        max_retries = 3
        base_delay = 1.0
        last_error: Optional[Exception] = None

        def _context_sync() -> str:
            # Build kwargs; TavilyClient.get_search_context may not accept all params
            context_kwargs: Dict[str, Any] = {
                "query": query,
                "search_depth": search_depth,
                "max_results": max_results,
            }
            if include_domains:
                context_kwargs["include_domains"] = include_domains
            try:
                return self._client.get_search_context(**context_kwargs)
            except (TypeError, AttributeError):
                # Client doesn't support these params; fall back to search + format
                return self._get_search_context_fallback(
                    query=query,
                    search_depth=search_depth,
                    max_results=max_results,
                    include_domains=include_domains,
                )

        for attempt in range(max_retries):
            try:
                loop = asyncio.get_event_loop()
                context = await loop.run_in_executor(None, _context_sync)
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)
                    await asyncio.sleep(delay)
                else:
                    self._map_tavily_exception(e)
                continue
            if context and isinstance(context, str):
                # Rough token truncation (~4 chars per token)
                if max_tokens and len(context) > max_tokens * 4:
                    context = context[: max_tokens * 4].rsplit(" ", 1)[0] + "..."
                if self._search_cache:
                    self._search_cache.set_context(context_cache_key, context)
                return context
            last_error = TavilyAPIError("Empty or invalid context response")
        raise last_error or TavilyAPIError("get_search_context failed after retries")

    @handle_tavily_errors
    async def search_case_law(
        self,
        query: str,
        jurisdiction: str = "Minnesota",
        max_results: int = 5,
        search_depth: str = "advanced",
    ) -> List[Dict[str, Any]]:
        """
        Case law search with jurisdiction context and legal domain filtering.
        Returns list of {title, url, content, citation?, relevance_score}.
        """
        enhanced = f"{query} {jurisdiction} case law precedent"
        domains = ["law.cornell.edu", "justia.com", "casetext.com", "courtlistener.com"]
        response = await self.search(
            query=enhanced,
            search_depth=search_depth,
            max_results=max_results,
            include_domains=domains,
            topic=self.DEFAULT_TOPIC,
            include_answer=True,
        )
        raw = response.get("results", [])
        parsed = [parse_search_result(r) for r in raw]
        for p in parsed:
            p.setdefault("citation", None)
            p["relevance_score"] = p.get("score", 0)
        filtered = filter_by_relevance(parsed, min_score=0.4)
        return deduplicate_results(filtered)

    @handle_tavily_errors
    async def search_precedents(
        self,
        dispute_type: str,
        facts: str,
        jurisdiction: str = "Minnesota",
        max_results: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Precedent research for conciliation court: dispute type + facts.
        Filters for small claims / conciliation relevance.
        """
        query = f"Minnesota conciliation court {dispute_type} precedent similar to: {facts[:200]}"
        response = await self.search(
            query=query,
            search_depth="advanced",
            max_results=max_results,
            include_domains=self.LEGAL_DOMAINS,
            include_answer=True,
        )
        raw = response.get("results", [])
        parsed = [parse_search_result(r) for r in raw]
        filtered = filter_by_relevance(parsed, min_score=0.5)
        for p in filtered:
            p.setdefault("citation", None)
            p["relevance_score"] = p.get("score", 0)
        return deduplicate_results(filtered)

    @handle_tavily_errors
    async def search_statutes(
        self,
        topic: str,
        statute_reference: Optional[str] = None,
        max_results: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Minnesota statute/rule search (Chapter 491A, revisor, law.cornell).
        """
        query = f"Minnesota Statutes Chapter 491A {topic} {statute_reference or ''}".strip()
        response = await self.search(
            query=query,
            search_depth="basic",
            max_results=max_results,
            include_domains=["www.revisor.mn.gov", "law.cornell.edu"],
        )
        raw = response.get("results", [])
        parsed = [parse_search_result(r) for r in raw]
        return deduplicate_results(parsed)

    @handle_tavily_errors
    async def research_legal_topic(
        self,
        topic: str,
        context: str = "",
        max_results: int = 5,
        include_answer: bool = True,
    ) -> str:
        """
        General legal research: flexible topic + optional context.
        Returns formatted context string via get_search_context for agent consumption.
        """
        q = f"{topic} {context}".strip() or topic
        return await self.get_search_context(
            query=q,
            max_tokens=4000,
            search_depth="basic",
            max_results=max_results,
            include_domains=self.LEGAL_DOMAINS,
        )
