from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.workspace_access import WorkspaceAccess, require_editor, workspace_access
from app.db.session import get_session
from app.models.workspaces import RadarProfileRecord
from app.schemas.profile import ProfileRead, ProfileUpdate, RadarProfile, WorkspaceRead
from app.services import workspaces

router = APIRouter(tags=["workspace"])

NO_PROFILE = "Este espacio todavía no tiene perfil de marca."
PROFILE_CONFLICT = (
    "Alguien del equipo guardó cambios mientras editabas. Recarga para ver la última versión."
)


def profile_read(record: RadarProfileRecord, access: WorkspaceAccess) -> ProfileRead:
    return ProfileRead(
        profile=RadarProfile.model_validate(record.profile),
        version=record.version,
        updated_at=record.created_at,
        can_edit=access.can_edit,
    )


@router.get("/workspace", response_model=WorkspaceRead)
async def read_workspace(
    access: Annotated[WorkspaceAccess, Depends(workspace_access)],
) -> WorkspaceRead:
    workspace = access.workspace
    return WorkspaceRead(
        slug=workspace.slug,
        name=workspace.name,
        public_demo=workspace.public_demo,
        role=access.role,
    )


@router.get("/profile", response_model=ProfileRead)
async def read_profile(
    session: Annotated[AsyncSession, Depends(get_session)],
    access: Annotated[WorkspaceAccess, Depends(workspace_access)],
) -> ProfileRead:
    record = await workspaces.current_profile(session, access.workspace.id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_PROFILE)
    return profile_read(record, access)


@router.put("/profile", response_model=ProfileRead)
async def update_profile(
    body: ProfileUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    access: Annotated[WorkspaceAccess, Depends(require_editor)],
) -> ProfileRead:
    # `require_editor` ya exigió sesión; el assert estrecha el tipo para pyright.
    assert access.user is not None
    try:
        await workspaces.save_profile(
            session,
            access.workspace.id,
            body.profile,
            created_by=access.user.user_id,
            expected_version=body.expected_version,
        )
    except workspaces.ProfileConflict:
        raise HTTPException(status.HTTP_409_CONFLICT, PROFILE_CONFLICT) from None
    # Se relee: tras el commit `created_at` (server_default) queda sin cargar.
    record = await workspaces.current_profile(session, access.workspace.id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, NO_PROFILE)
    return profile_read(record, access)
