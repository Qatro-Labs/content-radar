"""Respuestas validadas del LLM, una fila por llamada (CLAUDE.md §7). Es también la caché: un tema
no se vuelve a evaluar mientras no cambien su entrada, el prompt, la rúbrica, el perfil ni el modelo
(`cache_key`).
"""

from typing import Any

from sqlalchemy import CHAR, BigInteger, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class LlmEvaluation(TimestampMixin, Base):
    __tablename__ = "llm_evaluations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    cache_key: Mapped[str] = mapped_column(CHAR(64), unique=True)  # sha256 hex
    operation: Mapped[str] = mapped_column(String(32), index=True)
    prompt_version: Mapped[int] = mapped_column(Integer)
    requested_model: Mapped[str] = mapped_column(String(64))
    response_model: Mapped[str] = mapped_column(String(64))
    # Solo para auditar: el id del tema puede cambiar entre ejecuciones sin cambiar la entrada.
    opportunity_id: Mapped[str] = mapped_column(String(64))
    output: Mapped[dict[str, Any]] = mapped_column(JSONB)
    input_tokens: Mapped[int] = mapped_column(Integer)
    output_tokens: Mapped[int] = mapped_column(Integer)
