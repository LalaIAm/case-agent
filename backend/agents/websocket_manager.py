"""
WebSocket connection management and real-time status broadcasting for agent workflows.
"""
import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import WebSocket
from pydantic import BaseModel

from backend.agents.state import WorkflowState

logger = logging.getLogger(__name__)


class AgentStatusMessage(BaseModel):
    """Pydantic model for agent status WebSocket messages."""

    type: str = "agent_status"
    case_id: str
    agent_name: str
    status: str
    reasoning: Optional[str] = None
    progress: int = 0


class WorkflowUpdateMessage(BaseModel):
    """Pydantic model for workflow state WebSocket messages."""

    type: str = "workflow_update"
    case_id: str
    current_agent: Optional[str] = None
    completed_agents: List[str] = []
    workflow_status: str = "pending"
    error: Optional[str] = None
    progress_percentage: int = 0


class WebSocketManager:
    """Tracks WebSocket connections by case_id and broadcasts agent/workflow updates."""

    def __init__(self) -> None:
        self.active_connections: Dict[UUID, List[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, case_id: UUID) -> None:
        """Register a WebSocket connection for the given case_id."""
        await websocket.accept()
        async with self._lock:
            if case_id not in self.active_connections:
                self.active_connections[case_id] = []
            self.active_connections[case_id].append(websocket)
        logger.info("WebSocket connected for case_id=%s", case_id)

    async def disconnect(self, websocket: WebSocket, case_id: UUID) -> None:
        """Remove a WebSocket connection for the given case_id."""
        async with self._lock:
            if case_id in self.active_connections:
                conns = self.active_connections[case_id]
                if websocket in conns:
                    conns.remove(websocket)
                if not conns:
                    del self.active_connections[case_id]
        try:
            await websocket.close()
        except Exception:
            pass
        logger.info("WebSocket disconnected for case_id=%s", case_id)

    async def broadcast_to_case(self, case_id: UUID, message: dict) -> None:
        """Send message to all connections subscribed to this case."""
        async with self._lock:
            conns = list(self.active_connections.get(case_id, []))
        dead: List[WebSocket] = []
        payload = json.dumps(message)
        for ws in conns:
            try:
                await ws.send_text(payload)
            except Exception as e:
                logger.warning("Failed to send to WebSocket: %s", e)
                dead.append(ws)
        if dead:
            async with self._lock:
                if case_id in self.active_connections:
                    for ws in dead:
                        if ws in self.active_connections[case_id]:
                            self.active_connections[case_id].remove(ws)
                    if not self.active_connections[case_id]:
                        del self.active_connections[case_id]

    def send_agent_status(
        self,
        case_id: UUID,
        agent_name: str,
        status: str,
        reasoning: Optional[str] = None,
        progress: int = 0,
    ) -> Dict[str, Any]:
        """Build agent status message for broadcasting."""
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
        reasoning: Optional[str] = None,
        progress: int = 0,
    ) -> None:
        """Send agent status to all case subscribers."""
        message = self.send_agent_status(
            case_id=case_id,
            agent_name=agent_name,
            status=status,
            reasoning=reasoning,
            progress=progress,
        )
        await self.broadcast_to_case(case_id, message)

    def send_workflow_update(self, case_id: UUID, workflow_state: WorkflowState) -> Dict[str, Any]:
        """Build workflow update message from WorkflowState."""
        total = 5  # AGENT_WORKFLOW length
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
        """Send workflow state to all case subscribers."""
        message = self.send_workflow_update(case_id, workflow_state)
        await self.broadcast_to_case(case_id, message)


# Singleton for use by router and main.
websocket_manager = WebSocketManager()
