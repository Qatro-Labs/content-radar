"""Respuestas de Jev, una fila por llamada (CLAUDE.md §7). Es también la caché: una pieza no se
vuelve a evaluar mientras no cambien su `state`, la batería ni el modelo (`cache_key`).
"""

from typing import Any

from sqlalchemy import CHAR, BigInteger, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class JevJudgment(TimestampMixin, Base):
    __tablename__ = "jev_judgments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    cache_key: Mapped[str] = mapped_column(CHAR(64), unique=True)  # sha256 hex
    battery: Mapped[str] = mapped_column(String(32), index=True)
    battery_version: Mapped[int] = mapped_column(Integer)
    requested_model: Mapped[str] = mapped_column(String(64))
    response_model: Mapped[str] = mapped_column(String(64))
    content_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("content_items.id", ondelete="CASCADE"), index=True
    )
    answers: Mapped[dict[str, Any]] = mapped_column(JSONB)  # con probabilidades, para auditar
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
