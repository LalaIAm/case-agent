"""
FastAPI application entry point for Minnesota Conciliation Court Case Agent.
Socket.IO is mounted at /ws/agents for real-time agent status (see socketio_manager).
"""
from pathlib import Path

import socketio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import get_settings
from backend.database.utils import check_db_connection

from backend.agents.socketio_manager import sio, socketio_manager

app = FastAPI(title="Minnesota Conciliation Court Case Agent")

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FRONTEND_URL.split(",") if settings.FRONTEND_URL else ["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Authentication is now active - use current_active_user dependency for protected routes


@app.on_event("startup")
async def startup_event():
    """Verify database connection and create upload/generated doc directories on application startup."""
    await check_db_connection()
    settings = get_settings()
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    Path(settings.GENERATED_DOCS_DIR).mkdir(parents=True, exist_ok=True)


@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers and monitoring."""
    db_ok = await check_db_connection()
    return {"status": "healthy" if db_ok else "degraded", "database": "connected" if db_ok else "disconnected"}


@app.get("/")
def root():
    """Root endpoint returning API information."""
    return {
        "name": "Minnesota Conciliation Court Case Agent",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }


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
