"""Tablas del Signal Engine: fuentes, contenidos y snapshots de métricas.

Los enums se guardan como texto y se validan en los schemas Pydantic: así añadir un valor
no requiere migración durante la hackathon.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Source(TimestampMixin, Base):
    __tablename__ = "sources"
    __table_args__ = (UniqueConstraint("platform", "external_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(String(32))
    kind: Mapped[str] = mapped_column(String(32))
    external_id: Mapped[str] = mapped_column(String(512))
    name: Mapped[str] = mapped_column(String(255))
    url: Mapped[str | None] = mapped_column(Text)
    segment: Mapped[str] = mapped_column(String(32), index=True)
    language: Mapped[str | None] = mapped_column(String(8))
    region: Mapped[str | None] = mapped_column(String(32))
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    # Opciones del collector: handle, uploads_playlist_id, ai_filter…
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")

    items: Mapped[list["ContentItem"]] = relationship(back_populates="source")


class ContentItem(TimestampMixin, Base):
    __tablename__ = "content_items"
    __table_args__ = (
        UniqueConstraint("platform", "external_id"),
        Index("ix_content_items_published_at", "published_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), index=True)
    platform: Mapped[str] = mapped_column(String(32))
    external_id: Mapped[str] = mapped_column(String(512))
    url: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    author_name: Mapped[str | None] = mapped_column(String(255))
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    first_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    format: Mapped[str] = mapped_column(String(32), default="unknown")
    language: Mapped[str | None] = mapped_column(String(8))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)

    source: Mapped[Source] = relationship(back_populates="items")
    snapshots: Mapped[list["MetricSnapshot"]] = relationship(
        back_populates="content_item", order_by="MetricSnapshot.observed_at"
    )


class MetricSnapshot(Base):
    """Una observación de métricas públicas. Nunca se sobrescribe; sin historial
    no hay velocidad.
    """

    __tablename__ = "metric_snapshots"
    __table_args__ = (
        UniqueConstraint("content_item_id", "observed_at"),
        Index("ix_metric_snapshots_item_observed", "content_item_id", "observed_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    content_item_id: Mapped[int] = mapped_column(ForeignKey("content_items.id", ondelete="CASCADE"))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    views: Mapped[int | None] = mapped_column(BigInteger)
    likes: Mapped[int | None] = mapped_column(BigInteger)
    comments: Mapped[int | None] = mapped_column(BigInteger)
    points: Mapped[int | None] = mapped_column(BigInteger)
    shares: Mapped[int | None] = mapped_column(BigInteger)

    content_item: Mapped[ContentItem] = relationship(back_populates="snapshots")


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    job: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(16))  # running | success | failed
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stats: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error: Mapped[str | None] = mapped_column(Text)
