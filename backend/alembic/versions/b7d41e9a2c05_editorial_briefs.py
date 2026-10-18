"""editorial briefs

Revision ID: b7d41e9a2c05
Revises: eecbb695eb9d
Create Date: 2026-10-18 13:20:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b7d41e9a2c05"
down_revision: str | None = "eecbb695eb9d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "editorial_briefs",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("root_id", sa.BigInteger(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("opportunity_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=True),
        sa.Column("request", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("brief", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["root_id"],
            ["editorial_briefs.id"],
            name=op.f("fk_editorial_briefs_root_id_editorial_briefs"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_editorial_briefs")),
        sa.UniqueConstraint("root_id", "version", name="uq_editorial_briefs_root_id_version"),
    )
    op.create_index(
        "ix_editorial_briefs_user_id_root_id",
        "editorial_briefs",
        ["user_id", "root_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_editorial_briefs_user_id_root_id", table_name="editorial_briefs")
    op.drop_table("editorial_briefs")
