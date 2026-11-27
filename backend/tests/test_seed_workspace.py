from sqlalchemy import func, select

from app.jobs.seed_workspace import THIRTY_X_PROFILE, seed_thirty_x
from app.models.workspaces import RadarProfileRecord, WorkspaceRecord
from app.schemas.profile import RadarProfile


async def _profiles(session, workspace_id: int) -> list[RadarProfileRecord]:
    rows = await session.scalars(
        select(RadarProfileRecord)
        .where(RadarProfileRecord.workspace_id == workspace_id)
        .order_by(RadarProfileRecord.version)
    )
    return list(rows)


async def test_seed_creates_public_thirty_x_with_profile_v1(session):
    workspace = await seed_thirty_x(session)

    assert workspace.slug == "30x"
    assert workspace.name == "30X"
    assert workspace.public_demo is True
    (record,) = await _profiles(session, workspace.id)
    assert record.version == 1
    assert record.created_by is None
    assert RadarProfile.model_validate(record.profile) == THIRTY_X_PROFILE


async def test_seed_twice_keeps_one_workspace_and_one_profile(session):
    first = await seed_thirty_x(session)
    second = await seed_thirty_x(session)

    assert first.id == second.id
    assert await session.scalar(select(func.count()).select_from(WorkspaceRecord)) == 1
    assert len(await _profiles(session, first.id)) == 1


async def test_seed_does_not_overwrite_an_edited_profile(session):
    workspace = await seed_thirty_x(session)
    edited = THIRTY_X_PROFILE.model_copy(update={"call_to_action": "Escríbenos"})
    session.add(
        RadarProfileRecord(
            workspace_id=workspace.id,
            version=2,
            profile=edited.model_dump(mode="json"),
            created_by="user-1",
        )
    )
    await session.commit()

    await seed_thirty_x(session)

    records = await _profiles(session, workspace.id)
    assert [r.version for r in records] == [1, 2]
    assert RadarProfile.model_validate(records[1].profile) == edited
