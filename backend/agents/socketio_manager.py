"""
Socket.IO server and manager for real-time agent status. Replaces native WebSocket
for compatibility with the frontend Socket.IO client (path /ws/agents, query caseId + token).
"""
import logging
from urllib.parse import parse_qs
from uuid import UUID

import socketio
from jose import JWTError, jwt

from backend.config import get_settings
from backend.database import AsyncSessionLocal
from backend.memory.utils import validate_case_ownership
from backend.agents.websocket_manager import (
    AgentStatusMessage,
    WorkflowUpdateMessage,
)
from backend.agents.state import WorkflowState

logger = logging.getLogger(__name__)

settings = get_settings()
_cors = settings.FRONTEND_URL.split(",") if settings.FRONTEND_URL else ["http://localhost:5173"]

sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=_cors,
    logger=False,
    engineio_logger=False,
)


def _parse_query(environ: dict) -> dict:
    """Extract query string from ASGI scope and return parsed dict."""
    query_string = environ.get("query_string") or environ.get("QUERY_STRING", b"")
    if isinstance(query_string, bytes):
        query_string = query_string.decode("utf-8")
    return parse_qs(query_string)


@sio.event
async def connect(sid: str, environ: dict, auth: dict) -> bool:
    """Validate JWT and case ownership, then join room for case_id."""
    try:
        params = _parse_query(environ)
        case_id_str = (params.get("caseId") or [None])[0]
        token = (params.get("token") or [None])[0]
        if not case_id_str or not token:
            logger.warning("Socket.IO connect missing caseId or token")
            return False
        case_id = UUID(case_id_str)
    except (ValueError, TypeError) as e:
        logger.warning("Socket.IO connect invalid params: %s", e)
        return False

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
        )
        user_id_str = payload.get("sub")
        if not user_id_str:
            return False
        user_id = UUID(user_id_str)
    except (JWTError, ValueError, TypeError):
        return False

    async with AsyncSessionLocal() as db:
        if not await validate_case_ownership(db, case_id, user_id):
            return False

    await sio.enter_room(sid, f"case:{case_id}")
    logger.info("Socket.IO connected sid=%s case_id=%s", sid, case_id)
    return True


@sio.event
async def disconnect(sid: str, reason: str) -> None:
    """Log disconnect; rooms are cleared automatically."""
    logger.info("Socket.IO disconnected sid=%s reason=%s", sid, reason)


class SocketIOManager:
    """Same interface as WebSocketManager but emits over Socket.IO to case rooms."""

    def __init__(self, server: socketio.AsyncServer) -> None:
        self._sio = server

    def send_agent_status(
        self,
        case_id: UUID,
        agent_name: str,
        status: str,
        reasoning: str | None = None,
        progress: int = 0,
    ) -> dict:
        """Build agent status message (same as WebSocketManager)."""
        msg = AgentStatusMessage(
            case_id=str(case_id),
            agent_name=agent_name,
            status=status,
            reasoning=reasoning,
            progress=progress,
        )
        return msg.model_dump()

    async def broadcast_agent_status(
        self,
        case_id: UUID,
        agent_name: str,
        status: str,
        reasoning: str | None = None,
        progress: int = 0,
    ) -> None:
        """Emit agent_status to all clients in the case room."""
        message = self.send_agent_status(
            case_id=case_id,
            agent_name=agent_name,
            status=status,
            reasoning=reasoning,
            progress=progress,
        )
        await self._sio.emit("agent_status", message, room=f"case:{case_id}")

    def send_workflow_update(self, case_id: UUID, workflow_state: WorkflowState) -> dict:
        """Build workflow update message (same as WebSocketManager)."""
        total = 5
        completed = len(workflow_state.completed_agents)
        progress_percentage = int((completed / total) * 100) if total else 0
        msg = WorkflowUpdateMessage(
            case_id=str(case_id),
            current_agent=workflow_state.current_agent,
            completed_agents=workflow_state.completed_agents,
            workflow_status=workflow_state.workflow_status,
            error=workflow_state.error,
            progress_percentage=progress_percentage,
        )
        return msg.model_dump()

    async def broadcast_workflow_update(self, case_id: UUID, workflow_state: WorkflowState) -> None:
        """Emit workflow_update to all clients in the case room."""
        message = self.send_workflow_update(case_id, workflow_state)
        await self._sio.emit("workflow_update", message, room=f"case:{case_id}")


# Singleton used by router, advisor, and tasks (same interface as websocket_manager).
socketio_manager = SocketIOManager(sio)
