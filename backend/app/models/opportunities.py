"""Oportunidades calculadas por `app.jobs.analyze`, una tanda por ejecución.

Se guardan como JSONB ya validado contra el contrato (`app/schemas/opportunity.py`): la API y el
MCP leen la última ejecución correcta sin recalcular nada. Las tablas normalizadas de §6
(`topics`, `topic_content`, `opportunity_evidence`) quedan para después de la hackathon.
"""

from typing import Any

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class OpportunityRecord(TimestampMixin, Base):
    __tablename__ = "opportunities"
    __table_args__ = (UniqueConstraint("run_id", "opportunity_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("pipeline_runs.id", ondelete="CASCADE"), index=True
    )
    opportunity_id: Mapped[str] = mapped_column(String(64), index=True)
    rank: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)  # Opportunity
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)  # list[Evidence]
    timeline: Mapped[dict[str, Any]] = mapped_column(JSONB)  # OpportunityTimeline
