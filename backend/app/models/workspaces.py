"""Workspaces, sus miembros y las versiones del perfil de marca del Radar."""

from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    false,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class WorkspaceRecord(TimestampMixin, Base):
    __tablename__ = "workspaces"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    public_demo: Mapped[bool] = mapped_column(Boolean, server_default=false())


class WorkspaceMemberRecord(TimestampMixin, Base):
    __tablename__ = "workspace_members"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "user_id", name="uq_workspace_members_workspace_id_user_id"
        ),
        CheckConstraint("role in ('owner', 'member')", name="role"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("workspaces.id", ondelete="CASCADE")
    )
    # El `sub` del token de Supabase; no hay tabla de usuarios propia.
    user_id: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(16))


class RadarProfileRecord(TimestampMixin, Base):
    __tablename__ = "radar_profiles"
    __table_args__ = (
        UniqueConstraint("workspace_id", "version", name="uq_radar_profiles_workspace_id_version"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("workspaces.id", ondelete="CASCADE")
    )
    version: Mapped[int] = mapped_column(Integer)
    profile: Mapped[dict[str, Any]] = mapped_column(JSONB)
    # `None` = la siembra, no una persona.
    created_by: Mapped[str | None] = mapped_column(Text)
