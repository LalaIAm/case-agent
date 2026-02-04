"""
Structured Pydantic schemas for memory block types (facts, evidence, strategy, rules, questions).
"""
from datetime import date
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, field_validator


class CaseBlockBase(BaseModel):
    """Base model for all case memory block types."""

    content: str
    confidence_score: Optional[float] = None
    source: Optional[str] = None
    tags: Optional[List[str]] = None


class FactBlock(CaseBlockBase):
    """Memory block for case facts (claims, counterclaims, timeline)."""

    fact_type: Literal["claim", "counterclaim", "timeline"]
    date_occurred: Optional[date] = None
    parties_involved: Optional[List[str]] = None

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("content must be non-empty")
        return v.strip()


class EvidenceBlock(CaseBlockBase):
    """Memory block for evidence (documents, witnesses, physical)."""

    evidence_type: Literal["document", "witness", "physical"]
    document_id: Optional[str] = None  # FK to Document when evidence_type is document
    relevance_score: Optional[float] = None

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("content must be non-empty")
        return v.strip()


class StrategyBlock(CaseBlockBase):
    """Memory block for legal/negotiation strategy."""

    strategy_type: Literal["legal_argument", "negotiation", "procedural"]
    priority: Optional[int] = None
    dependencies: Optional[List[str]] = None  # e.g. block IDs or labels

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("content must be non-empty")
        return v.strip()


class RuleBlock(CaseBlockBase):
    """Memory block for legal rules (statutes, case law, court rules)."""

    rule_source: Literal["statute", "case_law", "court_rule"]
    citation: Optional[str] = None
    jurisdiction: Optional[str] = None
    applicability_score: Optional[float] = None

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("content must be non-empty")
        return v.strip()


class QuestionBlock(CaseBlockBase):
    """Memory block for open or answered questions."""

    question_type: Literal["clarification", "missing_info", "legal_issue"]
    answered: bool = False
    answer_content: Optional[str] = None

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("content must be non-empty")
        return v.strip()


def create_block_metadata(block_type: str, **kwargs: Any) -> Dict[str, Any]:
    """
    Build metadata JSON for a memory block from block type and optional fields.
    """
    metadata: Dict[str, Any] = {"block_type": block_type}
    for key, value in kwargs.items():
        if value is not None:
            metadata[key] = value
    return metadata
