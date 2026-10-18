"""Briefs guardados por usuario (`/editorial/briefs`). Solo se guardan con un usuario de Supabase:
sin sesión, o desde el MCP, el brief se devuelve y no queda fila.
"""

from typing import Any

from sqlalchemy import BigInteger, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class EditorialBriefRecord(TimestampMixin, Base):
    __tablename__ = "editorial_briefs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # El `sub` del token de Supabase; no hay tabla de usuarios propia.
    user_id: Mapped[str] = mapped_column(Text)
    opportunity_id: Mapped[str] = mapped_column(String(64))
    # Sin FK: la ejecución de `analyze` puede borrarse sin perder los briefs del usuario.
    run_id: Mapped[int | None] = mapped_column(Integer)
    request: Mapped[dict[str, Any]] = mapped_column(JSONB)
    brief: Mapped[dict[str, Any]] = mapped_column(JSONB)


# El listado pide los de un usuario, más recientes primero.
Index(
    "ix_editorial_briefs_user_id_created_at",
    EditorialBriefRecord.user_id,
    EditorialBriefRecord.created_at.desc(),
)
