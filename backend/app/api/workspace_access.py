from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import CurrentUser, _unauthorized, user_if_signed_in
from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.models.workspaces import WorkspaceRecord
from app.services.workspaces import MemberRole, get_workspace, member_role

WORKSPACE_NOT_FOUND = "Este espacio de trabajo no existe todavía."


@dataclass(frozen=True)
class WorkspaceAccess:
    workspace: WorkspaceRecord
    user: CurrentUser | None
    role: MemberRole | None

    @property
    def can_edit(self) -> bool:
        return self.role is not None


async def workspace_access(
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    user: Annotated[CurrentUser | None, Depends(user_if_signed_in)],
) -> WorkspaceAccess:
    # Un solo workspace en esta entrega; elegirlo por usuario llega con el radar configurable.
    workspace = await get_workspace(session, settings.default_workspace_slug)
    if workspace is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, WORKSPACE_NOT_FOUND)
    role = await member_role(session, workspace.id, user.user_id) if user else None
    # 404 y no 403: un workspace privado no revela que existe.
    if not workspace.public_demo and role is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, WORKSPACE_NOT_FOUND)
    return WorkspaceAccess(workspace=workspace, user=user, role=role)


async def require_editor(
    access: Annotated[WorkspaceAccess, Depends(workspace_access)],
) -> WorkspaceAccess:
    if access.user is None:
        raise _unauthorized()
    if not access.can_edit:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Solo el equipo de {access.workspace.name} puede cambiar esto.",
        )
    return access
