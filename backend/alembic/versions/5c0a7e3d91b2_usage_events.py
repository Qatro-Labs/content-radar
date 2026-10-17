"""usage_events

Revision ID: 5c0a7e3d91b2
Revises: aebe360930be
Create Date: 2026-10-17 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "5c0a7e3d91b2"
down_revision: str | None = "aebe360930be"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "usage_events",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("operation", sa.String(length=64), nullable=False),
        sa.Column("calls", sa.Integer(), server_default="1", nullable=False),
        sa.Column("units", sa.Numeric(precision=20, scale=4), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("cost_usd", sa.Numeric(precision=20, scale=10), nullable=True),
        sa.Column("pipeline_run_id", sa.Integer(), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(
            ["pipeline_run_id"],
            ["pipeline_runs.id"],
            name=op.f("fk_usage_events_pipeline_run_id_pipeline_runs"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_usage_events")),
    )
    op.create_index(
        op.f("ix_usage_events_occurred_at"), "usage_events", ["occurred_at"], unique=False
    )
    op.create_index(
        op.f("ix_usage_events_pipeline_run_id"), "usage_events", ["pipeline_run_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_usage_events_pipeline_run_id"), table_name="usage_events")
    op.drop_index(op.f("ix_usage_events_occurred_at"), table_name="usage_events")
    op.drop_table("usage_events")
