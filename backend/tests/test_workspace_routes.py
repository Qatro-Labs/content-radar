"""Rutas /workspace y /profile: tokens de Supabase firmados aquí y un JWKS falso, sin red."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, select

from app.api.auth import SupabaseJwks, get_signing_keys
from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.jobs.seed_workspace import THIRTY_X_PROFILE, seed_thirty_x
from app.main import app
from app.models.workspaces import RadarProfileRecord
from app.services.workspaces import add_member
from tests.test_auth import SUPABASE_URL, USER_ID, FakeFetcher, bearer, token

STRANGER_ID = "8f1c2d3e-0000-4000-8000-000000000002"
PROFILE = "/api/v1/profile"
WORKSPACE = "/api/v1/workspace"
CONFLICT = (
    "Alguien del equipo guardó cambios mientras editabas. Recarga para ver la última versión."
)


@pytest.fixture
async def client(session):
    async def override():
        yield session

    settings = Settings(supabase_url=SUPABASE_URL)
    keys = SupabaseJwks(FakeFetcher())
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_signing_keys] = lambda: keys
    app.dependency_overrides[get_session] = override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
async def workspace(session):
    return await seed_thirty_x(session)


@pytest.fixture
async def member(session, workspace):
    await add_member(session, workspace.id, USER_ID, "member")
    return bearer(token())


def update_body(version: int, **changes) -> dict:
    profile = THIRTY_X_PROFILE.model_dump(mode="json") | changes
    return {"profile": profile, "expected_version": version}


async def version_count(session) -> int:
    return await session.scalar(select(func.count()).select_from(RadarProfileRecord)) or 0


async def test_anonymous_reads_public_profile_without_edit_rights(client, workspace):
    response = await client.get(PROFILE)

    assert response.status_code == 200
    body = response.json()
    assert body["can_edit"] is False and body["version"] == 1
    assert body["profile"]["creates_about"] == THIRTY_X_PROFILE.creates_about


async def test_workspace_shows_role_for_member_and_none_for_stranger(client, member):
    as_member = await client.get(WORKSPACE, headers=member)
    as_stranger = await client.get(WORKSPACE, headers=bearer(token(sub=STRANGER_ID)))

    assert as_member.json() == {"slug": "30x", "name": "30X", "public_demo": True, "role": "member"}
    assert as_stranger.json()["role"] is None


async def test_put_without_token_is_401_and_changes_nothing(client, session, workspace):
    response = await client.put(PROFILE, json=update_body(1))

    assert response.status_code == 401
    assert await version_count(session) == 1


async def test_put_by_non_member_is_403_and_changes_nothing(client, session, workspace):
    response = await client.put(
        PROFILE, json=update_body(1), headers=bearer(token(sub=STRANGER_ID))
    )

    assert response.status_code == 403
    assert await version_count(session) == 1


async def test_member_put_creates_version_2(client, session, member):
    response = await client.put(
        PROFILE, json=update_body(1, creates_about="Otro tema"), headers=member
    )

    assert response.status_code == 200
    body = response.json()
    assert body["version"] == 2 and body["can_edit"] is True
    assert body["profile"]["creates_about"] == "Otro tema"
    assert (await client.get(PROFILE)).json()["version"] == 2
    assert await version_count(session) == 2


async def test_put_with_stale_version_is_409(client, session, member):
    await client.put(PROFILE, json=update_body(1), headers=member)

    response = await client.put(PROFILE, json=update_body(1), headers=member)

    assert response.status_code == 409
    assert response.json()["detail"] == CONFLICT
    assert await version_count(session) == 2


async def test_markup_in_profile_round_trips_verbatim(client, member):
    markup = "<b>negrita</b> & {{plantilla}} <script>x</script>"

    await client.put(PROFILE, json=update_body(1, never_say=markup), headers=member)

    assert (await client.get(PROFILE)).json()["profile"]["never_say"] == markup


async def test_workspace_without_profile_is_404(client, session, workspace):
    await session.execute(delete(RadarProfileRecord))
    await session.commit()

    response = await client.get(PROFILE)

    assert response.status_code == 404
    assert response.json()["detail"] == "Este espacio todavía no tiene perfil de marca."


async def test_missing_workspace_is_404_and_opportunities_still_work(client, seeded):
    workspace_response = await client.get(WORKSPACE)
    profile_response = await client.get(PROFILE)
    opportunities = await client.get("/api/v1/opportunities")

    assert workspace_response.status_code == 404
    assert profile_response.status_code == 404
    assert opportunities.status_code == 200 and opportunities.json() is not None
