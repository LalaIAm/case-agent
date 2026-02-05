"""Add conversation_messages table for advisor chat.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2025-02-05 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "conversation_messages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.cases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata_", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="public",
    )
    op.create_index(
        op.f("ix_conversation_messages_case_id"),
        "conversation_messages",
        ["case_id"],
        schema="public",
    )
    op.create_index(
        op.f("ix_conversation_messages_role"),
        "conversation_messages",
        ["role"],
        schema="public",
    )
    op.create_index(
        "idx_conversation_messages_case_id_created_at",
        "conversation_messages",
        ["case_id", "created_at"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_index(
        "idx_conversation_messages_case_id_created_at",
        table_name="conversation_messages",
        schema="public",
    )
    op.drop_index(
        op.f("ix_conversation_messages_role"),
        table_name="conversation_messages",
        schema="public",
    )
    op.drop_index(
        op.f("ix_conversation_messages_case_id"),
        table_name="conversation_messages",
        schema="public",
    )
    op.drop_table("conversation_messages", schema="public")
