"""
Shared utility functions for agent implementations.
Structured outputs are obtained via OpenAI tool/function calls; see backend.agents.tool_schemas.
"""
import json
import re
from typing import Any, Dict, List

from backend.database.models import MemoryBlock


def truncate_text_for_context(text: str, max_chars: int = 12000) -> str:
    """
    Smart truncation at sentence boundaries to fit OpenAI context window.
    """
    if not text or not isinstance(text, str):
        return ""
    text = text.strip()
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_period = truncated.rfind(".")
    last_newline = truncated.rfind("\n")
    cut = max(last_period, last_newline)
    if cut > max_chars // 2:
        return truncated[: cut + 1]
    return truncated.rstrip() + "..."


def build_facts_summary(fact_blocks: List[MemoryBlock]) -> str:
    """Format fact blocks into a single string for agent consumption."""
    if not fact_blocks:
        return ""
    lines = []
    for b in fact_blocks:
        if b.block_type != "fact":
            continue
        meta = b.metadata_ or {}
        fact_type = meta.get("fact_type", "fact")
        content = (b.content or "").strip()
        if content:
            lines.append(f"- [{fact_type}] {content}")
    return "\n".join(lines) if lines else ""


def build_evidence_summary(evidence_blocks: List[MemoryBlock]) -> str:
    """Format evidence blocks into a single string for agent consumption."""
    if not evidence_blocks:
        return ""
    lines = []
    for b in evidence_blocks:
        if b.block_type != "evidence":
            continue
        meta = b.metadata_ or {}
        evidence_type = meta.get("evidence_type", "document")
        score = meta.get("relevance_score", "")
        content = (b.content or "").strip()
        if content:
            lines.append(f"- [{evidence_type}] {content} (relevance: {score})")
    return "\n".join(lines) if lines else ""


def build_rules_summary(rule_blocks: List[MemoryBlock]) -> str:
    """Format rule blocks into a single string for agent consumption."""
    if not rule_blocks:
        return ""
    lines = []
    for b in rule_blocks:
        if b.block_type != "rule":
            continue
        meta = b.metadata_ or {}
        rule_source = meta.get("rule_source", "rule")
        citation = meta.get("citation", "")
        content = (b.content or "").strip()
        if len(content) > 500:
            content = content[:500] + "..."
        if content:
            lines.append(f"- [{rule_source}] {citation}: {content}")
    return "\n".join(lines) if lines else ""


def build_strategy_summary(strategy_blocks: List[MemoryBlock]) -> str:
    """Format strategy blocks into a single string, grouped by strategy_type."""
    if not strategy_blocks:
        return ""
    by_type: Dict[str, List[MemoryBlock]] = {}
    for b in strategy_blocks:
        if b.block_type != "strategy":
            continue
        meta = b.metadata_ or {}
        st = meta.get("strategy_type", "legal_argument")
        if st not in ("legal_argument", "negotiation", "procedural"):
            st = "legal_argument"
        by_type.setdefault(st, []).append(b)
    # Sort each list by priority (lower first)
    for key in by_type:
        by_type[key].sort(
            key=lambda x: (x.metadata_ or {}).get("priority", 99) if isinstance((x.metadata_ or {}).get("priority"), (int, float)) else 99
        )
    sections = []
    for st in ("legal_argument", "negotiation", "procedural"):
        blocks = by_type.get(st, [])
        if not blocks:
            continue
        lines = []
        for b in blocks:
            content = (b.content or "").strip()
            if content:
                lines.append(f"- {content}")
        if lines:
            sections.append(f"### {st.replace('_', ' ').title()}\n" + "\n".join(lines))
    return "\n\n".join(sections) if sections else ""


def parse_openai_json_response(content: str) -> Dict[str, Any]:
    """
    Extract JSON from OpenAI message content. Strips markdown code blocks if present.
    Raises ValueError if no valid JSON is found.
    """
    if not content or not isinstance(content, str):
        raise ValueError("Empty or invalid content")
    text = content.strip()
    # Strip ```json ... ``` or ``` ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        text = match.group(1).strip()
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("Expected JSON object")
    return data


def validate_memory_block_metadata(
    block_type: str, metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Validate metadata against Pydantic block schemas.
    Returns sanitized metadata dict suitable for MemoryBlock.metadata_.
    """
    if not metadata or not isinstance(metadata, dict):
        return {}
    out: Dict[str, Any] = {}
    if block_type == "fact":
        for key in ("fact_type", "date_occurred", "parties_involved", "confidence_score"):
            if key in metadata:
                out[key] = metadata[key]
        if "fact_type" in out and out["fact_type"] not in ("claim", "counterclaim", "timeline"):
            out["fact_type"] = "claim"
    elif block_type == "evidence":
        for key in (
            "evidence_type",
            "document_id",
            "relevance_score",
            "relevance_rationale",
            "is_document_summary",
            "key_details",
        ):
            if key in metadata:
                out[key] = metadata[key]
        if "evidence_type" in out and out["evidence_type"] not in ("document", "witness", "physical"):
            out["evidence_type"] = "document"
    elif block_type == "rule":
        for key in ("rule_source", "citation", "jurisdiction", "applicability_score"):
            if key in metadata:
                out[key] = metadata[key]
        if "rule_source" in out and out["rule_source"] not in ("statute", "case_law", "court_rule"):
            out["rule_source"] = "statute"
    elif block_type == "question":
        for key in ("question_type", "answered", "answer_content"):
            if key in metadata:
                out[key] = metadata[key]
        if "question_type" in out and out["question_type"] not in ("clarification", "missing_info", "legal_issue"):
            out["question_type"] = "clarification"
    elif block_type == "strategy":
        for key in ("strategy_type", "priority", "dependencies", "confidence_score", "supporting_evidence_ids", "supporting_rule_citations"):
            if key in metadata:
                out[key] = metadata[key]
        if "strategy_type" in out and out["strategy_type"] not in ("legal_argument", "negotiation", "procedural"):
            out["strategy_type"] = "legal_argument"
        if "priority" in out and out["priority"] is not None:
            try:
                out["priority"] = int(out["priority"])
            except (TypeError, ValueError):
                out["priority"] = 1
        if "dependencies" in out and not isinstance(out["dependencies"], list):
            out["dependencies"] = []
        if out.get("dependencies") is not None:
            out["dependencies"] = [str(d) for d in out["dependencies"] if d is not None]
    else:
        out = dict(metadata)
    return out


def calculate_confidence_score(response: Dict[str, Any]) -> float:
    """
    Extract or calculate confidence from LLM output.
    Looks for confidence_score, confidence, or defaults to 0.8.
    """
    if "confidence_score" in response and isinstance(response["confidence_score"], (int, float)):
        v = float(response["confidence_score"])
        return max(0.0, min(1.0, v))
    if "confidence" in response and isinstance(response["confidence"], (int, float)):
        v = float(response["confidence"])
        return max(0.0, min(1.0, v))
    return 0.8
