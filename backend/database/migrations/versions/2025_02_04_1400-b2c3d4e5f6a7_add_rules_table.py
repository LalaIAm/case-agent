"""Add rules table for rule storage with pgvector embeddings.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2025-02-04 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rules",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("rule_type", sa.String(100), nullable=False),
        sa.Column("source", sa.String(500), nullable=False),
        sa.Column("title", sa.String(1000), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("metadata_", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        schema="public",
    )
    op.create_index(
        op.f("ix_rules_rule_type"), "rules", ["rule_type"], schema="public"
    )
    op.create_index(
        "ix_rules_rule_type_source",
        "rules",
        ["rule_type", "source"],
        schema="public",
    )
    op.execute(
        """
        CREATE INDEX ix_rules_embedding ON public.rules
        USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS public.ix_rules_embedding")
    op.drop_index("ix_rules_rule_type_source", table_name="rules", schema="public")
    op.drop_index(op.f("ix_rules_rule_type"), table_name="rules", schema="public")
    op.drop_table("rules", schema="public")
