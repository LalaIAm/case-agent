"""
Tests for agent framework: BaseAgent, state, WebSocketManager, orchestrator, API.
"""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.base_agent import BaseAgent
from backend.agents.state import AgentState, WorkflowState, WorkflowStateManager
from backend.agents.websocket_manager import WebSocketManager
from backend.database.models import AgentRun
from backend.main import app


# --- BaseAgent ---


class MockAgent(BaseAgent):
    @property
    def agent_name(self) -> str:
        return "mock"

    async def execute(self, agent_run_id):
        return {"done": True}


@pytest.mark.asyncio
async def test_base_agent_run_creates_and_updates_agent_run():
    """BaseAgent.run() creates AgentRun with status running, then updates to completed."""
    case_id = uuid4()
    user_id = uuid4()
    db = AsyncMock(spec=AsyncSession)
    run = MagicMock(spec=AgentRun)
    run.id = uuid4()
    run.status = "running"
    run.case_id = case_id
    run.agent_name = "mock"
    run.reasoning = None
    run.result = None
    run.completed_at = None
    run.error_message = None

    async def flush():
        pass

    async def refresh(obj):
        if obj == run:
            obj.status = "completed"
            obj.result = {"done": True}

    db.add = MagicMock()
    db.flush = AsyncMock(side_effect=flush)
    db.refresh = AsyncMock(side_effect=refresh)

    with patch.object(MockAgent, "_create_agent_run", AsyncMock(return_value=run)):
        with patch.object(MockAgent, "_update_agent_run", AsyncMock()):
            agent = MockAgent(db, case_id, user_id)
            result = await agent.run()
    assert result == run
    assert result.status == "completed"


@pytest.mark.asyncio
async def test_base_agent_run_handles_failure():
    """BaseAgent.run() updates AgentRun to failed on execute() exception."""
    case_id = uuid4()
    user_id = uuid4()
    db = AsyncMock(spec=AsyncSession)
    run = MagicMock(spec=AgentRun)
    run.id = uuid4()
    run.status = "running"

    async def refresh(obj):
        if obj == run:
            obj.status = "failed"
            obj.error_message = "expected"

    db.add = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock(side_effect=refresh)

    class FailingAgent(MockAgent):
        async def execute(self, agent_run_id):
            raise ValueError("expected")

    with patch.object(FailingAgent, "_create_agent_run", AsyncMock(return_value=run)):
        with patch.object(FailingAgent, "_update_agent_run", AsyncMock()):
            agent = FailingAgent(db, case_id, user_id)
            with pytest.raises(ValueError, match="expected"):
                await agent.run()


# --- State ---


@pytest.mark.asyncio
async def test_workflow_state_manager_get_state_empty():
    """WorkflowStateManager.get_state() returns pending when no runs."""
    db = AsyncMock(spec=AsyncSession)
    case_id = uuid4()
    result_mock = MagicMock()
    result_mock.scalars.return_value.unique.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=result_mock)

    mgr = WorkflowStateManager(db, case_id)
    state = await mgr.get_state()
    assert state.case_id == case_id
    assert state.workflow_status == "pending"
    assert state.completed_agents == []
    assert state.current_agent is None


@pytest.mark.asyncio
async def test_workflow_state_manager_get_agent_result():
    """WorkflowStateManager.get_agent_result() returns result of latest completed run."""
    db = AsyncMock(spec=AsyncSession)
    case_id = uuid4()
    run = MagicMock()
    run.result = {"key": "value"}
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = run
    db.execute = AsyncMock(return_value=result_mock)

    mgr = WorkflowStateManager(db, case_id)
    out = await mgr.get_agent_result("intake")
    assert out == {"key": "value"}


# --- WebSocketManager ---


def test_websocket_manager_send_agent_status():
    """WebSocketManager.send_agent_status builds correct message dict."""
    mgr = WebSocketManager()
    msg = mgr.send_agent_status(
        case_id=uuid4(),
        agent_name="research",
        status="running",
        reasoning="Thinking...",
        progress=25,
    )
    assert msg["type"] == "agent_status"
    assert msg["agent_name"] == "research"
    assert msg["status"] == "running"
    assert msg["reasoning"] == "Thinking..."
    assert msg["progress"] == 25


def test_websocket_manager_send_workflow_update():
    """WebSocketManager.send_workflow_update builds message from WorkflowState."""
    mgr = WebSocketManager()
    state = WorkflowState(
        case_id=uuid4(),
        current_agent="document",
        completed_agents=["intake", "research"],
        workflow_status="running",
    )
    msg = mgr.send_workflow_update(state.case_id, state)
    assert msg["type"] == "workflow_update"
    assert msg["current_agent"] == "document"
    assert msg["completed_agents"] == ["intake", "research"]
    assert msg["workflow_status"] == "running"


# --- Orchestrator (mocked) ---


@pytest.mark.asyncio
async def test_orchestrator_execute_single_agent():
    """AgentOrchestrator.execute_single_agent runs one agent and returns run."""
    from backend.agents.orchestrator import AgentOrchestrator

    case_id = uuid4()
    user_id = uuid4()
    db = AsyncMock(spec=AsyncSession)
    run = MagicMock(spec=AgentRun)
    run.id = uuid4()
    run.status = "completed"
    run.result = {"ok": True}
    db.flush = AsyncMock()
    db.refresh = AsyncMock()

    with patch("backend.agents.orchestrator.AGENT_CLASSES", {"intake": MockAgent}):
        with patch.object(MockAgent, "_create_agent_run", AsyncMock(return_value=run)):
            with patch.object(MockAgent, "_update_agent_run", AsyncMock()):
                orch = AgentOrchestrator(db, case_id, user_id, websocket_manager=None)
                result = await orch.execute_single_agent("intake")
    assert result == run


@pytest.mark.asyncio
async def test_orchestrator_get_workflow_status():
    """AgentOrchestrator.get_workflow_status returns WorkflowState."""
    from backend.agents.orchestrator import AgentOrchestrator

    case_id = uuid4()
    user_id = uuid4()
    db = AsyncMock(spec=AsyncSession)
    result_mock = MagicMock()
    result_mock.scalars.return_value.unique.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=result_mock)

    orch = AgentOrchestrator(db, case_id, user_id)
    state = await orch.get_workflow_status()
    assert isinstance(state, WorkflowState)
    assert state.case_id == case_id


# --- API endpoints (authenticated) ---


@pytest.mark.asyncio
async def test_agents_execute_requires_auth():
    """POST /api/agents/execute returns 401 without auth."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            "/api/agents/execute",
            json={"case_id": str(uuid4())},
        )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_agents_status_requires_auth():
    """GET /api/agents/status/{case_id} returns 401 without auth."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get(f"/api/agents/status/{uuid4()}")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_agents_cases_runs_requires_auth():
    """GET /api/agents/cases/{case_id}/runs returns 401 without auth."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get(f"/api/agents/cases/{uuid4()}/runs")
    assert r.status_code == 401


# --- IntakeAgent execution (mocked) ---


@pytest.mark.asyncio
async def test_intake_agent_execution():
    """IntakeAgent with mocked case and OpenAI creates fact blocks and returns summary."""
    from backend.agents.concrete_agents import IntakeAgent

    case_id = uuid4()
    user_id = uuid4()
    agent_run_id = uuid4()
    session_id = uuid4()

    db = AsyncMock(spec=AsyncSession)
    case = MagicMock()
    case.id = case_id
    case.description = "Plaintiff paid $500 deposit. Defendant did not complete the work."
    session = MagicMock()
    session.id = session_id

    openai_response = MagicMock()
    openai_response.choices = [MagicMock()]
    openai_response.choices[0].message.content = None
    tool_call = MagicMock()
    tool_call.function = MagicMock()
    tool_call.function.name = "submit_intake"
    tool_call.function.arguments = """{
        "dispute_type": "contract",
        "parties": ["Plaintiff", "Defendant"],
        "timeline_events": [],
        "facts": [
            {"content": "Plaintiff paid $500 deposit", "fact_type": "claim", "date_occurred": "2024-01-15"}
        ],
        "questions": [
            {"content": "What was the agreed completion date?", "question_type": "clarification"}
        ]
    }"""
    openai_response.choices[0].message.tool_calls = [tool_call]

    result_case = MagicMock()
    result_case.scalar_one_or_none.return_value = case
    result_session = MagicMock()
    result_session.scalar_one_or_none.return_value = session
    result_blocks = MagicMock()
    result_blocks.scalars.return_value.unique.return_value.all.return_value = []

    async def execute_side_effect(*args, **kwargs):
        if "Case" in str(args) or (kwargs.get("params") and "case_id" in str(kwargs)):
            return result_case
        if "CaseSession" in str(args):
            return result_session
        return result_blocks

    db.execute = AsyncMock(side_effect=execute_side_effect)
    db.flush = AsyncMock()
    db.add = MagicMock()

    memory = MagicMock()
    memory.get_case_context = AsyncMock(return_value=[])
    memory.create_memory_block = AsyncMock(return_value=MagicMock(id=uuid4()))

    with patch("backend.agents.concrete_agents.get_or_create_session", AsyncMock(return_value=session)):
        with patch.object(IntakeAgent, "_get_memory_manager", return_value=memory):
            with patch.object(IntakeAgent, "_get_openai_client") as mock_client:
                mock_client.return_value.chat.completions.create = AsyncMock(return_value=openai_response)
                with patch.object(IntakeAgent, "_log_reasoning", AsyncMock()):
                    with patch.object(IntakeAgent, "_update_agent_run", AsyncMock()):
                        agent = IntakeAgent(db, case_id, user_id)
                        result = await agent.execute(agent_run_id)

    assert result["dispute_type"] == "contract"
    assert result["facts_extracted"] >= 1
    assert result["questions_generated"] >= 1
    assert "Plaintiff" in result["parties"] or len(result["parties"]) >= 1
    assert memory.create_memory_block.await_count >= 2  # at least one fact, one question


# --- ResearchAgent (mocked) ---


@pytest.mark.asyncio
async def test_research_agent_with_rules():
    """ResearchAgent with mocked rule retriever and Tavily creates rule blocks."""
    from backend.agents.concrete_agents import ResearchAgent

    case_id = uuid4()
    user_id = uuid4()
    agent_run_id = uuid4()
    session_id = uuid4()

    db = AsyncMock(spec=AsyncSession)
    session = MagicMock()
    session.id = session_id

    openai_response = MagicMock()
    openai_response.choices = [MagicMock()]
    openai_response.choices[0].message.content = None
    tool_call = MagicMock()
    tool_call.function = MagicMock()
    tool_call.function.name = "submit_research"
    tool_call.function.arguments = """{
        "research_queries": ["Minnesota conciliation court jurisdiction"],
        "applicable_rules": [
            {"source": "statute", "citation": "MN Stat § 491A.01", "content_summary": "Jurisdiction up to $15,000", "applicability_score": 0.9}
        ],
        "precedents": [],
        "legal_standards": ["Burden of proof on plaintiff"]
    }"""
    openai_response.choices[0].message.tool_calls = [tool_call]

    memory = MagicMock()
    memory.get_case_context = AsyncMock(return_value=[])
    memory.create_memory_block = AsyncMock(return_value=MagicMock(id=uuid4()))

    state_mgr = MagicMock()
    state_mgr.get_agent_result = AsyncMock(return_value={"dispute_type": "contract"})

    hybrid_result = {"static_rules": [{"title": "491A", "content": "Conciliation court rules."}], "case_law": []}

    with patch("backend.agents.concrete_agents.get_or_create_session", AsyncMock(return_value=session)):
        with patch.object(ResearchAgent, "_get_memory_manager", return_value=memory):
            with patch.object(ResearchAgent, "_get_openai_client") as mock_client:
                mock_client.return_value.chat.completions.create = AsyncMock(return_value=openai_response)
                with patch.object(ResearchAgent, "_log_reasoning", AsyncMock()):
                    with patch.object(ResearchAgent, "_update_agent_run", AsyncMock()):
                        with patch("backend.agents.concrete_agents.WorkflowStateManager", return_value=state_mgr):
                            with patch("backend.agents.concrete_agents.RuleRetriever") as mock_rr:
                                with patch("backend.agents.concrete_agents.TavilySearchService") as mock_tavily:
                                    mock_rr.return_value.hybrid_search = AsyncMock(return_value=hybrid_result)
                                    mock_tavily.return_value.search_case_law = AsyncMock(return_value=[])
                                    mock_tavily.return_value.search_precedents = AsyncMock(return_value=[])
                                    agent = ResearchAgent(db, case_id, user_id)
                                    result = await agent.execute(agent_run_id)

    assert result["rules_found"] >= 1
    assert "research_summary" in result


# --- DocumentAgent (mocked) ---


@pytest.mark.asyncio
async def test_document_agent_processing():
    """DocumentAgent with mocked documents creates evidence blocks."""
    from backend.agents.concrete_agents import DocumentAgent

    case_id = uuid4()
    user_id = uuid4()
    agent_run_id = uuid4()
    session_id = uuid4()
    doc_id = uuid4()

    db = AsyncMock(spec=AsyncSession)
    session = MagicMock()
    session.id = session_id
    doc = MagicMock()
    doc.id = doc_id
    doc.filename = "receipt.pdf"
    doc.extracted_text = "Receipt: $500 paid on 2024-01-15."
    doc.processed = False

    result_docs = MagicMock()
    result_docs.scalars.return_value.unique.return_value.all.return_value = [doc]
    result_session = MagicMock()
    result_session.scalar_one_or_none.return_value = session
    result_blocks = MagicMock()
    result_blocks.scalars.return_value.unique.return_value.all.return_value = []

    async def execute_side_effect(*args, **kwargs):
        if "Document" in str(args):
            return result_docs
        if "CaseSession" in str(args):
            return result_session
        return result_blocks

    db.execute = AsyncMock(side_effect=execute_side_effect)
    db.flush = AsyncMock()

    openai_response = MagicMock()
    openai_response.choices = [MagicMock()]
    openai_response.choices[0].message.content = None
    tool_call = MagicMock()
    tool_call.function = MagicMock()
    tool_call.function.name = "submit_document_analysis"
    tool_call.function.arguments = """{
        "evidence_items": [
            {"content": "Receipt shows $500 payment", "evidence_type": "document", "relevance_score": 0.9}
        ],
        "document_summaries": [{"summary": "Payment receipt", "key_details": ["$500", "2024-01-15"]}],
        "relevance_scores": {}
    }"""
    openai_response.choices[0].message.tool_calls = [tool_call]

    memory = MagicMock()
    memory.get_case_context = AsyncMock(return_value=[])
    memory.create_memory_block = AsyncMock(return_value=MagicMock(id=uuid4()))
    memory.search_similar_blocks = AsyncMock(return_value=[])
    memory.link_blocks = AsyncMock(return_value=None)

    with patch("backend.agents.concrete_agents.get_or_create_session", AsyncMock(return_value=session)):
        with patch.object(DocumentAgent, "_get_memory_manager", return_value=memory):
            with patch.object(DocumentAgent, "_get_openai_client") as mock_client:
                mock_client.return_value.chat.completions.create = AsyncMock(return_value=openai_response)
                with patch.object(DocumentAgent, "_log_reasoning", AsyncMock()):
                    with patch.object(DocumentAgent, "_update_agent_run", AsyncMock()):
                        with patch("backend.agents.concrete_agents.EmbeddingService") as mock_emb:
                            mock_emb.return_value.generate_embedding = AsyncMock(return_value=[0.1] * 1536)
                            agent = DocumentAgent(db, case_id, user_id)
                            result = await agent.execute(agent_run_id)

    assert result["documents_analyzed"] == 1
    assert result["evidence_items_extracted"] >= 1
    assert doc.processed is True


# --- Error handling ---


@pytest.mark.asyncio
async def test_agent_error_handling():
    """Agents log errors to AgentRun and raise on OpenAI/API failures."""
    from backend.agents.concrete_agents import IntakeAgent

    case_id = uuid4()
    user_id = uuid4()
    agent_run_id = uuid4()
    session_id = uuid4()

    db = AsyncMock(spec=AsyncSession)
    case = MagicMock()
    case.id = case_id
    case.description = "Some case"
    session = MagicMock()
    session.id = session_id

    result_case = MagicMock()
    result_case.scalar_one_or_none.return_value = case
    result_session = MagicMock()
    result_session.scalar_one_or_none.return_value = session
    result_blocks = MagicMock()
    result_blocks.scalars.return_value.unique.return_value.all.return_value = []

    async def execute_side_effect(*args, **kwargs):
        if "Case" in str(args):
            return result_case
        if "CaseSession" in str(args):
            return result_session
        return result_blocks

    db.execute = AsyncMock(side_effect=execute_side_effect)
    db.flush = AsyncMock()
    memory = MagicMock()
    memory.get_case_context = AsyncMock(return_value=[])

    update_called = []

    async def capture_update(*args, **kwargs):
        if kwargs.get("error_message"):
            update_called.append(kwargs["error_message"])

    with patch("backend.agents.concrete_agents.get_or_create_session", AsyncMock(return_value=session)):
        with patch.object(IntakeAgent, "_get_memory_manager", return_value=memory):
            with patch.object(IntakeAgent, "_get_openai_client") as mock_client:
                mock_client.return_value.chat.completions.create = AsyncMock(
                    side_effect=Exception("OpenAI API error")
                )
                with patch.object(IntakeAgent, "_update_agent_run", side_effect=capture_update):
                    agent = IntakeAgent(db, case_id, user_id)
                    with pytest.raises(Exception, match="OpenAI API error"):
                        await agent.execute(agent_run_id)
    assert any("OpenAI" in str(m) for m in update_called) or len(update_called) >= 1


# --- Memory integration ---


@pytest.mark.asyncio
async def test_agent_memory_integration():
    """Memory blocks created by agents use correct block_type and metadata."""
    from backend.agents.agent_utils import validate_memory_block_metadata

    meta_fact = validate_memory_block_metadata("fact", {
        "fact_type": "claim",
        "date_occurred": "2024-01-15",
        "parties_involved": ["Plaintiff"],
        "confidence_score": 0.9,
    })
    assert meta_fact["fact_type"] == "claim"
    assert meta_fact["confidence_score"] == 0.9

    meta_rule = validate_memory_block_metadata("rule", {
        "rule_source": "statute",
        "citation": "MN Stat § 491A.01",
        "jurisdiction": "Minnesota",
        "applicability_score": 0.8,
    })
    assert meta_rule["rule_source"] == "statute"
    assert meta_rule["jurisdiction"] == "Minnesota"

    meta_evidence = validate_memory_block_metadata("evidence", {
        "evidence_type": "document",
        "document_id": "doc-uuid",
        "relevance_score": 0.85,
    })
    assert meta_evidence["evidence_type"] == "document"
    assert meta_evidence["relevance_score"] == 0.85


# --- Utils ---


def test_calculate_workflow_progress():
    """calculate_workflow_progress returns percentage from completed runs."""
    from backend.agents.utils import calculate_workflow_progress

    runs = [
        MagicMock(agent_name="intake", status="completed"),
        MagicMock(agent_name="research", status="completed"),
    ]
    assert calculate_workflow_progress(runs) == 40  # 2/5 = 40%
    assert calculate_workflow_progress([]) == 0
