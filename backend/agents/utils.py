"""
Helper functions for agent operations: validation, context, prompts, progress.
"""
from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from backend.agents.orchestrator import AGENT_WORKFLOW
from backend.database.models import AgentRun


async def validate_agent_prerequisites(
    db: AsyncSession,
    case_id: UUID,
    agent_name: str,
) -> bool:
    """
    Check if required previous agents have completed successfully and necessary data exists.
    """
    workflow = AGENT_WORKFLOW
    if agent_name not in workflow:
        return False
    idx = workflow.index(agent_name)
    if idx == 0:
        return True
    required = workflow[:idx]
    result = await db.execute(
        select(AgentRun)
        .where(
            AgentRun.case_id == case_id,
            AgentRun.agent_name.in_(required),
            AgentRun.status == "completed",
        )
    )
    runs = result.scalars().unique().all()
    completed_names = {r.agent_name for r in runs}
    return all(name in completed_names for name in required)


async def get_agent_context(
    db: AsyncSession,
    case_id: UUID,
    agent_name: str,
) -> Dict[str, Any]:
    """
    Retrieve relevant memory blocks, previous agent results, and case context.
    """
    from backend.memory.memory_manager import MemoryManager
    manager = MemoryManager(db)
    blocks = await manager.get_case_context(case_id, limit=50)
    from backend.agents.state import WorkflowStateManager
    state_mgr = WorkflowStateManager(db, case_id)
    state = await state_mgr.get_state()
    return {
        "memory_blocks": blocks,
        "previous_results": state.agent_results,
        "completed_agents": state.completed_agents,
    }


def format_agent_prompt(agent_name: str, context: Dict[str, Any]) -> str:
    """
    Build agent-specific prompts with context injection and relevant rules/memory.
    """
    parts = [f"You are the {agent_name} agent. Use the following context.\n\n"]
    if context.get("memory_blocks"):
        parts.append("## Memory\n")
        for b in context["memory_blocks"][:20]:
            parts.append(f"- [{b.block_type}] {b.content[:500]}\n")
        parts.append("\n")
    if context.get("previous_results"):
        parts.append("## Previous agent results\n")
        for name, data in context["previous_results"].items():
            parts.append(f"- {name}: {str(data)[:300]}\n")
    return "".join(parts)


def parse_agent_response(response: str, agent_name: str) -> Dict[str, Any]:
    """
    Extract structured data from agent responses and validate format.
    """
    # Minimal parsing; real implementation could use JSON or structured output.
    return {"raw_response": response[:10000], "agent": agent_name}


def calculate_workflow_progress(agent_runs: List[AgentRun]) -> int:
    """Compute percentage based on completed agents in workflow."""
    if not agent_runs:
        return 0
    total = len(AGENT_WORKFLOW)
    completed_names = set()
    for run in agent_runs:
        if run.status == "completed" and run.agent_name in AGENT_WORKFLOW:
            completed_names.add(run.agent_name)
    return int((len(completed_names) / total) * 100) if total else 0
