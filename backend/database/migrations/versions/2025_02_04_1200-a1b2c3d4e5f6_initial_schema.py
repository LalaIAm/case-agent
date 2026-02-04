"""Initial schema with User, Case, CaseSession, MemoryBlock, Document, AgentRun, GeneratedDocument.

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2025-02-04 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable extensions before table creation (gen_random_uuid requires pgcrypto)
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Users
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="public",
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True, schema="public")

    # Cases
    op.create_table(
        "cases",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default=sa.text("'draft'")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["public.users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="public",
    )
    op.create_index(op.f("ix_cases_user_id"), "cases", ["user_id"], schema="public")
    op.create_index(op.f("ix_cases_status"), "cases", ["status"], schema="public")

    # Case sessions
    op.create_table(
        "case_sessions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_number", sa.Integer(), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default=sa.text("'active'")),
        sa.ForeignKeyConstraint(["case_id"], ["public.cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_id", "session_number", name="uq_case_session_number"),
        schema="public",
    )
    op.create_index(op.f("ix_case_sessions_case_id"), "case_sessions", ["case_id"], schema="public")

    # Memory blocks (with vector embedding)
    op.create_table(
        "memory_blocks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("block_type", sa.String(50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("metadata_", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["session_id"], ["public.case_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="public",
    )
    op.create_index(op.f("ix_memory_blocks_session_id"), "memory_blocks", ["session_id"], schema="public")
    op.create_index(op.f("ix_memory_blocks_block_type"), "memory_blocks", ["block_type"], schema="public")
    op.execute(
        """
        CREATE INDEX ix_memory_blocks_embedding ON public.memory_blocks
        USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)
        """
    )

    # Documents (with vector embedding)
    op.create_table(
        "documents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("file_path", sa.String(1000), nullable=False),
        sa.Column("file_type", sa.String(50), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("processed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.ForeignKeyConstraint(["case_id"], ["public.cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="public",
    )
    op.create_index(op.f("ix_documents_case_id"), "documents", ["case_id"], schema="public")
    op.execute(
        """
        CREATE INDEX ix_documents_embedding ON public.documents
        USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)
        """
    )

    # Agent runs
    op.create_table(
        "agent_runs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default=sa.text("'running'")),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("result", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["case_id"], ["public.cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="public",
    )
    op.create_index(op.f("ix_agent_runs_case_id"), "agent_runs", ["case_id"], schema="public")
    op.create_index(op.f("ix_agent_runs_agent_name"), "agent_runs", ["agent_name"], schema="public")
    op.create_index(op.f("ix_agent_runs_status"), "agent_runs", ["status"], schema="public")

    # Generated documents
    op.create_table(
        "generated_documents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_type", sa.String(100), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("file_path", sa.String(1000), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["case_id"], ["public.cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        schema="public",
    )
    op.create_index(
        op.f("ix_generated_documents_case_id"),
        "generated_documents",
        ["case_id"],
        schema="public",
    )
    op.create_index(
        op.f("ix_generated_documents_document_type"),
        "generated_documents",
        ["document_type"],
        schema="public",
    )
    op.create_index(
        "ix_generated_documents_case_type_version",
        "generated_documents",
        ["case_id", "document_type", "version"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_generated_documents_case_type_version",
        table_name="generated_documents",
        schema="public",
    )
    op.drop_index(
        op.f("ix_generated_documents_document_type"),
        table_name="generated_documents",
        schema="public",
    )
    op.drop_index(
        op.f("ix_generated_documents_case_id"),
        table_name="generated_documents",
        schema="public",
    )
    op.drop_table("generated_documents", schema="public")

    op.drop_index(op.f("ix_agent_runs_status"), table_name="agent_runs", schema="public")
    op.drop_index(op.f("ix_agent_runs_agent_name"), table_name="agent_runs", schema="public")
    op.drop_index(op.f("ix_agent_runs_case_id"), table_name="agent_runs", schema="public")
    op.drop_table("agent_runs", schema="public")

    op.execute("DROP INDEX IF EXISTS public.ix_documents_embedding")
    op.drop_index(op.f("ix_documents_case_id"), table_name="documents", schema="public")
    op.drop_table("documents", schema="public")

    op.execute("DROP INDEX IF EXISTS public.ix_memory_blocks_embedding")
    op.drop_index(op.f("ix_memory_blocks_block_type"), table_name="memory_blocks", schema="public")
    op.drop_index(op.f("ix_memory_blocks_session_id"), table_name="memory_blocks", schema="public")
    op.drop_table("memory_blocks", schema="public")

    op.drop_index(op.f("ix_case_sessions_case_id"), table_name="case_sessions", schema="public")
    op.drop_table("case_sessions", schema="public")

    op.drop_index(op.f("ix_cases_status"), table_name="cases", schema="public")
    op.drop_index(op.f("ix_cases_user_id"), table_name="cases", schema="public")
    op.drop_table("cases", schema="public")

    op.drop_index(op.f("ix_users_email"), table_name="users", schema="public")
    op.drop_table("users", schema="public")

    op.execute("DROP EXTENSION IF EXISTS vector")
    op.execute("DROP EXTENSION IF EXISTS pgcrypto")
