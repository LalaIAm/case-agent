"""
SQLAlchemy 2.0 models for Minnesota Conciliation Court Case Agent.
"""
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.schema import Index
from pgvector.sqlalchemy import Vector

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "public"}

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    cases = relationship("Case", back_populates="user", cascade="all, delete-orphan")


class Case(Base):
    __tablename__ = "cases"
    __table_args__ = {"schema": "public"}

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(
        String(50), default="draft", nullable=False, index=True
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
    )

    user = relationship("User", back_populates="cases")
    sessions = relationship(
        "CaseSession", back_populates="case", cascade="all, delete-orphan"
    )
    documents = relationship(
        "Document", back_populates="case", cascade="all, delete-orphan"
    )
    agent_runs = relationship(
        "AgentRun", back_populates="case", cascade="all, delete-orphan"
    )
    generated_documents = relationship(
        "GeneratedDocument", back_populates="case", cascade="all, delete-orphan"
    )
    conversation_messages = relationship(
        "ConversationMessage", back_populates="case", cascade="all, delete-orphan"
    )


class CaseSession(Base):
    __tablename__ = "case_sessions"
    __table_args__ = (
        UniqueConstraint("case_id", "session_number", name="uq_case_session_number"),
        {"schema": "public"},
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    case_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_number = Column(Integer, nullable=False)
    started_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(
        String(50), default="active", nullable=False
    )

    case = relationship("Case", back_populates="sessions")
    memory_blocks = relationship(
        "MemoryBlock", back_populates="session", cascade="all, delete-orphan"
    )


class MemoryBlock(Base):
    __tablename__ = "memory_blocks"
    __table_args__ = (
        Index(
            "ix_memory_blocks_embedding",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        {"schema": "public"},
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.case_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    block_type = Column(String(50), nullable=False, index=True)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536), nullable=True)
    metadata_ = Column(JSON, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    session = relationship("CaseSession", back_populates="memory_blocks")


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        Index(
            "ix_documents_embedding",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        {"schema": "public"},
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    case_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_type = Column(String(50), nullable=False)
    file_size = Column(Integer, nullable=False)
    extracted_text = Column(Text, nullable=True)
    embedding = Column(Vector(1536), nullable=True)
    uploaded_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    processed = Column(Boolean, default=False, nullable=False)

    case = relationship("Case", back_populates="documents")


class AgentRun(Base):
    __tablename__ = "agent_runs"
    __table_args__ = {"schema": "public"}

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    case_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_name = Column(String(100), nullable=False, index=True)
    status = Column(
        String(50), default="running", nullable=False, index=True
    )
    reasoning = Column(Text, nullable=True)
    result = Column(JSON, nullable=True)
    started_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)

    case = relationship("Case", back_populates="agent_runs")


class GeneratedDocument(Base):
    __tablename__ = "generated_documents"
    __table_args__ = (
        Index(
            "ix_generated_documents_case_type_version",
            "case_id",
            "document_type",
            "version",
        ),
        {"schema": "public"},
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    case_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_type = Column(String(100), nullable=False, index=True)
    content = Column(Text, nullable=False)
    file_path = Column(String(1000), nullable=True)
    version = Column(Integer, default=1, nullable=False)
    generated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    case = relationship("Case", back_populates="generated_documents")


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"
    __table_args__ = (
        Index(
            "idx_conversation_messages_case_id_created_at",
            "case_id",
            "created_at",
            postgresql_ops={"created_at": "DESC"},
        ),
        {"schema": "public"},
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    case_id = Column(
        UUID(as_uuid=True),
        ForeignKey("public.cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(20), nullable=False, index=True)  # 'user' | 'assistant'
    content = Column(Text, nullable=False)
    metadata_ = Column(JSON, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    case = relationship("Case", back_populates="conversation_messages")


class Rule(Base):
    __tablename__ = "rules"
    __table_args__ = (
        Index(
            "ix_rules_embedding",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index("ix_rules_rule_type_source", "rule_type", "source"),
        {"schema": "public"},
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    rule_type = Column(String(100), nullable=False, index=True)
    source = Column(String(500), nullable=False)
    title = Column(String(1000), nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536), nullable=True)
    metadata_ = Column(JSON, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
    )
