# Agent Architecture

Overview of the multi-agent framework for the Minnesota Conciliation Court Case Agent: workflow, responsibilities, memory block schemas, and integration points.

## Architecture and Workflow

Agents are orchestrated by `AgentOrchestrator`, which runs them in sequence: **Intake → Research → Document → Strategy → Drafting**. Each agent receives an `agent_run_id` for logging and returns a result dict that is stored on `AgentRun` and passed to the next agent via `WorkflowStateManager.get_agent_result()`.

- **BaseAgent**: Abstract base providing OpenAI client, memory manager access, AgentRun creation/update, and `_log_reasoning()` for real-time reasoning updates.
- **Orchestrator**: Drives the workflow, broadcasts status over WebSocket, and persists state via AgentRun records.
- **WebSocketManager**: Sends agent status and workflow updates to connected clients per case.

## Agent Responsibilities

### IntakeAgent

- **Role**: Legal intake specialist for Minnesota Conciliation Court cases.
- **Responsibilities**:
  - Extract case facts from the case description and initial input.
  - Categorize dispute type (contract, property damage, debt collection, landlord-tenant, consumer, personal injury, other).
  - Identify parties and timeline.
  - Generate clarifying questions for missing information (capped by `INTAKE_MAX_QUESTIONS`).
- **Output**: Result dict with `dispute_type`, `facts_extracted`, `questions_generated`, `parties`.
- **Memory**: Creates `fact` and `question` blocks with metadata aligned to `FactBlock` and `QuestionBlock` schemas.

### ResearchAgent

- **Role**: Legal research specialist for Minnesota small claims / conciliation court.
- **Responsibilities**:
  - Retrieve applicable Minnesota Conciliation Court rules (Chapter 491A) via `RuleRetriever.hybrid_search()`.
  - Search case law and precedents via `TavilySearchService.search_case_law()` and `search_precedents()`.
  - Identify legal standards and burden of proof.
  - Store findings as `rule` memory blocks.
- **Output**: Result dict with `rules_found`, `case_law_count`, `static_rules_count`, `research_summary`.
- **Memory**: Creates `rule` blocks with metadata: `rule_source` (statute/case_law/court_rule), `citation`, `jurisdiction`, `applicability_score`.

### DocumentAgent

- **Role**: Legal document analyst for small claims cases.
- **Responsibilities**:
  - Analyze uploaded documents (contracts, receipts, correspondence, photos) with `extracted_text` available.
  - Extract key evidence and assess relevance.
  - Link evidence blocks to related fact blocks via semantic search and `memory.link_blocks()`.
  - Mark documents as `processed` and optionally store document embeddings.
- **Output**: Result dict with `documents_analyzed`, `evidence_items_extracted`, `high_relevance_count`.
- **Memory**: Creates `evidence` blocks with metadata: `evidence_type`, `document_id`, `relevance_score`; links to fact blocks for traceability.

### StrategyAgent and DraftingAgent

- Currently stubs; return a simple completion message. Intended for strategy development and document drafting in a later phase.

## Memory Block Structure Reference

| Block Type | Metadata Fields | Example Content |
|------------|-----------------|-----------------|
| **fact** | `fact_type` (claim/counterclaim/timeline), `date_occurred`, `parties_involved`, `confidence_score` | "Plaintiff paid $500 deposit on 2024-01-15" |
| **evidence** | `evidence_type` (document/witness/physical), `document_id`, `relevance_score`, `related_blocks` | "Receipt shows payment of $500 to defendant" |
| **rule** | `rule_source` (statute/case_law/court_rule), `citation`, `jurisdiction`, `applicability_score` | "MN Stat § 491A.01: Conciliation court has jurisdiction up to $15,000" |
| **question** | `question_type` (clarification/missing_info/legal_issue), `answered`, `answer_content` | "What was the agreed-upon completion date for the work?" |

Schemas are defined in `backend.memory.case_blocks` (FactBlock, EvidenceBlock, RuleBlock, QuestionBlock). Metadata is validated with `validate_memory_block_metadata()` in `backend.agents.agent_utils` before persisting.

## Integration Points

1. **Session management**: All agents use `get_or_create_session(db, case_id)` from `backend.memory.utils` to obtain `session_id` for memory block creation.

2. **Memory manager**: Agents use `self._get_memory_manager()` (from BaseAgent), which returns a `MemoryManager(self._db)`. Key methods:
   - `get_case_context(case_id, block_types=..., limit=...)`
   - `create_memory_block(session_id, block_type, content, metadata)`
   - `search_similar_blocks(query, case_id=..., block_types=..., limit=...)`
   - `link_blocks(block_id, related_block_ids)`

3. **OpenAI client**: Agents use `self._get_openai_client()` from BaseAgent; model and temperature come from `config.AGENT_MODEL` and `config.AGENT_TEMPERATURE`.

4. **Rules system**: ResearchAgent uses `RuleRetriever(self._db)` from `backend.rules.rule_retriever` and calls `hybrid_search(query, include_static=True, include_case_law=True, limit=...)`.

5. **Tavily search**: ResearchAgent uses `TavilySearchService()` from `backend.tools.tavily_search` for `search_case_law()` and `search_precedents()`. Results are formatted with `format_search_results_for_agent()` for inclusion in prompts.

6. **Logging**: Agents call `self._log_reasoning(agent_run_id, text)` to update `AgentRun.reasoning` in real time.

7. **Result format**: Each agent returns a `Dict[str, Any]` with summary statistics and key findings for the orchestrator and downstream agents.

## Configuration

Agent-related settings in `backend.config`:

- `AGENT_MODEL`, `AGENT_TEMPERATURE`, `AGENT_MAX_RETRIES`, `AGENT_TIMEOUT_SECONDS`
- `INTAKE_MAX_QUESTIONS`, `RESEARCH_MAX_RULES`, `DOCUMENT_BATCH_SIZE`, `AGENT_CONTEXT_WINDOW`
- Tavily: `TAVILY_SEARCH_DEPTH`, `TAVILY_MAX_RESULTS`, `TAVILY_RATE_LIMIT_RPM`, etc.

## Prompts and Utilities

- **Prompts**: Centralized in `backend.agents.prompts` (`INTAKE_SYSTEM_PROMPT`, `RESEARCH_SYSTEM_PROMPT`, `DOCUMENT_ANALYSIS_SYSTEM_PROMPT`) and helper builders (`build_intake_user_message`, `build_research_user_message`, `build_document_analysis_message`).
- **Utilities**: `backend.agents.agent_utils` provides `truncate_text_for_context()`, `build_facts_summary()`, `validate_memory_block_metadata()`, `calculate_confidence_score()`. Structured outputs use OpenAI tool/function schemas in `backend.agents.tool_schemas`; agents pass `tools` and `tool_choice` to `chat.completions.create` and parse arguments from `tool_calls`.

## Troubleshooting

- **Empty or invalid tool call from OpenAI**: Agents use forced tool calls (`tool_choice`). If the response has no `tool_calls`, check model support for tools and prompts that instruct calling the correct function. Arguments are parsed via `parse_tool_call_arguments()` in `tool_schemas`.
- **No case description**: IntakeAgent returns early with default values; ensure `Case.description` is set before running the workflow.
- **Tavily rate limits**: `TavilySearchService` uses rate limiting and retries; on persistent 429s, reduce request frequency or increase `TAVILY_RATE_LIMIT_RPM` if your plan allows.
- **Document agent skips documents**: Only documents with `extracted_text` and `processed == False` are processed; ensure extraction runs before the document agent.
- **Memory blocks not linked**: DocumentAgent links evidence to facts via `search_similar_blocks`; ensure fact blocks exist (IntakeAgent run first) and embeddings are generated.

## Examples of Agent Outputs

- **Intake**: `{"dispute_type": "contract", "facts_extracted": 3, "questions_generated": 2, "parties": ["Plaintiff", "Defendant"]}`
- **Research**: `{"rules_found": 5, "case_law_count": 2, "static_rules_count": 3, "research_summary": "Burden of proof on plaintiff; jurisdiction under $15,000."}`
- **Document**: `{"documents_analyzed": 2, "evidence_items_extracted": 4, "high_relevance_count": 3}`
