import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.api.auth import CurrentUser
from app.api.workspace_access import WorkspaceAccess, require_editor
from app.jobs.seed_workspace import THIRTY_X_PROFILE, seed_thirty_x
from app.jobs.workspace_members import run
from app.models.workspaces import WorkspaceRecord
from app.services.workspaces import (
    ProfileConflict,
    add_member,
    current_profile,
    member_role,
    remove_member,
    save_profile,
)


@pytest.fixture
async def workspace(session) -> WorkspaceRecord:
    return await seed_thirty_x(session)


@pytest.fixture
def session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


async def test_member_role_none_for_strangers_and_role_for_members(session, workspace):
    assert await member_role(session, workspace.id, "user-1") is None
    await add_member(session, workspace.id, "user-1", "member")
    assert await member_role(session, workspace.id, "user-1") == "member"
    assert await member_role(session, workspace.id, "user-2") is None


async def test_add_member_twice_updates_the_role(session, workspace):
    await add_member(session, workspace.id, "user-1", "member")
    await add_member(session, workspace.id, "user-1", "owner")
    assert await member_role(session, workspace.id, "user-1") == "owner"


async def test_remove_member_reports_whether_it_existed(session, workspace):
    await add_member(session, workspace.id, "user-1", "member")
    assert await remove_member(session, workspace.id, "user-1") is True
    assert await remove_member(session, workspace.id, "user-1") is False


async def test_save_profile_appends_next_version(session, workspace):
    saved = await save_profile(
        session, workspace.id, THIRTY_X_PROFILE, created_by="user-1", expected_version=1
    )
    assert saved.version == 2
    assert saved.created_by == "user-1"
    latest = await current_profile(session, workspace.id)
    assert latest is not None and latest.version == 2


async def test_save_profile_with_stale_version_raises_conflict(session, workspace):
    await save_profile(
        session, workspace.id, THIRTY_X_PROFILE, created_by="user-1", expected_version=1
    )
    with pytest.raises(ProfileConflict):
        await save_profile(
            session, workspace.id, THIRTY_X_PROFILE, created_by="user-2", expected_version=1
        )


async def test_require_editor_401_without_user_403_for_non_member(workspace):
    anonymous = WorkspaceAccess(workspace=workspace, user=None, role=None)
    with pytest.raises(HTTPException) as unauthorized:
        await require_editor(anonymous)
    assert unauthorized.value.status_code == 401

    stranger = WorkspaceAccess(workspace=workspace, user=CurrentUser(user_id="x"), role=None)
    with pytest.raises(HTTPException) as forbidden:
        await require_editor(stranger)
    assert forbidden.value.status_code == 403
    assert forbidden.value.detail == "Solo el equipo de 30X puede cambiar esto."

    member = WorkspaceAccess(workspace=workspace, user=CurrentUser(user_id="x"), role="member")
    assert await require_editor(member) is member


async def test_cli_add_then_remove(session, session_factory, workspace):
    workspace_id = workspace.id
    assert await run(["add", "--user-id", "u1", "--role", "owner"], session_factory) == 0
    assert await member_role(session, workspace_id, "u1") == "owner"
    assert await run(["remove", "--user-id", "u1"], session_factory) == 0
    assert await member_role(session, workspace_id, "u1") is None
