"""
Concrete agent implementations. Intake, Research, and Document agents are fully implemented;
Strategy and Drafting remain stubs for orchestrator handoff.
"""
from typing import Any, Dict, List
from uuid import UUID

from sqlalchemy import select

from backend.agents.agent_utils import (
    build_evidence_summary,
    build_facts_summary,
    build_rules_summary,
    build_strategy_summary,
    calculate_confidence_score,
    parse_openai_json_response,
    truncate_text_for_context,
    validate_memory_block_metadata,
)
from backend.agents.base_agent import BaseAgent
from backend.agents.prompts import (
    DOCUMENT_ANALYSIS_SYSTEM_PROMPT,
    DRAFTING_SYSTEM_PROMPT,
    INTAKE_SYSTEM_PROMPT,
    RESEARCH_SYSTEM_PROMPT,
    STRATEGY_SYSTEM_PROMPT,
    build_document_analysis_message,
    build_drafting_user_message,
    build_intake_user_message,
    build_research_user_message,
    build_strategy_user_message,
)
from backend.agents.tool_schemas import (
    DOCUMENT_TOOL_NAME,
    DOCUMENT_TOOLS,
    INTAKE_TOOL_NAME,
    INTAKE_TOOLS,
    RESEARCH_TOOL_NAME,
    RESEARCH_TOOLS,
    parse_tool_call_arguments,
)
from backend.config import get_settings
from backend.database.models import Case, Document, GeneratedDocument
from backend.memory.utils import format_memory_context, get_or_create_session
from backend.tools.tavily_search import (
    TavilySearchService,
    format_search_results_for_agent,
)


# --- IntakeAgent ---


class IntakeAgent(BaseAgent):
    """Extracts case facts, categorizes dispute type, identifies parties and timeline, generates questions."""

    @property
    def agent_name(self) -> str:
        return "intake"

    async def execute(self, agent_run_id: UUID) -> Dict[str, Any]:
        settings = get_settings()
        session = await get_or_create_session(self._db, self._case_id)
        memory = self._get_memory_manager()
        client = self._get_openai_client()
        model = settings.AGENT_MODEL
        max_questions = settings.INTAKE_MAX_QUESTIONS

        # Case description
        result = await self._db.execute(select(Case).where(Case.id == self._case_id))
        case = result.scalar_one_or_none()
        if not case:
            raise ValueError("Case not found")
        case_description = (case.description or "").strip()
        if not case_description:
            await self._log_reasoning(agent_run_id, "No case description; skipping fact extraction.")
            return {
                "dispute_type": "other",
                "facts_extracted": 0,
                "questions_generated": 0,
                "parties": [],
            }

        # Existing context
        existing_blocks = await memory.get_case_context(
            self._case_id, block_types=["fact", "question"], limit=50
        )
        existing_context = format_memory_context(existing_blocks)

        user_message = build_intake_user_message(case_description, existing_context)

        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": INTAKE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                tools=INTAKE_TOOLS,
                tool_choice={"type": "function", "function": {"name": INTAKE_TOOL_NAME}},
                temperature=getattr(settings, "AGENT_TEMPERATURE", 0.7),
            )
        except Exception as e:
            await self._update_agent_run(agent_run_id, error_message=str(e))
            raise

        choice = response.choices[0] if response.choices else None
        if not choice or not getattr(choice.message, "tool_calls", None):
            raise ValueError("Empty or invalid OpenAI response: expected tool call")

        await self._log_reasoning(agent_run_id, "OpenAI response received; parsing tool call arguments.")

        try:
            data = parse_tool_call_arguments(choice.message.tool_calls, INTAKE_TOOL_NAME)
        except ValueError as e:
            await self._update_agent_run(agent_run_id, error_message=str(e))
            raise

        dispute_type = data.get("dispute_type") or "other"
        parties = data.get("parties") or []
        facts_raw = data.get("facts") or []
        questions_raw = data.get("questions") or []

        # Limit questions
        questions_raw = questions_raw[:max_questions]

        # Create fact blocks
        facts_created = 0
        for item in facts_raw:
            if not isinstance(item, dict):
                continue
            content = (item.get("content") or "").strip()
            if not content:
                continue
            fact_type = item.get("fact_type") or "claim"
            if fact_type not in ("claim", "counterclaim", "timeline"):
                fact_type = "claim"
            metadata = validate_memory_block_metadata("fact", {
                "fact_type": fact_type,
                "date_occurred": item.get("date_occurred"),
                "parties_involved": item.get("parties_involved"),
                "confidence_score": calculate_confidence_score(item),
            })
            await memory.create_memory_block(session.id, "fact", content, metadata)
            facts_created += 1

        # Create fact blocks from timeline events
        for item in data.get("timeline_events", []):
            if not isinstance(item, dict):
                continue
            content = (item.get("description") or "").strip()
            if not content:
                continue
            metadata = validate_memory_block_metadata("fact", {
                "fact_type": "timeline",
                "date_occurred": item.get("date"),
                "parties_involved": item.get("parties_involved"),
                "confidence_score": calculate_confidence_score(item),
            })
            await memory.create_memory_block(session.id, "fact", content, metadata)
            facts_created += 1

        # Create question blocks
        questions_created = 0
        for item in questions_raw:
            if not isinstance(item, dict):
                continue
            content = (item.get("content") or "").strip()
            if not content:
                continue
            q_type = item.get("question_type") or "clarification"
            if q_type not in ("clarification", "missing_info", "legal_issue"):
                q_type = "clarification"
            metadata = validate_memory_block_metadata("question", {
                "question_type": q_type,
                "answered": False,
            })
            await memory.create_memory_block(session.id, "question", content, metadata)
            questions_created += 1

        return {
            "dispute_type": dispute_type,
            "facts_extracted": facts_created,
            "questions_generated": questions_created,
            "parties": parties if isinstance(parties, list) else [],
        }


# --- ResearchAgent ---


class ResearchAgent(BaseAgent):
    """Researches Minnesota Conciliation Court rules, case law, and precedents; stores rule blocks."""

    @property
    def agent_name(self) -> str:
        return "research"

    async def execute(self, agent_run_id: UUID) -> Dict[str, Any]:
        settings = get_settings()
        session = await get_or_create_session(self._db, self._case_id)
        memory = self._get_memory_manager()
        client = self._get_openai_client()
        model = settings.AGENT_MODEL
        max_rules = settings.RESEARCH_MAX_RULES

        # Case facts and dispute type
        fact_blocks = await memory.get_case_context(
            self._case_id, block_types=["fact"], limit=50
        )
        facts_summary = build_facts_summary(fact_blocks)

        from backend.agents.state import WorkflowStateManager
        state_mgr = WorkflowStateManager(self._db, self._case_id)
        intake_result = await state_mgr.get_agent_result("intake")
        dispute_type = "other"
        if intake_result and isinstance(intake_result.get("dispute_type"), str):
            dispute_type = intake_result["dispute_type"]

        # Rule retriever and Tavily
        from backend.rules.rule_retriever import RuleRetriever
        rule_retriever = RuleRetriever(self._db)
        tavily_service = TavilySearchService()

        query = f"{dispute_type} Minnesota Conciliation Court rules procedures"
        if facts_summary:
            query = f"{query} {facts_summary[:300]}"

        # Hybrid rule search
        hybrid = await rule_retriever.hybrid_search(
            query, include_static=True, include_case_law=True, limit=max_rules
        )
        static_rules = hybrid.get("static_rules") or []
        case_law = hybrid.get("case_law") or []

        static_rules_text: str
        if static_rules:
            lines = []
            for r in static_rules:
                if isinstance(r, dict):
                    lines.append(f"- {r.get('title', r.get('content', str(r)))}: {r.get('content', '')[:500]}")
                else:
                    lines.append(str(r))
            static_rules_text = "\n".join(lines)
        else:
            static_rules_text = ""

        case_law_results: List[Dict[str, Any]] = []
        try:
            case_law_results = await tavily_service.search_case_law(
                query, jurisdiction="Minnesota", max_results=5
            )
        except Exception:
            pass
        try:
            precedent_results = await tavily_service.search_precedents(
                dispute_type, facts_summary[:500], jurisdiction="Minnesota", max_results=5
            )
            seen_urls = {r.get("url") for r in case_law_results if r.get("url")}
            for r in precedent_results:
                if r.get("url") and r["url"] not in seen_urls:
                    case_law_results.append(r)
                    seen_urls.add(r["url"])
        except Exception:
            pass

        case_law_text = format_search_results_for_agent(case_law_results) if case_law_results else ""
        if case_law:
            for item in case_law:
                if isinstance(item, dict):
                    r = item.get("rule") or item
                    if isinstance(r, dict):
                        case_law_text += f"\n### {r.get('title', '')}\n{r.get('content', '')}\n"

        user_message = build_research_user_message(
            facts_summary, dispute_type, static_rules_text, case_law_text
        )
        await self._log_reasoning(agent_run_id, "Analyzing research results with OpenAI.")

        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": RESEARCH_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                tools=RESEARCH_TOOLS,
                tool_choice={"type": "function", "function": {"name": RESEARCH_TOOL_NAME}},
                temperature=getattr(settings, "AGENT_TEMPERATURE", 0.7),
            )
        except Exception as e:
            await self._update_agent_run(agent_run_id, error_message=str(e))
            raise

        choice = response.choices[0] if response.choices else None
        if not choice or not getattr(choice.message, "tool_calls", None):
            raise ValueError("Empty or invalid OpenAI response: expected tool call")

        try:
            data = parse_tool_call_arguments(choice.message.tool_calls, RESEARCH_TOOL_NAME)
        except ValueError as e:
            await self._update_agent_run(agent_run_id, error_message=str(e))
            raise

        applicable_rules = data.get("applicable_rules") or []
        rules_found = 0
        static_count = 0
        case_law_count = 0

        for item in applicable_rules:
            if not isinstance(item, dict):
                continue
            source = (item.get("source") or "statute").lower()
            if source not in ("statute", "case_law", "court_rule"):
                source = "statute"
            content = (item.get("content_summary") or item.get("content") or str(item))[:2000]
            if not content:
                continue
            metadata = validate_memory_block_metadata("rule", {
                "rule_source": source,
                "citation": item.get("citation"),
                "jurisdiction": "Minnesota",
                "applicability_score": item.get("applicability_score"),
            })
            await memory.create_memory_block(session.id, "rule", content, metadata)
            rules_found += 1
            if source == "case_law":
                case_law_count += 1
            else:
                static_count += 1

        # Store static rules that were returned as relevant
        for r in static_rules[:5]:
            if isinstance(r, dict) and r.get("content"):
                content = (r.get("content") or "")[:2000]
                if content and rules_found < max_rules:
                    metadata = validate_memory_block_metadata("rule", {
                        "rule_source": "statute",
                        "citation": r.get("source") or r.get("title"),
                        "jurisdiction": "Minnesota",
                        "applicability_score": 0.8,
                    })
                    await memory.create_memory_block(session.id, "rule", content, metadata)
                    rules_found += 1
                    static_count += 1

        research_summary = (
            data.get("legal_standards") or []
        )
        if isinstance(research_summary, list):
            research_summary = "; ".join(str(s) for s in research_summary[:5])
        else:
            research_summary = str(research_summary)[:500]

        return {
            "rules_found": rules_found,
            "case_law_count": case_law_count,
            "static_rules_count": static_count,
            "research_summary": research_summary,
        }


# --- DocumentAgent ---


class DocumentAgent(BaseAgent):
    """Analyzes uploaded documents, extracts evidence, links to facts, stores evidence blocks."""

    @property
    def agent_name(self) -> str:
        return "document"

    async def execute(self, agent_run_id: UUID) -> Dict[str, Any]:
        settings = get_settings()
        session = await get_or_create_session(self._db, self._case_id)
        memory = self._get_memory_manager()
        client = self._get_openai_client()
        model = settings.AGENT_MODEL
        batch_size = settings.DOCUMENT_BATCH_SIZE
        max_chars = getattr(settings, "AGENT_CONTEXT_WINDOW", 12000)

        # Unprocessed documents
        result = await self._db.execute(
            select(Document).where(
                Document.case_id == self._case_id,
                Document.processed == False,
            ).limit(batch_size)
        )
        documents = list(result.scalars().unique().all())

        if not documents:
            await self._log_reasoning(agent_run_id, "No unprocessed documents; skipping.")
            return {
                "documents_analyzed": 0,
                "evidence_items_extracted": 0,
                "high_relevance_count": 0,
            }

        fact_blocks = await memory.get_case_context(
            self._case_id, block_types=["fact"], limit=50
        )
        case_facts_summary = build_facts_summary(fact_blocks)

        documents_analyzed = 0
        evidence_items_extracted = 0
        high_relevance_count = 0

        from backend.memory.embeddings import EmbeddingService
        embedding_service = EmbeddingService()

        for doc in documents:
            if not doc.extracted_text or not doc.extracted_text.strip():
                continue
            doc_text = truncate_text_for_context(doc.extracted_text, max_chars=max_chars)
            user_message = build_document_analysis_message(
                doc.filename, doc_text, case_facts_summary
            )
            await self._log_reasoning(
                agent_run_id, f"Analyzing document: {doc.filename}"
            )
            try:
                response = await client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": DOCUMENT_ANALYSIS_SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    tools=DOCUMENT_TOOLS,
                    tool_choice={"type": "function", "function": {"name": DOCUMENT_TOOL_NAME}},
                    temperature=getattr(settings, "AGENT_TEMPERATURE", 0.7),
                )
            except Exception as e:
                await self._update_agent_run(agent_run_id, error_message=str(e))
                raise

            choice = response.choices[0] if response.choices else None
            if not choice or not getattr(choice.message, "tool_calls", None):
                continue

            try:
                data = parse_tool_call_arguments(choice.message.tool_calls, DOCUMENT_TOOL_NAME)
            except ValueError:
                continue

            relevance_scores = data.get("relevance_scores") or {}
            if not isinstance(relevance_scores, dict):
                relevance_scores = {}

            evidence_items = data.get("evidence_items") or []
            for i, item in enumerate(evidence_items):
                if not isinstance(item, dict):
                    continue
                content = (item.get("content") or "").strip()
                if not content:
                    continue
                ev_type = item.get("evidence_type") or "document"
                if ev_type not in ("document", "witness", "physical"):
                    ev_type = "document"
                relevance = item.get("relevance_score")
                if relevance is not None:
                    try:
                        relevance = float(relevance)
                    except (TypeError, ValueError):
                        relevance = 0.7
                else:
                    relevance = 0.7
                if relevance >= 0.7:
                    high_relevance_count += 1
                rationale = relevance_scores.get(str(i)) or relevance_scores.get(i)
                if isinstance(rationale, str):
                    rationale = rationale.strip() or None
                else:
                    rationale = None
                meta_input = {
                    "evidence_type": ev_type,
                    "document_id": str(doc.id),
                    "relevance_score": relevance,
                }
                if rationale:
                    meta_input["relevance_rationale"] = rationale
                metadata = validate_memory_block_metadata("evidence", meta_input)
                block = await memory.create_memory_block(
                    session.id, "evidence", content, metadata
                )
                evidence_items_extracted += 1

                # Link to related fact blocks via semantic search
                similar = await memory.search_similar_blocks(
                    content, case_id=self._case_id, block_types=["fact"], limit=3
                )
                if similar:
                    fact_ids = [b.id for b, _ in similar]
                    await memory.link_blocks(block.id, fact_ids)

            # Store document_summaries as evidence blocks (summary + key_details, metadata: document summary, document_id)
            document_summaries = data.get("document_summaries") or []
            for summ in document_summaries:
                if not isinstance(summ, dict):
                    continue
                summary_text = (summ.get("summary") or "").strip()
                key_details = summ.get("key_details")
                if isinstance(key_details, list):
                    key_details = [str(k).strip() for k in key_details if k]
                else:
                    key_details = []
                content_parts = [summary_text] if summary_text else []
                if key_details:
                    content_parts.append("Key details: " + "; ".join(key_details))
                content = "\n".join(content_parts).strip()
                if not content:
                    continue
                metadata = validate_memory_block_metadata("evidence", {
                    "evidence_type": "document",
                    "document_id": str(doc.id),
                    "is_document_summary": True,
                    "key_details": key_details,
                })
                await memory.create_memory_block(session.id, "evidence", content, metadata)

            doc.processed = True
            try:
                emb = await embedding_service.generate_embedding(doc.extracted_text[:8000])
                doc.embedding = emb
            except Exception:
                pass
            documents_analyzed += 1

        await self._db.flush()

        return {
            "documents_analyzed": documents_analyzed,
            "evidence_items_extracted": evidence_items_extracted,
            "high_relevance_count": high_relevance_count,
        }


# --- StrategyAgent ---


class StrategyAgent(BaseAgent):
    """Analyzes case context and generates strategic recommendations stored as strategy memory blocks."""

    @property
    def agent_name(self) -> str:
        return "strategy"

    async def execute(self, agent_run_id: UUID) -> Dict[str, Any]:
        settings = get_settings()
        session = await get_or_create_session(self._db, self._case_id)
        memory = self._get_memory_manager()
        client = self._get_openai_client()
        model = settings.AGENT_MODEL
        max_chars = getattr(settings, "AGENT_CONTEXT_WINDOW", 12000)

        fact_blocks = await memory.get_case_context(
            self._case_id, block_types=["fact"], limit=50
        )
        evidence_blocks = await memory.get_case_context(
            self._case_id, block_types=["evidence"], limit=50
        )
        rule_blocks = await memory.get_case_context(
            self._case_id, block_types=["rule"], limit=30
        )

        facts_summary = truncate_text_for_context(build_facts_summary(fact_blocks), max_chars=max_chars)
        evidence_summary = truncate_text_for_context(build_evidence_summary(evidence_blocks), max_chars=max_chars)
        rules_summary = truncate_text_for_context(build_rules_summary(rule_blocks), max_chars=max_chars)

        from backend.agents.state import WorkflowStateManager
        state_mgr = WorkflowStateManager(self._db, self._case_id)
        intake_result = await state_mgr.get_agent_result("intake")
        dispute_type = "other"
        if intake_result and isinstance(intake_result.get("dispute_type"), str):
            dispute_type = intake_result["dispute_type"]

        user_message = build_strategy_user_message(
            facts_summary, evidence_summary, rules_summary, dispute_type
        )
        user_message = truncate_text_for_context(user_message, max_chars=max_chars)

        await self._log_reasoning(agent_run_id, "Analyzing case strategy with OpenAI.")

        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": STRATEGY_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                temperature=getattr(settings, "AGENT_TEMPERATURE", 0.7),
            )
        except Exception as e:
            await self._update_agent_run(agent_run_id, error_message=str(e))
            raise

        choice = response.choices[0] if response.choices else None
        if not choice or not getattr(choice.message, "content", None):
            raise ValueError("Empty or invalid OpenAI response: expected JSON content")

        try:
            data = parse_openai_json_response(choice.message.content or "")
        except (ValueError, TypeError) as e:
            await self._update_agent_run(agent_run_id, error_message=str(e))
            raise

        legal_arguments_created = 0
        negotiation_points_created = 0
        procedural_steps_created = 0

        for item in data.get("legal_arguments") or []:
            if not isinstance(item, dict):
                continue
            content = (item.get("content") or "").strip()
            if not content:
                continue
            priority = item.get("priority")
            try:
                priority = int(priority) if priority is not None else 1
            except (TypeError, ValueError):
                priority = 1
            metadata = validate_memory_block_metadata("strategy", {
                "strategy_type": "legal_argument",
                "priority": priority,
                "confidence_score": item.get("confidence_score"),
                "supporting_evidence_ids": item.get("supporting_evidence_ids"),
                "supporting_rule_citations": item.get("supporting_rule_citations"),
            })
            await memory.create_memory_block(session.id, "strategy", content, metadata)
            legal_arguments_created += 1

        for item in data.get("negotiation_points") or []:
            if not isinstance(item, dict):
                continue
            content = (item.get("content") or "").strip()
            if not content:
                continue
            priority = item.get("priority")
            try:
                priority = int(priority) if priority is not None else 1
            except (TypeError, ValueError):
                priority = 1
            metadata = validate_memory_block_metadata("strategy", {
                "strategy_type": "negotiation",
                "priority": priority,
            })
            await memory.create_memory_block(session.id, "strategy", content, metadata)
            negotiation_points_created += 1

        for item in data.get("procedural_steps") or []:
            if not isinstance(item, dict):
                continue
            content = (item.get("content") or "").strip()
            if not content:
                continue
            priority = item.get("priority")
            try:
                priority = int(priority) if priority is not None else 1
            except (TypeError, ValueError):
                priority = 1
            deps = item.get("dependencies")
            if not isinstance(deps, list):
                deps = []
            metadata = validate_memory_block_metadata("strategy", {
                "strategy_type": "procedural",
                "priority": priority,
                "dependencies": [str(d) for d in deps],
            })
            await memory.create_memory_block(session.id, "strategy", content, metadata)
            procedural_steps_created += 1

        return {
            "legal_arguments_created": legal_arguments_created,
            "negotiation_points_created": negotiation_points_created,
            "procedural_steps_created": procedural_steps_created,
            "case_strengths": data.get("case_strengths") or [],
            "case_weaknesses": data.get("case_weaknesses") or [],
            "burden_of_proof_analysis": (data.get("burden_of_proof_analysis") or "").strip(),
            "recommended_approach": (data.get("recommended_approach") or "").strip(),
        }


# --- DraftingAgent ---


class DraftingAgent(BaseAgent):
    """Synthesizes case context into court-ready documents stored in GeneratedDocument."""

    @property
    def agent_name(self) -> str:
        return "drafting"

    async def execute(self, agent_run_id: UUID) -> Dict[str, Any]:
        settings = get_settings()
        session = await get_or_create_session(self._db, self._case_id)
        memory = self._get_memory_manager()
        client = self._get_openai_client()
        model = settings.AGENT_MODEL
        max_chars = getattr(settings, "AGENT_CONTEXT_WINDOW", 12000)

        fact_blocks = await memory.get_case_context(
            self._case_id, block_types=["fact"], limit=100
        )
        evidence_blocks = await memory.get_case_context(
            self._case_id, block_types=["evidence"], limit=100
        )
        rule_blocks = await memory.get_case_context(
            self._case_id, block_types=["rule"], limit=50
        )
        strategy_blocks = await memory.get_case_context(
            self._case_id, block_types=["strategy"], limit=50
        )

        facts_summary = truncate_text_for_context(build_facts_summary(fact_blocks), max_chars=max_chars)
        evidence_summary = truncate_text_for_context(build_evidence_summary(evidence_blocks), max_chars=max_chars)
        rules_summary = truncate_text_for_context(build_rules_summary(rule_blocks), max_chars=max_chars)
        strategy_summary = truncate_text_for_context(build_strategy_summary(strategy_blocks), max_chars=max_chars)

        result = await self._db.execute(select(Case).where(Case.id == self._case_id))
        case = result.scalar_one_or_none()
        if not case:
            raise ValueError("Case not found")
        case_title = (case.title or "").strip() or "Untitled Case"

        from backend.agents.state import WorkflowStateManager
        state_mgr = WorkflowStateManager(self._db, self._case_id)
        intake_result = await state_mgr.get_agent_result("intake")
        dispute_type = "other"
        parties: List[str] = []
        if intake_result:
            if isinstance(intake_result.get("dispute_type"), str):
                dispute_type = intake_result["dispute_type"]
            p = intake_result.get("parties")
            if isinstance(p, list):
                parties = [str(x) for x in p]

        user_message = build_drafting_user_message(
            case_title, facts_summary, evidence_summary, rules_summary,
            strategy_summary, dispute_type, parties,
        )
        user_message = truncate_text_for_context(user_message, max_chars=max_chars)

        await self._log_reasoning(agent_run_id, "Generating court documents with OpenAI.")

        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": DRAFTING_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                temperature=getattr(settings, "AGENT_TEMPERATURE", 0.7),
            )
        except Exception as e:
            await self._update_agent_run(agent_run_id, error_message=str(e))
            raise

        choice = response.choices[0] if response.choices else None
        if not choice or not getattr(choice.message, "content", None):
            raise ValueError("Empty or invalid OpenAI response: expected JSON content")

        try:
            data = parse_openai_json_response(choice.message.content or "")
        except (ValueError, TypeError) as e:
            await self._update_agent_run(agent_run_id, error_message=str(e))
            raise

        doc_ids: Dict[str, Any] = {}
        claim_amount = None

        stmt = data.get("statement_of_claim")
        if isinstance(stmt, dict) and (stmt.get("full_text") or "").strip():
            full_text = (stmt.get("full_text") or "").strip()
            gd = GeneratedDocument(
                case_id=self._case_id,
                document_type="statement_of_claim",
                content=full_text,
                version=1,
            )
            self._db.add(gd)
            await self._db.flush()
            doc_ids["statement_of_claim_id"] = str(gd.id)
            if stmt.get("claim_amount") is not None:
                claim_amount = stmt.get("claim_amount")

        hearing = data.get("hearing_script")
        if isinstance(hearing, dict) and (hearing.get("full_text") or "").strip():
            full_text = (hearing.get("full_text") or "").strip()
            gd = GeneratedDocument(
                case_id=self._case_id,
                document_type="hearing_script",
                content=full_text,
                version=1,
            )
            self._db.add(gd)
            await self._db.flush()
            doc_ids["hearing_script_id"] = str(gd.id)

        advice = data.get("legal_advice")
        if isinstance(advice, dict) and (advice.get("full_text") or "").strip():
            full_text = (advice.get("full_text") or "").strip()
            gd = GeneratedDocument(
                case_id=self._case_id,
                document_type="advice",
                content=full_text,
                version=1,
            )
            self._db.add(gd)
            await self._db.flush()
            doc_ids["legal_advice_id"] = str(gd.id)

        documents_generated = len(doc_ids)
        out: Dict[str, Any] = {
            "documents_generated": documents_generated,
            **doc_ids,
        }
        if claim_amount is not None:
            out["claim_amount"] = claim_amount
        return out


AGENT_CLASSES: Dict[str, type] = {
    "intake": IntakeAgent,
    "research": ResearchAgent,
    "document": DocumentAgent,
    "strategy": StrategyAgent,
    "drafting": DraftingAgent,
}
