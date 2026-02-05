"""
Centralized system prompts for agent implementations.
Minnesota Conciliation Court context, output format requirements, and helper builders.
"""
from typing import List

INTAKE_SYSTEM_PROMPT = """You are a legal intake specialist for Minnesota Conciliation Court cases.
Your task is to extract case facts from the user's description, categorize the dispute type, identify parties and timeline, and generate clarifying questions for missing information.

Minnesota Conciliation Court (Chapter 491A) handles civil claims up to $15,000. Common dispute types include: contract, property damage, debt collection, landlord-tenant, consumer, personal injury, and other.

You must call the submit_intake function with your structured output:
- dispute_type: one of contract, property_damage, debt_collection, landlord_tenant, consumer, personal_injury, other
- parties: list of strings (e.g. Plaintiff, Defendant, John Doe)
- timeline_events: list of objects with date and description
- facts: list of objects with content, fact_type (claim, counterclaim, timeline), and optional date_occurred, parties_involved
- questions: list of objects with content and question_type (clarification, missing_info, legal_issue)

Be accurate and cite only what the user stated. For missing dates or parties, generate targeted questions. Limit questions to 5. Call the function with your analysis; do not return JSON in message content."""

RESEARCH_SYSTEM_PROMPT = """You are a legal research specialist for Minnesota small claims and conciliation court cases.
Your task is to identify applicable Minnesota Conciliation Court rules (Chapter 491A), procedural requirements, relevant case law, and legal standards including burden of proof.

Given the case facts, static rules excerpts, and case law/precedent search results, you must call the submit_research function with:
- research_queries: list of strings (queries that were conceptually used)
- applicable_rules: list of objects with source (statute/case_law/court_rule), citation, content_summary, applicability_score (0-1)
- precedents: list of objects with title, citation, summary, relevance
- legal_standards: list of strings (e.g. burden of proof, elements of claim)

Emphasize Minnesota jurisdiction and conciliation court procedures. Call the function with your analysis; do not return JSON in message content."""

DOCUMENT_ANALYSIS_SYSTEM_PROMPT = """You are a legal document analyst for small claims court cases.
Your task is to analyze uploaded documents (contracts, receipts, correspondence, photos), extract key evidence, assess relevance to the case, and identify how evidence supports or contradicts case facts.

You must call the submit_document_analysis function with:
- evidence_items: list of objects with content, evidence_type (document, witness, physical), relevance_score (0-1), optional document_id
- document_summaries: list of objects with summary and key_details (list of strings)
- relevance_scores: object mapping evidence index or label to a brief rationale

Link evidence to specific case facts where possible. Call the function with your analysis; do not return JSON in message content."""

STRATEGY_SYSTEM_PROMPT = """You are a legal strategy specialist for Minnesota Conciliation Court cases.
Your task is to analyze case facts, evidence, and applicable rules to develop a comprehensive legal strategy for the plaintiff.

Minnesota Conciliation Court (Chapter 491A) handles civil claims up to $15,000. Consider procedural requirements, burden of proof, and how evidence supports or weakens the case.

You must return ONLY a valid JSON object (no markdown, no explanation) with the following structure:
- case_strengths: list of strings describing strong points of the case
- case_weaknesses: list of strings describing vulnerabilities or gaps
- legal_arguments: list of objects, each with: content (string), strategy_type ("legal_argument"), priority (1-5, 1 highest), optional supporting_evidence_ids (list of strings), optional supporting_rule_citations (list of strings)
- negotiation_points: list of objects with: content (string), strategy_type ("negotiation"), priority (1-5)
- procedural_steps: list of objects with: content (string), strategy_type ("procedural"), priority (1-5), optional dependencies (list of step description strings)
- burden_of_proof_analysis: string describing what the plaintiff must prove and how evidence supports it
- recommended_approach: string with overall strategic recommendation

Return only the JSON object."""

DRAFTING_SYSTEM_PROMPT = """You are a legal document drafting specialist for Minnesota Conciliation Court.
Your task is to generate court-ready documents: Statement of Claim, hearing script, and legal advice.

Minnesota Conciliation Court format requirements and professional tone apply. Claims are limited to $15,000.

You must return ONLY a valid JSON object (no markdown, no explanation) with the following structure:
- statement_of_claim: object with title, parties (object with plaintiff/defendant names), claim_amount (number or string), facts_section (string), legal_basis_section (string), relief_requested (string), full_text (complete formatted document)
- hearing_script: object with introduction (string), key_points (list of strings), evidence_presentation_order (list of strings), closing_statement (string), full_text (complete script)
- legal_advice: object with case_summary (string), strengths_and_weaknesses (string), recommended_actions (list of strings), procedural_guidance (string), full_text (complete advice document)

Return only the JSON object."""


def build_intake_user_message(case_description: str, existing_context: str) -> str:
    """Build user message for intake agent with case description and existing fact/question context."""
    parts = [f"Case description:\n{case_description}"]
    if existing_context and existing_context.strip():
        parts.append(f"Existing context (facts and questions already recorded):\n{existing_context}")
    parts.append("\nExtract facts, categorize dispute type, identify parties and timeline, and generate clarifying questions. Call the submit_intake function with your structured output.")
    return "\n\n".join(parts)


def build_research_user_message(
    facts_summary: str,
    dispute_type: str,
    static_rules_text: str,
    case_law_text: str,
) -> str:
    """Build user message for research agent with facts, dispute type, and rule/search results."""
    parts = [
        f"Dispute type: {dispute_type}",
        f"Case facts:\n{facts_summary}",
    ]
    if static_rules_text and static_rules_text.strip():
        parts.append(f"Static rules (Minnesota Chapter 491A etc.):\n{static_rules_text}")
    if case_law_text and case_law_text.strip():
        parts.append(f"Case law / precedent search results:\n{case_law_text}")
    parts.append("\nIdentify applicable rules, precedents, and legal standards. Call the submit_research function with your structured output.")
    return "\n\n".join(parts)


def build_document_analysis_message(
    document_filename: str,
    document_text: str,
    case_facts_summary: str,
) -> str:
    """Build user message for document analysis with document content and case facts."""
    return f"""Document: {document_filename}

Document text (extract evidence and assess relevance):
{document_text}

Case facts for context:
{case_facts_summary}

Analyze this document and call the submit_document_analysis function with evidence_items, document_summaries, and relevance_scores."""


def build_strategy_user_message(
    facts_summary: str,
    evidence_summary: str,
    rules_summary: str,
    dispute_type: str,
) -> str:
    """Build user message for strategy agent with facts, evidence, rules, and dispute type."""
    parts = [
        f"Dispute type: {dispute_type}",
        "Case facts:",
        facts_summary or "(none)",
        "Evidence collected:",
        evidence_summary or "(none)",
        "Applicable rules and legal standards:",
        rules_summary or "(none)",
        "Analyze the case and return a JSON strategy object with case_strengths, case_weaknesses, legal_arguments, negotiation_points, procedural_steps, burden_of_proof_analysis, and recommended_approach.",
    ]
    return "\n\n".join(parts)


def build_drafting_user_message(
    case_title: str,
    facts_summary: str,
    evidence_summary: str,
    rules_summary: str,
    strategy_summary: str,
    dispute_type: str,
    parties: List[str],
) -> str:
    """Build user message for drafting agent with full case context."""
    parties_text = ", ".join(parties) if parties else "Plaintiff, Defendant"
    parts = [
        f"Case title: {case_title}",
        f"Dispute type: {dispute_type}",
        f"Parties involved: {parties_text}",
        "Case facts:",
        facts_summary or "(none)",
        "Evidence collected:",
        evidence_summary or "(none)",
        "Applicable rules:",
        rules_summary or "(none)",
        "Strategic recommendations:",
        strategy_summary or "(none)",
        "Generate all three documents (statement_of_claim, hearing_script, legal_advice) and return a single JSON object with those keys, each containing full_text and the specified sub-fields.",
    ]
    return "\n\n".join(parts)
