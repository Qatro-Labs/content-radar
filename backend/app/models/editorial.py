"""Briefs del equipo de cada workspace (`/editorial/briefs`). Solo se guardan si los pide un
miembro: sin sesión, desde fuera del equipo o desde el MCP, el brief se devuelve y no queda fila.

Cada brief pertenece a una cadena de versiones: la primera tiene `root_id = id` y `version = 1`, y
regenerar a partir de un brief añade la siguiente versión a su cadena.
"""

from typing import Any

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class EditorialBriefRecord(TimestampMixin, Base):
    __tablename__ = "editorial_briefs"
    __table_args__ = (
        UniqueConstraint("root_id", "version", name="uq_editorial_briefs_root_id_version"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    root_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("editorial_briefs.id", ondelete="CASCADE")
    )
    version: Mapped[int] = mapped_column(Integer)
    workspace_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("workspaces.id", ondelete="CASCADE")
    )
    # El `sub` del token de Supabase de quien lo pidió; no hay tabla de usuarios propia.
    created_by: Mapped[str] = mapped_column(Text)
    opportunity_id: Mapped[str] = mapped_column(String(64))
    # Sin FK: la ejecución de `analyze` puede borrarse sin perder los briefs del equipo.
    run_id: Mapped[int | None] = mapped_column(Integer)
    request: Mapped[dict[str, Any]] = mapped_column(JSONB)
    # Con otra versión del perfil, la misma petición es un brief distinto (no se deduplica).
    profile_version: Mapped[int | None] = mapped_column(Integer)
    brief: Mapped[dict[str, Any]] = mapped_column(JSONB)


# El listado agrupa por cadena los briefs de un workspace.
Index(
    "ix_editorial_briefs_workspace_id_root_id",
    EditorialBriefRecord.workspace_id,
    EditorialBriefRecord.root_id,
)
