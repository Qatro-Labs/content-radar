"""Briefs del equipo del workspace: tokens de Supabase firmados aquí y un JWKS falso, sin red."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.agent.limits import RateLimiter
from app.api.auth import SupabaseJwks, get_signing_keys
from app.api.routes.editorial import get_brief_limiter, get_briefer
from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.jobs.seed_workspace import seed_thirty_x
from app.main import app
from app.models import EditorialBriefRecord
from app.models.workspaces import WorkspaceRecord
from app.schemas.editorial import BriefFormat
from app.services.workspaces import add_member
from tests.test_auth import SUPABASE_URL, USER_ID, FakeFetcher, bearer, token
from tests.test_editorial_brief import FakeBriefer, body, seed

OTHER_MEMBER_ID = "8f1c2d3e-0000-4000-8000-000000000002"
STRANGER_ID = "8f1c2d3e-0000-4000-8000-000000000003"
BRIEF = "/api/v1/editorial/brief"
BRIEFS = "/api/v1/editorial/briefs"
FOREIGN_BRIEF_ID = 987654

MEMBER = bearer(token())
OTHER_MEMBER = bearer(token(sub=OTHER_MEMBER_ID))
STRANGER = bearer(token(sub=STRANGER_ID))


@pytest.fixture
def configure(session):
    async def override():
        yield session

    def apply(*, auth_required: bool = False) -> None:
        settings = Settings(auth_required=auth_required, supabase_url=SUPABASE_URL)
        keys = SupabaseJwks(FakeFetcher())
        limiter = RateLimiter(per_ip_per_hour=20, global_per_day=300)
        app.dependency_overrides[get_settings] = lambda: settings
        app.dependency_overrides[get_signing_keys] = lambda: keys
        app.dependency_overrides[get_session] = override
        app.dependency_overrides[get_brief_limiter] = lambda: limiter
        app.dependency_overrides[get_briefer] = FakeBriefer

    try:
        yield apply
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def workspace(session):
    workspace = await seed_thirty_x(session)
    await add_member(session, workspace.id, USER_ID, "owner")
    await add_member(session, workspace.id, OTHER_MEMBER_ID, "member")
    return workspace


async def saved_count(session) -> int:
    return await session.scalar(select(func.count()).select_from(EditorialBriefRecord)) or 0


async def brief_in_other_workspace(session, opportunity_id: str) -> int:
    other = WorkspaceRecord(slug="otro", name="Otro", public_demo=True)
    session.add(other)
    await session.flush()
    session.add(
        EditorialBriefRecord(
            id=FOREIGN_BRIEF_ID,
            root_id=FOREIGN_BRIEF_ID,
            version=1,
            workspace_id=other.id,
            created_by=STRANGER_ID,
            opportunity_id=opportunity_id,
            run_id=None,
            request=body(opportunity_id),
            brief={"topic": "Ajeno"},
        )
    )
    await session.commit()
    return FOREIGN_BRIEF_ID


async def test_member_post_saves_the_brief_in_the_workspace(session, configure, client, workspace):
    configure()
    opportunity_id = await seed(session)

    response = await client.post(BRIEF, json=body(opportunity_id), headers=MEMBER)

    assert response.status_code == 200
    record = await session.get(EditorialBriefRecord, response.json()["id"])
    assert record is not None
    assert (record.workspace_id, record.created_by) == (workspace.id, USER_ID)
    assert record.opportunity_id == opportunity_id and record.run_id is not None


@pytest.mark.parametrize(
    ("auth_required", "headers"),
    [(False, None), (False, bearer(token(aud="anon"))), (False, STRANGER), (True, STRANGER)],
    ids=["no-token", "invalid-token", "stranger", "stranger-flag-on"],
)
async def test_non_member_post_returns_brief_without_saving(
    session, configure, client, workspace, auth_required, headers
):
    configure(auth_required=auth_required)
    opportunity_id = await seed(session)

    response = await client.post(BRIEF, json=body(opportunity_id), headers=headers)

    assert response.status_code == 200
    assert response.json()["id"] is None and response.json()["version"] is None
    assert await saved_count(session) == 0


async def test_anonymous_lists_team_briefs_of_public_workspace(
    session, configure, client, workspace
):
    configure()
    opportunity_id = await seed(session)
    first = await client.post(BRIEF, json=body(opportunity_id), headers=MEMBER)
    article = {**body(opportunity_id), "format": BriefFormat.ARTICLE.value}
    second = await client.post(BRIEF, json=article, headers=OTHER_MEMBER)

    listed = await client.get(BRIEFS)
    detail = await client.get(f"{BRIEFS}/{first.json()['id']}")

    assert listed.status_code == 200
    items = listed.json()
    assert [i["id"] for i in items] == [second.json()["id"], first.json()["id"]]
    assert items[0]["format"] == "article" and items[0]["topic"] == first.json()["topic"]
    assert detail.status_code == 200
    assert detail.json()["request"] == body(opportunity_id)
    assert detail.json()["brief"] == first.json()


async def test_any_member_sees_briefs_created_by_another_member(
    session, configure, client, workspace
):
    configure()
    opportunity_id = await seed(session)
    created = await client.post(BRIEF, json=body(opportunity_id), headers=MEMBER)

    listed = await client.get(BRIEFS, headers=OTHER_MEMBER)
    detail = await client.get(f"{BRIEFS}/{created.json()['id']}", headers=OTHER_MEMBER)

    assert [i["id"] for i in listed.json()] == [created.json()["id"]]
    assert detail.status_code == 200


async def test_brief_of_another_workspace_is_404(session, configure, client, workspace):
    configure()
    opportunity_id = await seed(session)
    foreign = await brief_in_other_workspace(session, opportunity_id)

    read = await client.get(f"{BRIEFS}/{foreign}", headers=MEMBER)
    deleted = await client.delete(f"{BRIEFS}/{foreign}", headers=MEMBER)
    listed = await client.get(BRIEFS, headers=MEMBER)
    missing = await client.get(f"{BRIEFS}/999999", headers=MEMBER)

    assert (read.status_code, deleted.status_code, missing.status_code) == (404, 404, 404)
    assert listed.json() == []
    assert await saved_count(session) == 1


async def test_member_deletes_a_brief_created_by_another_member(
    session, configure, client, workspace
):
    configure()
    opportunity_id = await seed(session)
    created = await client.post(BRIEF, json=body(opportunity_id), headers=MEMBER)

    response = await client.delete(f"{BRIEFS}/{created.json()['id']}", headers=OTHER_MEMBER)

    assert response.status_code == 204
    assert await saved_count(session) == 0


async def test_non_member_delete_is_403_and_keeps_the_brief(session, configure, client, workspace):
    configure()
    opportunity_id = await seed(session)
    created = await client.post(BRIEF, json=body(opportunity_id), headers=MEMBER)

    response = await client.delete(f"{BRIEFS}/{created.json()['id']}", headers=STRANGER)

    assert response.status_code == 403
    assert await saved_count(session) == 1


@pytest.mark.parametrize("auth_required", [False, True], ids=["flag-off", "flag-on"])
async def test_anonymous_delete_is_401(session, configure, client, workspace, auth_required):
    configure(auth_required=auth_required)
    opportunity_id = await seed(session)
    created = await client.post(BRIEF, json=body(opportunity_id), headers=MEMBER)

    response = await client.delete(f"{BRIEFS}/{created.json()['id']}")

    assert response.status_code == 401
    assert await saved_count(session) == 1


async def test_private_workspace_briefs_are_404_without_membership(
    session, configure, client, workspace
):
    configure()
    workspace.public_demo = False
    await session.commit()

    anonymous = await client.get(BRIEFS)
    stranger = await client.get(BRIEFS, headers=STRANGER)
    member = await client.get(BRIEFS, headers=MEMBER)

    assert (anonymous.status_code, stranger.status_code, member.status_code) == (404, 404, 200)


# --- versiones ----------------------------------------------------------------------------


def with_format(opportunity_id: str, fmt: BriefFormat, parent: int | None = None) -> dict:
    return {**body(opportunity_id), "format": fmt.value, "parent_brief_id": parent}


async def test_regenerating_from_a_parent_adds_version_2_to_its_chain(
    session, configure, client, workspace
):
    configure()
    opportunity_id = await seed(session)
    first = (await client.post(BRIEF, json=body(opportunity_id), headers=MEMBER)).json()

    # Otro miembro regenera: la cadena es del equipo, no de quien la empezó.
    second = await client.post(
        BRIEF,
        json=with_format(opportunity_id, BriefFormat.ARTICLE, parent=first["id"]),
        headers=OTHER_MEMBER,
    )

    assert second.status_code == 200
    assert (first["version"], second.json()["version"]) == (1, 2)
    record = await session.get(EditorialBriefRecord, second.json()["id"])
    assert record is not None and record.root_id == first["id"]
    assert record.created_by == OTHER_MEMBER_ID


@pytest.mark.parametrize("with_parent", [True, False], ids=["with-parent", "without-parent"])
async def test_the_same_request_again_returns_the_existing_version(
    session, configure, client, workspace, with_parent
):
    configure()
    opportunity_id = await seed(session)
    first = (await client.post(BRIEF, json=body(opportunity_id), headers=MEMBER)).json()
    again = {**body(opportunity_id), "parent_brief_id": first["id"] if with_parent else None}

    response = await client.post(BRIEF, json=again, headers=MEMBER)

    assert (response.json()["id"], response.json()["version"]) == (first["id"], 1)
    assert await saved_count(session) == 1


async def test_parent_from_another_workspace_is_404(session, configure, client, workspace):
    configure()
    opportunity_id = await seed(session)
    foreign = await brief_in_other_workspace(session, opportunity_id)

    response = await client.post(
        BRIEF,
        json=with_format(opportunity_id, BriefFormat.ARTICLE, parent=foreign),
        headers=MEMBER,
    )

    assert response.status_code == 404
    assert await saved_count(session) == 1


async def chain_of_two(client, opportunity_id: str) -> tuple[dict, dict]:
    first = (await client.post(BRIEF, json=body(opportunity_id), headers=MEMBER)).json()
    second = await client.post(
        BRIEF,
        json=with_format(opportunity_id, BriefFormat.ARTICLE, parent=first["id"]),
        headers=MEMBER,
    )
    return first, second.json()


async def test_list_shows_one_row_per_chain_with_its_latest_version(
    session, configure, client, workspace
):
    configure()
    opportunity_id = await seed(session)
    first, second = await chain_of_two(client, opportunity_id)

    items = (await client.get(BRIEFS, headers=MEMBER)).json()

    assert len(items) == 1
    item = items[0]
    assert (item["id"], item["root_id"], item["version"], item["version_count"]) == (
        second["id"],
        first["id"],
        2,
        2,
    )
    assert item["format"] == "article"


async def test_detail_lists_every_version_in_order(session, configure, client, workspace):
    configure()
    opportunity_id = await seed(session)
    first, second = await chain_of_two(client, opportunity_id)

    response = await client.get(f"{BRIEFS}/{first['id']}", headers=MEMBER)

    saved = response.json()
    assert (saved["id"], saved["version"], saved["root_id"]) == (first["id"], 1, first["id"])
    assert [(v["id"], v["version"], v["format"]) for v in saved["versions"]] == [
        (first["id"], 1, "carousel"),
        (second["id"], 2, "article"),
    ]


async def test_delete_removes_the_whole_chain(session, configure, client, workspace):
    configure()
    opportunity_id = await seed(session)
    _, second = await chain_of_two(client, opportunity_id)

    response = await client.delete(f"{BRIEFS}/{second['id']}", headers=MEMBER)

    assert response.status_code == 204
    assert await saved_count(session) == 0
