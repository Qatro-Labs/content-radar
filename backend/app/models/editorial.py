"""Briefs guardados por usuario (`/editorial/briefs`). Solo se guardan con un usuario de Supabase:
sin sesión, o desde el MCP, el brief se devuelve y no queda fila.

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
    # El `sub` del token de Supabase; no hay tabla de usuarios propia.
    user_id: Mapped[str] = mapped_column(Text)
    opportunity_id: Mapped[str] = mapped_column(String(64))
    # Sin FK: la ejecución de `analyze` puede borrarse sin perder los briefs del usuario.
    run_id: Mapped[int | None] = mapped_column(Integer)
    request: Mapped[dict[str, Any]] = mapped_column(JSONB)
    brief: Mapped[dict[str, Any]] = mapped_column(JSONB)


# El listado agrupa por cadena los briefs de un usuario.
Index(
    "ix_editorial_briefs_user_id_root_id",
    EditorialBriefRecord.user_id,
    EditorialBriefRecord.root_id,
)
