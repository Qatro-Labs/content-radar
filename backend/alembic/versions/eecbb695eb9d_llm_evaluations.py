"""llm evaluations

Revision ID: eecbb695eb9d
Revises: 55279147dbd2
Create Date: 2026-10-17 19:20:57.402267
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "eecbb695eb9d"
down_revision: str | None = "55279147dbd2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "llm_evaluations",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("cache_key", sa.CHAR(length=64), nullable=False),
        sa.Column("operation", sa.String(length=32), nullable=False),
        sa.Column("prompt_version", sa.Integer(), nullable=False),
        sa.Column("requested_model", sa.String(length=64), nullable=False),
        sa.Column("response_model", sa.String(length=64), nullable=False),
        sa.Column("opportunity_id", sa.String(length=64), nullable=False),
        sa.Column("output", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_llm_evaluations")),
        sa.UniqueConstraint("cache_key", name=op.f("uq_llm_evaluations_cache_key")),
    )
    op.create_index(
        op.f("ix_llm_evaluations_operation"), "llm_evaluations", ["operation"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_llm_evaluations_operation"), table_name="llm_evaluations")
    op.drop_table("llm_evaluations")
