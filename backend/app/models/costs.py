"""Consumo de APIs externas y su coste (CLAUDE.md §4)."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UsageEvent(Base):
    """Un consumo de una API externa. El coste se fija al registrarlo con el precio vigente en
    pricing.yaml, así que cambiar un precio no altera el histórico.
    """

    __tablename__ = "usage_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    provider: Mapped[str] = mapped_column(String(32))
    operation: Mapped[str] = mapped_column(String(64))
    # Llamadas HTTP que cubre el evento: los jobs agregan por operación en vez de una fila
    # por request.
    calls: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    units: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    unit: Mapped[str] = mapped_column(String(32))
    # Null = precio desconocido, no gratis.
    cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(20, 10))
    pipeline_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("pipeline_runs.id", ondelete="SET NULL"), index=True
    )
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
