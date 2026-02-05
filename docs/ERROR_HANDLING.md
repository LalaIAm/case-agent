# Error Handling

## Overview

The API uses a consistent error response format and custom exception types. All errors return JSON with a common structure.

## Error response format

All error responses follow this shape:

```json
{
  "error": {
    "type": "ErrorType",
    "message": "Human-readable message",
    "details": {},
    "request_id": "uuid-for-support"
  }
}
```

- **type**: Machine-readable error type (e.g. `ValidationError`, `CaseNotFoundError`).
- **message**: Short message suitable for UI or logs.
- **details**: Optional extra data (e.g. `retry_after` for 429, `fields` for 422).
- **request_id**: Unique ID for the request; use when contacting support or searching logs.

## Custom exception types

| Exception             | Status | When used |
|-----------------------|--------|-----------|
| `CaseNotFoundError`  | 404    | Case or session not found |
| `DocumentNotFoundError` | 404  | Document or generated document not found |
| `UnauthorizedError`   | 403    | User not allowed to access resource |
| `ValidationError`     | 422    | Request validation failed (beyond Pydantic) |
| `RateLimitError`      | 429    | Too many requests |
| `AgentExecutionError` | 500    | Agent run failed |

## HTTP and validation errors

- **HTTPException**: Converted to the same JSON shape; `detail` is in `error.message` and `error.details.detail`.
- **RequestValidationError** (Pydantic): Returned as 422 with `error.details.fields` as a list of `{ "loc": [...], "msg": "..." }`.

## Error codes (type) for clients

Clients can branch on `error.type`:

- `ValidationError` – show field-level errors from `details.fields`.
- `RateLimitError` – show “Too many requests” and optionally `details.retry_after` (seconds).
- `CaseNotFoundError` / `DocumentNotFoundError` – show “Not found” and optional navigation.
- `UnauthorizedError` – prompt re-login or show “Access denied”.
- `DatabaseError` / `InternalServerError` – show generic “Something went wrong” and optionally `request_id` for support.

## Retry policies (agents)

Agent runs use a retry policy (see `backend/agents/retry_policy.py`):

- **Retryable**: `TimeoutError`, `ConnectionError`, rate-limit–style messages.
- **Backoff**: Exponential backoff with jitter between attempts.
- **Timeout**: Each agent run is wrapped with `asyncio.wait_for` using `AGENT_TIMEOUT_SECONDS` from config.

## Configuration

Relevant settings in `backend/config.py`:

- `ENABLE_RATE_LIMITING`: Turn rate limiting on/off.
- `ERROR_INCLUDE_TRACEBACK`: Include traceback in error responses (development only).
- `LOG_LEVEL`: Logging level.
- `SENTRY_DSN`: Optional Sentry DSN for server-side error tracking.
