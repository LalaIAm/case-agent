"""
Pydantic v2 schemas for API validation and serialization.
"""
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


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


# --- GeneratedDocument Schemas ---
class GeneratedDocumentBase(BaseModel):
    document_type: Literal["statement_of_claim", "hearing_script", "advice"]
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


# --- CaseWithRelations (for detailed views) ---
class CaseWithRelations(CaseRead):
    sessions: List[CaseSessionRead] = []
    documents: List[DocumentRead] = []
