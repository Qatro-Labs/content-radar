from datetime import UTC, datetime, timedelta

from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.db.session import get_session
from app.main import app
from app.models import ContentItem, MetricSnapshot, Source
from app.schemas.signal import ContentFormat, ContentSignal, Metrics, Platform
from app.services.signals import store_signals

T0 = datetime(2026, 10, 16, 20, 0, tzinfo=UTC)


def signal(
    observed_at: datetime,
    views: int,
    title: str = "Agentes de IA en ventas",
    description: str | None = None,
):
    return ContentSignal(
        platform=Platform.YOUTUBE,
        external_id="vid123",
        url="https://www.youtube.com/watch?v=vid123",
        title=title,
        description=description,
        author_name="Canal Ejemplo",
        published_at=T0 - timedelta(days=2),
        observed_at=observed_at,
        format=ContentFormat.LONG_VIDEO,
        language="es",
        metrics=Metrics(views=views, likes=10, comments=2),
    )


async def make_source(session) -> Source:
    src = Source(
        platform="youtube",
        kind="channel",
        external_id="UC123",
        name="Canal Ejemplo",
        segment="latam_es",
        language="es",
    )
    session.add(src)
    await session.commit()
    return src


async def test_dedupes_items_and_keeps_snapshot_history(session):
    src = await make_source(session)

    await store_signals(session, src, [signal(T0, 1000)])
    result = await store_signals(
        session, src, [signal(T0 + timedelta(hours=2), 1600, "Título nuevo")]
    )

    assert result.snapshots_inserted == 1
    assert await session.scalar(select(func.count(ContentItem.id))) == 1
    views = (
        await session.scalars(select(MetricSnapshot.views).order_by(MetricSnapshot.observed_at))
    ).all()
    assert views == [1000, 1600]

    item = await session.scalar(select(ContentItem))
    assert item.title == "Título nuevo"
    assert item.first_observed_at == T0
    assert item.last_observed_at == T0 + timedelta(hours=2)


async def test_missing_description_does_not_erase_existing(session):
    src = await make_source(session)
    await store_signals(session, src, [signal(T0, 1000, description="Resumen original")])
    await store_signals(
        session,
        src,
        [signal(T0 + timedelta(hours=1), 1200, description="Resumen nuevo")],
    )
    item = await session.scalar(select(ContentItem))
    assert item.description == "Resumen nuevo"

    await store_signals(session, src, [signal(T0 + timedelta(hours=2), 1400)])
    item = await session.scalar(select(ContentItem))
    assert item.description == "Resumen nuevo"


async def test_same_observation_is_not_duplicated(session):
    src = await make_source(session)
    await store_signals(session, src, [signal(T0, 1000)])
    result = await store_signals(session, src, [signal(T0, 1000)])
    assert result.snapshots_inserted == 0


async def test_health_and_sources_status(session):
    src = await make_source(session)
    await store_signals(session, src, [signal(T0, 1000)])

    async def override():
        yield session

    app.dependency_overrides[get_session] = override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            health = (await client.get("/health")).json()
            status = (await client.get("/api/v1/sources/status")).json()
    finally:
        app.dependency_overrides.clear()

    assert health["db"] == "ok"
    assert status == [
        {
            "id": src.id,
            "platform": "youtube",
            "name": "Canal Ejemplo",
            "segment": "latam_es",
            "active": True,
            "items": 1,
            "last_observed_at": "2026-10-16T20:00:00Z",
        }
    ]
