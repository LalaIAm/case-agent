"""
Pydantic v2 schemas for API validation and serialization.
"""
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field, field_validator


# --- User Schemas ---
class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    is_active: bool
    is_verified: bool
    created_at: datetime


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None


# --- Case Schemas ---
class CaseBase(BaseModel):
    title: str = Field(..., max_length=500)
    description: Optional[str] = None


class CaseCreate(CaseBase):
    pass


class CaseRead(CaseBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class CaseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


# --- CaseSession Schemas ---
class CaseSessionBase(BaseModel):
    session_number: int


class CaseSessionCreate(CaseSessionBase):
    case_id: UUID


class CaseSessionRead(CaseSessionBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    case_id: UUID
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str


class CaseSessionUpdate(BaseModel):
    status: Optional[str] = None
    completed_at: Optional[datetime] = None


# --- MemoryBlock Schemas ---
def _validate_content_non_empty(v: str) -> str:
    """Reject empty or whitespace-only content; return stripped string."""
    if not isinstance(v, str):
        raise ValueError("content must be a string")
    s = v.strip()
    if not s:
        raise ValueError("content must be non-empty after trimming whitespace")
    return s


class MemoryBlockBase(BaseModel):
    block_type: Literal["fact", "evidence", "strategy", "rule", "question"]
    content: str
    metadata_: Optional[Dict[str, Any]] = None

    @field_validator("content")
    @classmethod
    def content_non_empty_stripped(cls, v: str) -> str:
        return _validate_content_non_empty(v)


class MemoryBlockCreate(MemoryBlockBase):
    session_id: UUID


class MemoryBlockUpdate(BaseModel):
    """Update body for memory block; content must be non-empty after trim."""

    content: str
    metadata_: Optional[Dict[str, Any]] = Field(None, alias="metadata")

    @field_validator("content")
    @classmethod
    def content_non_empty_stripped(cls, v: str) -> str:
        return _validate_content_non_empty(v)


class MemoryBlockRead(MemoryBlockBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    session_id: UUID
    created_at: datetime


class MemoryBlockSearch(BaseModel):
    query: str
    block_types: Optional[List[str]] = None
    limit: int = 10


# --- Document Schemas ---
class DocumentBase(BaseModel):
    filename: str
    file_type: str


class DocumentCreate(DocumentBase):
    case_id: UUID
    file_size: int
    file_path: Optional[str] = None
    extracted_text: Optional[str] = None


class DocumentRead(DocumentBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    case_id: UUID
    file_path: str
    file_size: int
    uploaded_at: datetime
    processed: bool


class DocumentUpdate(BaseModel):
    processed: Optional[bool] = None
    extracted_text: Optional[str] = None


# --- AgentRun Schemas ---
class AgentRunBase(BaseModel):
    agent_name: Literal["intake", "research", "document", "strategy", "drafting"]


class AgentRunCreate(AgentRunBase):
    case_id: UUID


class AgentRunRead(AgentRunBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    case_id: UUID
    status: str
    reasoning: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class AgentRunUpdate(BaseModel):
    status: Optional[str] = None
    reasoning: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class AgentExecuteRequest(BaseModel):
    case_id: UUID
    agent_name: Optional[Literal["intake", "research", "document", "strategy", "drafting"]] = None
    force_restart: bool = False


class AgentStatusResponse(BaseModel):
    case_id: UUID
    current_agent: Optional[str] = None
    workflow_status: str
    progress_percentage: int
    agent_runs: List[AgentRunRead] = []


class WorkflowStateResponse(BaseModel):
    case_id: UUID
    completed_agents: List[str] = []
    pending_agents: List[str] = []
    current_agent: Optional[str] = None
    overall_status: str


# --- GeneratedDocument Schemas ---
class GeneratedDocumentBase(BaseModel):
    document_type: Literal["statement_of_claim", "hearing_script", "legal_advice"]
    content: str


class GeneratedDocumentCreate(GeneratedDocumentBase):
    case_id: UUID


class GeneratedDocumentRead(GeneratedDocumentBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    case_id: UUID
    file_path: Optional[str] = None
    version: int
    generated_at: datetime


class GeneratedDocumentWithPDF(GeneratedDocumentRead):
    """Generated document with computed has_pdf and download_url for frontend."""

    @computed_field
    @property
    def has_pdf(self) -> bool:
        return self.file_path is not None

    @computed_field
    @property
    def download_url(self) -> Optional[str]:
        if not self.file_path:
            return None
        return f"/api/documents/generated/{self.id}/download"


class DocumentGenerationRequest(BaseModel):
    """Request body for triggering PDF generation."""

    document_id: UUID
    force_regenerate: bool = False


class DocumentGenerationResponse(GeneratedDocumentRead):
    """Response after PDF generation with generation metadata."""

    pdf_generated: bool = True
    generation_time_ms: Optional[int] = None


# --- CaseWithRelations (for detailed views) ---
class CaseWithRelations(CaseRead):
    sessions: List[CaseSessionRead] = []
    documents: List[DocumentRead] = []


# --- Rule Schemas ---
RULE_TYPES = ("statute", "procedure", "case_law", "interpretation")


class RuleBase(BaseModel):
    rule_type: str
    source: str
    title: str
    content: str
    metadata_: Optional[Dict[str, Any]] = None


class RuleCreate(RuleBase):
    rule_type: Literal["statute", "procedure", "case_law", "interpretation"]

    @field_validator("rule_type")
    @classmethod
    def rule_type_valid(cls, v: str) -> str:
        if v not in RULE_TYPES:
            raise ValueError(f"rule_type must be one of {RULE_TYPES}")
        return v


class RuleRead(RuleBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None


class RuleUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    metadata_: Optional[Dict[str, Any]] = None


def _default_rules_limit() -> int:
    from backend.config import get_settings
    return get_settings().RULES_MAX_RESULTS


class RuleSearch(BaseModel):
    query: str
    rule_types: Optional[List[str]] = None
    limit: int = Field(default_factory=_default_rules_limit)
    min_similarity: Optional[float] = None


class HybridRuleSearch(RuleSearch):
    include_static: bool = True
    include_case_law: bool = True


# --- Tavily Search Schemas ---


class TavilySearchRequest(BaseModel):
    """Request body for general Tavily search."""

    query: str
    search_depth: str = "basic"
    max_results: int = Field(default=5, ge=1, le=20)
    include_domains: Optional[List[str]] = None
    exclude_domains: Optional[List[str]] = None
    topic: str = "general"


class TavilySearchResponse(BaseModel):
    """Response for Tavily search endpoints."""

    query: str
    results: List[Dict[str, Any]]
    answer: Optional[str] = None
    search_time: Optional[float] = None


class CaseLawSearchRequest(BaseModel):
    """Request body for case law search."""

    query: str
    jurisdiction: str = "Minnesota"
    max_results: int = Field(default=5, ge=1, le=20)


class PrecedentSearchRequest(BaseModel):
    """Request body for precedent research."""

    dispute_type: str
    facts: str
    jurisdiction: str = "Minnesota"
    max_results: int = Field(default=5, ge=1, le=20)


class StatuteSearchRequest(BaseModel):
    """Request body for statute lookup."""

    topic: str
    statute_reference: Optional[str] = None
    max_results: int = Field(default=3, ge=1, le=20)
