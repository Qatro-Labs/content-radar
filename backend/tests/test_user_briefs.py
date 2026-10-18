"""Briefs guardados por usuario: tokens de Supabase firmados aquí y un JWKS falso, sin red."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.agent.limits import RateLimiter
from app.api.auth import SupabaseJwks, get_signing_keys
from app.api.routes.editorial import get_brief_limiter, get_briefer
from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.main import app
from app.models import EditorialBriefRecord
from app.schemas.editorial import BriefFormat
from tests.test_auth import SUPABASE_URL, USER_ID, FakeFetcher, bearer, token
from tests.test_editorial_brief import FakeBriefer, body, seed

OTHER_USER_ID = "8f1c2d3e-0000-4000-8000-000000000002"


@pytest.fixture
def configure(session):
    async def override():
        yield session

    def apply(*, auth_required: bool = True) -> None:
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


async def saved_count(session) -> int:
    return await session.scalar(select(func.count()).select_from(EditorialBriefRecord)) or 0


async def test_post_with_a_user_saves_the_brief_and_returns_its_id(session, configure, client):
    configure()
    opportunity_id = await seed(session)

    response = await client.post(
        "/api/v1/editorial/brief", json=body(opportunity_id), headers=bearer(token())
    )

    assert response.status_code == 200
    brief_id = response.json()["id"]
    record = await session.get(EditorialBriefRecord, brief_id)
    assert record is not None and record.user_id == USER_ID
    assert record.opportunity_id == opportunity_id and record.run_id is not None


async def test_flag_off_with_a_valid_token_still_saves(session, configure, client):
    configure(auth_required=False)
    opportunity_id = await seed(session)

    response = await client.post(
        "/api/v1/editorial/brief", json=body(opportunity_id), headers=bearer(token())
    )

    assert response.status_code == 200 and response.json()["id"] is not None


@pytest.mark.parametrize(
    ("auth_required", "headers"),
    [(False, None), (False, bearer(token(aud="anon")))],
    ids=["no-token", "flag-off-invalid-token"],
)
async def test_post_without_a_user_saves_nothing(
    session, configure, client, auth_required, headers
):
    configure(auth_required=auth_required)
    opportunity_id = await seed(session)

    response = await client.post(
        "/api/v1/editorial/brief", json=body(opportunity_id), headers=headers
    )

    assert response.status_code == 200
    assert response.json()["id"] is None
    assert await saved_count(session) == 0


async def test_each_user_gets_a_row_even_when_the_brief_comes_from_the_cache(
    session, configure, client
):
    configure()
    opportunity_id = await seed(session)

    for sub in (USER_ID, OTHER_USER_ID):
        await client.post(
            "/api/v1/editorial/brief", json=body(opportunity_id), headers=bearer(token(sub=sub))
        )

    assert await saved_count(session) == 2


async def test_list_shows_only_own_briefs_newest_first(session, configure, client):
    configure()
    opportunity_id = await seed(session)
    mine = bearer(token())
    first = await client.post("/api/v1/editorial/brief", json=body(opportunity_id), headers=mine)
    article = {**body(opportunity_id), "format": BriefFormat.ARTICLE.value}
    second = await client.post("/api/v1/editorial/brief", json=article, headers=mine)
    await client.post(
        "/api/v1/editorial/brief",
        json=body(opportunity_id),
        headers=bearer(token(sub=OTHER_USER_ID)),
    )

    response = await client.get("/api/v1/editorial/briefs", headers=mine)

    assert response.status_code == 200
    items = response.json()
    assert [i["id"] for i in items] == [second.json()["id"], first.json()["id"]]
    assert items[0]["format"] == "article" and items[0]["topic"] == first.json()["topic"]


async def test_detail_returns_the_request_and_the_brief(session, configure, client):
    configure()
    opportunity_id = await seed(session)
    created = await client.post(
        "/api/v1/editorial/brief", json=body(opportunity_id), headers=bearer(token())
    )
    brief_id = created.json()["id"]

    response = await client.get(f"/api/v1/editorial/briefs/{brief_id}", headers=bearer(token()))

    assert response.status_code == 200
    saved = response.json()
    assert saved["request"] == body(opportunity_id)
    assert saved["brief"] == created.json()


async def test_another_users_brief_is_404(session, configure, client):
    configure()
    opportunity_id = await seed(session)
    created = await client.post(
        "/api/v1/editorial/brief", json=body(opportunity_id), headers=bearer(token())
    )
    path = f"/api/v1/editorial/briefs/{created.json()['id']}"
    other = bearer(token(sub=OTHER_USER_ID))

    read = await client.get(path, headers=other)
    deleted = await client.delete(path, headers=other)
    missing = await client.get("/api/v1/editorial/briefs/999999", headers=bearer(token()))

    assert (read.status_code, deleted.status_code, missing.status_code) == (404, 404, 404)
    assert await saved_count(session) == 1


async def test_owner_deletes_the_brief(session, configure, client):
    configure()
    opportunity_id = await seed(session)
    created = await client.post(
        "/api/v1/editorial/brief", json=body(opportunity_id), headers=bearer(token())
    )

    response = await client.delete(
        f"/api/v1/editorial/briefs/{created.json()['id']}", headers=bearer(token())
    )

    assert response.status_code == 204
    assert await saved_count(session) == 0


@pytest.mark.parametrize("auth_required", [False, True], ids=["flag-off", "flag-on"])
@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/api/v1/editorial/briefs"),
        ("GET", "/api/v1/editorial/briefs/1"),
        ("DELETE", "/api/v1/editorial/briefs/1"),
    ],
    ids=["list", "detail", "delete"],
)
async def test_saved_briefs_without_token_are_401(configure, client, auth_required, method, path):
    configure(auth_required=auth_required)

    response = await client.request(method, path)

    assert response.status_code == 401
