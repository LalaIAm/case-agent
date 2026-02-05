"""
Request logging middleware: method, path, status, duration, correlation ID.
"""
import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Log each request with correlation_id, method, path, status, duration. Log body for errors (sanitized)."""

    async def dispatch(self, request: Request, call_next) -> Response:
        correlation_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())
        if not getattr(request.state, "request_id", None):
            request.state.request_id = correlation_id
        method = request.method
        path = request.url.path
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        status = response.status_code
        user_id = getattr(request.state, "user_id", None) if hasattr(request.state, "user_id") else None
        log_extra = {"correlation_id": correlation_id, "method": method, "path": path, "status": status, "duration_ms": round(duration_ms, 2)}
        if user_id:
            log_extra["user_id"] = str(user_id)
        if status >= 500:
            logger.error("Request failed: %s %s %s %.0fms", method, path, status, duration_ms, extra=log_extra)
        elif status >= 400:
            logger.warning("Request client error: %s %s %s %.0fms", method, path, status, duration_ms, extra=log_extra)
        else:
            logger.info("Request: %s %s %s %.0fms", method, path, status, duration_ms, extra=log_extra)
        return response
