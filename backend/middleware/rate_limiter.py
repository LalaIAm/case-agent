"""
Rate limiting using SlowAPI. Configurable per-endpoint limits and 429 with Retry-After.
"""
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from backend.config import get_settings

# Limit strings for different endpoint types (per minute)
RATE_READ = "100/minute"
RATE_WRITE = "20/minute"
RATE_AGENT = "5/minute"


def get_limiter() -> Limiter:
    """Return a Limiter instance. Uses in-memory storage. When rate limiting is disabled, still returns a limiter so routes can use @limiter.exempt."""
    return Limiter(key_func=get_remote_address, default_limits=[RATE_READ])


def rate_limit_exceeded_handler(request, exc: RateLimitExceeded):
    """Return 429 with Retry-After and consistent error body."""
    from fastapi.responses import JSONResponse

    request_id = getattr(request.state, "request_id", None) or ""
    detail = getattr(exc, "detail", "Too many requests") or "Too many requests"
    retry_after = getattr(exc, "retry_after", None) or 60
    body = {
        "error": {
            "type": "RateLimitError",
            "message": str(detail),
            "details": {"retry_after": retry_after},
            "request_id": request_id,
        }
    }
    response = JSONResponse(status_code=429, content=body)
    response.headers["Retry-After"] = str(int(retry_after))
    response.headers.setdefault("X-RateLimit-Limit", "0")
    response.headers.setdefault("X-RateLimit-Remaining", "0")
    return response
