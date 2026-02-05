# Tavily Search Integration

Tavily Search integration for the case-agent backend: singleton client, retry logic, async support, specialized legal search methods, result parsing, rate limiting, and agent-friendly formatting.

## Overview

The `TavilySearchService` provides:

- **Singleton client** via `_get_tavily_client()` (cached with `lru_cache`)
- **Exponential backoff** (3 retries, base delay 1s) for search and context calls
- **Async wrappers** using `run_in_executor` for sync Tavily client
- **Legal-specific methods**: case law, precedents, statutes, general legal research
- **Result parsing**: normalize fields, filter by relevance, deduplicate by URL/domain
- **Rate limiting**: configurable RPM with `TavilyRateLimiter`
- **Custom exceptions**: `TavilySearchError`, `TavilyRateLimitError`, `TavilyAPIError`
- **Agent helpers**: `format_search_results_for_agent()`, `summarize_search_results()`

## Usage Examples

### Basic search

```python
from backend.tools.tavily_search import TavilySearchService

service = TavilySearchService()
result = await service.search(
    query="Minnesota conciliation court jurisdiction",
    search_depth="basic",
    max_results=5,
)
# result["query"], result["results"], result["answer"]
```

### Case law search

```python
results = await service.search_case_law(
    query="breach of contract damages",
    jurisdiction="Minnesota",
    max_results=5,
    search_depth="advanced",
)
# List of {title, url, content, citation?, relevance_score}
```

### Precedent research

```python
results = await service.search_precedents(
    dispute_type="landlord-tenant",
    facts="Security deposit not returned after move-out",
    jurisdiction="Minnesota",
    max_results=5,
)
```

### Statute lookup

```python
results = await service.search_statutes(
    topic="jurisdiction",
    statute_reference="491A.01",
    max_results=3,
)
```

### Legal topic research (context for RAG/agent)

```python
context = await service.research_legal_topic(
    topic="conciliation court filing deadline",
    context="Minnesota small claims",
    max_results=5,
    include_answer=True,
)
# Formatted string suitable for LLM context
```

### Format for agent

```python
from backend.tools.tavily_search import format_search_results_for_agent, summarize_search_results

markdown = format_search_results_for_agent(results)
summary = summarize_search_results(results, focus_area="jurisdiction", max_chars=500)
```

## Configuration

Environment variables (optional; defaults in parentheses):

| Variable | Description | Default |
|----------|-------------|---------|
| `TAVILY_API_KEY` | Tavily API key | (required) |
| `TAVILY_SEARCH_DEPTH` | Default search depth: basic, advanced, fast, ultra-fast | `basic` |
| `TAVILY_MAX_RESULTS` | Default max results per search (1–20) | `5` |
| `TAVILY_RATE_LIMIT_RPM` | Rate limit requests per minute | `100` |
| `TAVILY_ENABLE_CACHING` | Enable search result caching | `true` |
| `TAVILY_CACHE_TTL_SECONDS` | Cache TTL in seconds | `3600` |

Add to `.env` (or backend `.env`) as needed. Only `TAVILY_API_KEY` is required.

## Rate Limiting and Cost

- **Rate limiter**: In-memory RPM cap (default 100). When exceeded, `TavilyRateLimitError` is raised with `retry_after_seconds`.
- **Credits**: `basic` depth ≈ 1 credit per request; `advanced` ≈ 2. Use `basic` for high volume and `advanced` for case law/precedents when needed.

## Error Handling

- **TavilySearchError**: Base for all Tavily errors.
- **TavilyRateLimitError**: Rate limit hit; use `retry_after_seconds` to back off.
- **TavilyAPIError**: API/network errors after retries.

Use the `@handle_tavily_errors` decorator (applied on service methods) for consistent logging and exception mapping.

## Best Practices for Legal Queries

- Include jurisdiction (e.g. "Minnesota") in case law and precedent queries.
- Use `search_statutes()` for Chapter 491A and revisor.mn.gov.
- Use `search_precedents()` with concrete dispute type and short fact summary.
- Prefer `get_search_context()` or `research_legal_topic()` when you need a single context string for an agent.

## API Endpoints

When the tools router is mounted at `/api/tools`:

- `POST /api/tools/search` – General Tavily search (body: `TavilySearchRequest`)
- `POST /api/tools/search/case-law` – Case law search (body: `CaseLawSearchRequest`)
- `POST /api/tools/search/precedents` – Precedent research (body: `PrecedentSearchRequest`)
- `POST /api/tools/search/statutes` – Statute lookup (body: `StatuteSearchRequest`)

All require authentication (`current_active_user`).
