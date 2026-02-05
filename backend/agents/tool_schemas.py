"""
OpenAI tool (function) schemas for agent structured outputs.
Each agent uses a single tool call; we parse function arguments instead of free-form JSON.
"""
import json
from typing import Any, Dict, List

# --- Intake agent: submit_intake ---

INTAKE_TOOL_NAME = "submit_intake"

INTAKE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": INTAKE_TOOL_NAME,
            "description": "Submit the structured intake output: dispute type, parties, facts, timeline events, and clarifying questions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dispute_type": {
                        "type": "string",
                        "description": "Category of the dispute",
                        "enum": [
                            "contract",
                            "property_damage",
                            "debt_collection",
                            "landlord_tenant",
                            "consumer",
                            "personal_injury",
                            "other",
                        ],
                    },
                    "parties": {
                        "type": "array",
                        "description": "List of party names or roles (e.g. Plaintiff, Defendant, John Doe)",
                        "items": {"type": "string"},
                    },
                    "facts": {
                        "type": "array",
                        "description": "Extracted facts with content and type",
                        "items": {
                            "type": "object",
                            "properties": {
                                "content": {"type": "string", "description": "Fact description"},
                                "fact_type": {
                                    "type": "string",
                                    "enum": ["claim", "counterclaim", "timeline"],
                                    "description": "Type of fact",
                                },
                                "date_occurred": {
                                    "type": "string",
                                    "description": "Date if known (YYYY-MM-DD or description)",
                                },
                                "parties_involved": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Parties involved in this fact",
                                },
                                "confidence_score": {
                                    "type": "number",
                                    "description": "Confidence 0-1",
                                },
                            },
                            "required": ["content", "fact_type"],
                        },
                    },
                    "timeline_events": {
                        "type": "array",
                        "description": "Chronological events with date and description",
                        "items": {
                            "type": "object",
                            "properties": {
                                "date": {
                                    "type": "string",
                                    "description": "Date (YYYY-MM-DD or description)",
                                },
                                "description": {"type": "string", "description": "Event description"},
                                "parties_involved": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                            "required": ["date", "description"],
                        },
                    },
                    "questions": {
                        "type": "array",
                        "description": "Clarifying questions for missing information",
                        "items": {
                            "type": "object",
                            "properties": {
                                "content": {"type": "string", "description": "Question text"},
                                "question_type": {
                                    "type": "string",
                                    "enum": ["clarification", "missing_info", "legal_issue"],
                                    "description": "Type of question",
                                },
                            },
                            "required": ["content", "question_type"],
                        },
                    },
                },
                "required": ["dispute_type", "parties", "facts", "questions"],
            },
        },
    }
]

# --- Research agent: submit_research ---

RESEARCH_TOOL_NAME = "submit_research"

RESEARCH_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": RESEARCH_TOOL_NAME,
            "description": "Submit the research output: applicable rules, precedents, and legal standards.",
            "parameters": {
                "type": "object",
                "properties": {
                    "research_queries": {
                        "type": "array",
                        "description": "Queries that were conceptually used",
                        "items": {"type": "string"},
                    },
                    "applicable_rules": {
                        "type": "array",
                        "description": "Applicable rules with source, citation, and summary",
                        "items": {
                            "type": "object",
                            "properties": {
                                "source": {
                                    "type": "string",
                                    "enum": ["statute", "case_law", "court_rule"],
                                    "description": "Rule source",
                                },
                                "citation": {
                                    "type": "string",
                                    "description": "e.g. MN Stat § 491A.01",
                                },
                                "content_summary": {
                                    "type": "string",
                                    "description": "Summary of the rule",
                                },
                                "content": {
                                    "type": "string",
                                    "description": "Full or alternate content",
                                },
                                "applicability_score": {
                                    "type": "number",
                                    "description": "Relevance 0-1",
                                },
                            },
                            "required": ["source", "content_summary"],
                        },
                    },
                    "precedents": {
                        "type": "array",
                        "description": "Relevant precedents",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "citation": {"type": "string"},
                                "summary": {"type": "string"},
                                "relevance": {"type": "string"},
                            },
                            "required": ["title", "summary"],
                        },
                    },
                    "legal_standards": {
                        "type": "array",
                        "description": "Legal standards (e.g. burden of proof, elements of claim)",
                        "items": {"type": "string"},
                    },
                },
                "required": ["applicable_rules", "legal_standards"],
            },
        },
    }
]

# --- Document agent: submit_document_analysis ---

DOCUMENT_TOOL_NAME = "submit_document_analysis"

DOCUMENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": DOCUMENT_TOOL_NAME,
            "description": "Submit the document analysis: evidence items, document summaries, and relevance rationales.",
            "parameters": {
                "type": "object",
                "properties": {
                    "evidence_items": {
                        "type": "array",
                        "description": "Extracted evidence with type and relevance",
                        "items": {
                            "type": "object",
                            "properties": {
                                "content": {
                                    "type": "string",
                                    "description": "Description of the evidence",
                                },
                                "evidence_type": {
                                    "type": "string",
                                    "enum": ["document", "witness", "physical"],
                                    "description": "Type of evidence",
                                },
                                "relevance_score": {
                                    "type": "number",
                                    "description": "Relevance to case 0-1",
                                },
                                "document_id": {
                                    "type": "string",
                                    "description": "Optional document ID for linking",
                                },
                            },
                            "required": ["content", "evidence_type", "relevance_score"],
                        },
                    },
                    "document_summaries": {
                        "type": "array",
                        "description": "Summary and key details per document",
                        "items": {
                            "type": "object",
                            "properties": {
                                "summary": {"type": "string", "description": "Brief summary"},
                                "key_details": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Key details list",
                                },
                            },
                            "required": ["summary"],
                        },
                    },
                    "relevance_scores": {
                        "type": "object",
                        "description": "Mapping of evidence index or label to rationale for relevance",
                        "additionalProperties": {"type": "string"},
                    },
                },
                "required": ["evidence_items", "document_summaries", "relevance_scores"],
            },
        },
    }
]


def parse_tool_call_arguments(tool_calls: Any, expected_name: str) -> Dict[str, Any]:
    """
    Extract JSON arguments from the first tool call matching expected_name.
    Raises ValueError if no matching tool call or invalid JSON.
    """
    if not tool_calls or not hasattr(tool_calls, "__iter__"):
        raise ValueError("No tool calls in response")
    for tc in tool_calls:
        name = getattr(tc, "function", None) and getattr(tc.function, "name", None)
        if name != expected_name:
            continue
        args_str = getattr(tc.function, "arguments", None)
        if not args_str or not isinstance(args_str, str):
            raise ValueError("Tool call has no arguments")
        try:
            return json.loads(args_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in tool call arguments: {e}") from e
    raise ValueError(f"No tool call found for function '{expected_name}'")
