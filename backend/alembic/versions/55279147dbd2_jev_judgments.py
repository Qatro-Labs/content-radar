"""jev judgments

Revision ID: 55279147dbd2
Revises: 5c0a7e3d91b2
Create Date: 2026-10-17 17:29:49.024756
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "55279147dbd2"
down_revision: str | None = "5c0a7e3d91b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "jev_judgments",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("cache_key", sa.CHAR(length=64), nullable=False),
        sa.Column("battery", sa.String(length=32), nullable=False),
        sa.Column("battery_version", sa.Integer(), nullable=False),
        sa.Column("requested_model", sa.String(length=64), nullable=False),
        sa.Column("response_model", sa.String(length=64), nullable=False),
        sa.Column("content_item_id", sa.Integer(), nullable=True),
        sa.Column("answers", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["content_item_id"],
            ["content_items.id"],
            name=op.f("fk_jev_judgments_content_item_id_content_items"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_jev_judgments")),
        sa.UniqueConstraint("cache_key", name=op.f("uq_jev_judgments_cache_key")),
    )
    op.create_index(op.f("ix_jev_judgments_battery"), "jev_judgments", ["battery"], unique=False)
    op.create_index(
        op.f("ix_jev_judgments_content_item_id"), "jev_judgments", ["content_item_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_jev_judgments_content_item_id"), table_name="jev_judgments")
    op.drop_index(op.f("ix_jev_judgments_battery"), table_name="jev_judgments")
    op.drop_table("jev_judgments")
