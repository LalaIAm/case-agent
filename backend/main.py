"""
FastAPI application entry point for Minnesota Conciliation Court Case Agent.
Socket.IO is mounted at /ws/agents for real-time agent status (see socketio_manager).
"""
import logging
import uuid
from pathlib import Path

import socketio
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError

from backend.config import get_settings
from backend.database.utils import check_db_connection
from backend.exceptions import AppException
from backend.middleware.logging import LoggingMiddleware
from backend.middleware.rate_limiter import get_limiter, rate_limit_exceeded_handler

from backend.agents.socketio_manager import sio, socketio_manager

logger = logging.getLogger(__name__)


def _error_response(
    request: Request,
    error_type: str,
    message: str,
    status_code: int = 500,
    details: dict | None = None,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())
    body = {
        "error": {
            "type": error_type,
            "message": message,
            "details": details or {},
            "request_id": request_id,
        }
    }
    return JSONResponse(status_code=status_code, content=body)


app = FastAPI(title="Minnesota Conciliation Court Case Agent")

settings = get_settings()


app.add_middleware(LoggingMiddleware)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    if not getattr(request.state, "request_id", None):
        request.state.request_id = str(uuid.uuid4())
    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FRONTEND_URL.split(",") if settings.FRONTEND_URL else ["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

limiter = None
if settings.ENABLE_RATE_LIMITING:
    limiter = get_limiter()
    app.state.limiter = limiter
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    logger.warning("HTTPException: %s %s", exc.status_code, exc.detail)
    return _error_response(
        request,
        "HTTPException",
        str(exc.detail) if isinstance(exc.detail, str) else "An error occurred",
        exc.status_code,
        {"detail": exc.detail} if not isinstance(exc.detail, str) else None,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    logger.warning("Request validation error: %s", exc.errors())
    errors = exc.errors()
    details = {"fields": [{"loc": e.get("loc"), "msg": e.get("msg")} for e in errors]}
    return _error_response(
        request,
        "ValidationError",
        "Request validation failed",
        422,
        details,
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.exception("Database error: %s", exc)
    return _error_response(
        request,
        "DatabaseError",
        "A database error occurred. Please try again.",
        500,
        {},
    )


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    level = logging.WARNING if exc.status_code < 500 else logging.ERROR
    logger.log(level, "%s: %s", exc.error_type, exc.message, extra={"details": exc.details})
    return _error_response(
        request,
        exc.error_type,
        exc.message,
        exc.status_code,
        exc.details,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception: %s", exc)
    return _error_response(
        request,
        "InternalServerError",
        "An unexpected error occurred. Please try again.",
        500,
        {},
    )


# Authentication is now active - use current_active_user dependency for protected routes


@app.on_event("startup")
async def startup_event():
    """Verify database connection and create upload/generated doc directories on application startup."""
    await check_db_connection()
    settings = get_settings()
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.GENERATED_DOCS_DIR).mkdir(parents=True, exist_ok=True)


async def _health_check(request: Request):
    """Health check logic (exempt from rate limiting when enabled)."""
    db_ok = await check_db_connection()
    return {"status": "healthy" if db_ok else "degraded", "database": "connected" if db_ok else "disconnected"}


def _root(request: Request):
    """Root endpoint logic."""
    return {
        "name": "Minnesota Conciliation Court Case Agent",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }


if limiter is not None:
    app.get("/health")(limiter.exempt(_health_check))
    app.get("/")(limiter.exempt(_root))
else:
    app.get("/health")(_health_check)
    app.get("/")(_root)


from backend.agents.advisor_router import router as advisor_router
from backend.agents.router import router as agents_router
from backend.auth.router import router as auth_router
from backend.documents.router import router as documents_router
from backend.memory.cases_router import router as cases_router
from backend.memory.router import router as memory_router
from backend.rules.router import router as rules_router
from backend.tools.router import router as tools_router

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(cases_router, prefix="/api/cases", tags=["cases"])
app.include_router(advisor_router, prefix="/api", tags=["advisor"])
app.include_router(memory_router, prefix="/api/memory", tags=["memory"])
app.include_router(rules_router, prefix="/api/rules", tags=["rules"])
app.include_router(tools_router, prefix="/api/tools", tags=["tools"])
app.include_router(documents_router, prefix="/api/documents", tags=["documents"])
app.include_router(agents_router, prefix="/api", tags=["agents"])

# Mount Socket.IO at /ws/agents for frontend socket.io-client (path: '/ws/agents', query: caseId, token)
app = socketio.ASGIApp(sio, app, socketio_path="/ws/agents")
