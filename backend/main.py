"""
FastAPI application entry point for Minnesota Conciliation Court Case Agent.
"""
import asyncio
from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt

from backend.config import get_settings
from backend.database import AsyncSessionLocal
from backend.database.utils import check_db_connection
from backend.memory.utils import validate_case_ownership

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


# Singleton WebSocket manager for agent status broadcasts
from backend.agents.websocket_manager import websocket_manager

@app.websocket("/ws/agents/{case_id}")
async def agent_status_websocket(
    websocket: WebSocket,
    case_id: UUID,
    token: str = Query(..., alias="token"),
):
    """WebSocket for real-time agent status. Authenticate with JWT in query parameter."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
        )
        user_id_str = payload.get("sub")
        if not user_id_str:
            await websocket.close(code=4001)
            return
        user_id = UUID(user_id_str)
    except (JWTError, ValueError, TypeError):
        await websocket.close(code=4001)
        return

    async with AsyncSessionLocal() as db:
        if not await validate_case_ownership(db, case_id, user_id):
            await websocket.close(code=4003)
            return
    await websocket_manager.connect(websocket, case_id)
    heartbeat_interval = getattr(settings, "WEBSOCKET_HEARTBEAT_INTERVAL", 30)
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=float(heartbeat_interval))
                if data.strip().lower() == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                await websocket.send_text('{"type":"ping"}')
    except WebSocketDisconnect:
        pass
    finally:
        await websocket_manager.disconnect(websocket, case_id)


from backend.agents.router import router as agents_router
from backend.auth.router import router as auth_router
from backend.documents.router import router as documents_router
from backend.memory.cases_router import router as cases_router
from backend.memory.router import router as memory_router
from backend.rules.router import router as rules_router
from backend.tools.router import router as tools_router

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(cases_router, prefix="/api/cases", tags=["cases"])
app.include_router(memory_router, prefix="/api/memory", tags=["memory"])
app.include_router(rules_router, prefix="/api/rules", tags=["rules"])
app.include_router(tools_router, prefix="/api/tools", tags=["tools"])
app.include_router(documents_router, prefix="/api/documents", tags=["documents"])
app.include_router(agents_router, prefix="/api", tags=["agents"])
