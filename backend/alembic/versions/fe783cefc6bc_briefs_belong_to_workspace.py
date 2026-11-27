"""briefs belong to workspace

Los briefs guardados dejan de ser de un usuario y pasan al workspace: los que ya existen van al de
30X con sus cadenas de versiones intactas, y el antiguo `user_id` queda como `created_by`.

Revision ID: fe783cefc6bc
Revises: 27e213f52e34
Create Date: 2026-11-27 18:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "fe783cefc6bc"
down_revision: str | None = "27e213f52e34"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FK_NAME = "fk_editorial_briefs_workspace_id_workspaces"
OLD_INDEX = "ix_editorial_briefs_user_id_root_id"
NEW_INDEX = "ix_editorial_briefs_workspace_id_root_id"

# El mismo workspace que siembra app.jobs.seed_workspace, en SQL: una migración no importa código
# de la app. La siembra busca por slug, así que las dos conviven.
ENSURE_THIRTY_X = """
    insert into workspaces (slug, name, public_demo) values ('30x', '30X', true)
    on conflict (slug) do nothing
"""
MOVE_TO_THIRTY_X = """
    update editorial_briefs set workspace_id = (select id from workspaces where slug = '30x')
"""


def upgrade() -> None:
    op.add_column("editorial_briefs", sa.Column("workspace_id", sa.BigInteger(), nullable=True))
    op.execute(ENSURE_THIRTY_X)
    op.execute(MOVE_TO_THIRTY_X)
    op.alter_column("editorial_briefs", "workspace_id", nullable=False)
    op.create_foreign_key(
        FK_NAME, "editorial_briefs", "workspaces", ["workspace_id"], ["id"], ondelete="CASCADE"
    )
    op.alter_column("editorial_briefs", "user_id", new_column_name="created_by")
    op.drop_index(OLD_INDEX, table_name="editorial_briefs")
    op.create_index(NEW_INDEX, "editorial_briefs", ["workspace_id", "root_id"], unique=False)


def downgrade() -> None:
    op.drop_index(NEW_INDEX, table_name="editorial_briefs")
    op.create_index(OLD_INDEX, "editorial_briefs", ["created_by", "root_id"], unique=False)
    op.alter_column("editorial_briefs", "created_by", new_column_name="user_id")
    op.drop_constraint(FK_NAME, "editorial_briefs", type_="foreignkey")
    # La fila de 30X se queda: puede haberla creado la siembra, y no estorba a la revisión anterior.
    op.drop_column("editorial_briefs", "workspace_id")
