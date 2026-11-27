from typing import Literal

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workspaces import RadarProfileRecord, WorkspaceMemberRecord, WorkspaceRecord
from app.schemas.profile import RadarProfile

MemberRole = Literal["owner", "member"]


class ProfileConflict(Exception):
    """Alguien guardó una versión nueva del perfil mientras esta persona editaba."""


async def get_workspace(session: AsyncSession, slug: str) -> WorkspaceRecord | None:
    return await session.scalar(select(WorkspaceRecord).where(WorkspaceRecord.slug == slug))


async def member_role(session: AsyncSession, workspace_id: int, user_id: str) -> MemberRole | None:
    role = await session.scalar(
        select(WorkspaceMemberRecord.role).where(
            WorkspaceMemberRecord.workspace_id == workspace_id,
            WorkspaceMemberRecord.user_id == user_id,
        )
    )
    if role == "owner" or role == "member":
        return role
    return None


async def add_member(
    session: AsyncSession, workspace_id: int, user_id: str, role: MemberRole
) -> None:
    statement = insert(WorkspaceMemberRecord).values(
        workspace_id=workspace_id, user_id=user_id, role=role
    )
    await session.execute(
        statement.on_conflict_do_update(
            constraint="uq_workspace_members_workspace_id_user_id",
            set_={"role": statement.excluded.role},
        )
    )
    await session.commit()


async def remove_member(session: AsyncSession, workspace_id: int, user_id: str) -> bool:
    result = await session.execute(
        delete(WorkspaceMemberRecord)
        .where(
            WorkspaceMemberRecord.workspace_id == workspace_id,
            WorkspaceMemberRecord.user_id == user_id,
        )
        .returning(WorkspaceMemberRecord.id)
    )
    await session.commit()
    return result.first() is not None


async def current_profile(session: AsyncSession, workspace_id: int) -> RadarProfileRecord | None:
    return await session.scalar(
        select(RadarProfileRecord)
        .where(RadarProfileRecord.workspace_id == workspace_id)
        .order_by(RadarProfileRecord.version.desc())
        .limit(1)
    )


async def save_profile(
    session: AsyncSession,
    workspace_id: int,
    profile: RadarProfile,
    *,
    created_by: str,
    expected_version: int,
) -> RadarProfileRecord:
    latest_version = await session.scalar(
        select(func.max(RadarProfileRecord.version)).where(
            RadarProfileRecord.workspace_id == workspace_id
        )
    )
    if (latest_version or 0) != expected_version:
        raise ProfileConflict
    record = RadarProfileRecord(
        workspace_id=workspace_id,
        version=expected_version + 1,
        profile=profile.model_dump(mode="json"),
        created_by=created_by,
    )
    session.add(record)
    try:
        await session.commit()
    except IntegrityError:
        # Dos guardados con la misma versión esperada: el UniqueConstraint deja pasar solo uno.
        await session.rollback()
        raise ProfileConflict from None
    return record
