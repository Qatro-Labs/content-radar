"""Búsqueda por texto en las piezas recolectadas (contra radar_test)."""

from datetime import UTC, datetime, timedelta
from urllib.parse import quote

import pytest

from app.models import ContentItem, MetricSnapshot, Source
from app.schemas.signal import Platform, Segment
from app.services.signals import search_signals
from tests.test_opportunity_routes import add_run, fixture_results

NOW = datetime(2026, 10, 17, 12, tzinfo=UTC)
WEEK_AGO = NOW - timedelta(days=7)
OPP_001_URL = "https://example.com/mock/1"


def source(
    name: str = "YT negocio",
    *,
    platform: Platform = Platform.YOUTUBE,
    segment: Segment = Segment.BUSINESS,
    active: bool = True,
) -> Source:
    return Source(
        platform=platform.value,
        kind="channel",
        external_id=name,
        name=name,
        segment=segment.value,
        region="co",
        active=active,
    )


def item(
    src: Source,
    title: str,
    *,
    description: str | None = None,
    url: str | None = None,
    published_at: datetime = NOW - timedelta(days=1),
) -> ContentItem:
    return ContentItem(
        source=src,
        platform=src.platform,
        external_id=f"{src.name}:{title}",
        url=url or f"https://example.com/{quote(src.name)}/{quote(title)}",
        title=title,
        description=description,
        published_at=published_at,
        first_observed_at=published_at,
        last_observed_at=published_at + timedelta(hours=2),
    )


async def search(session, query: str, **filters):
    return await search_signals(
        session,
        query=query,
        platform=filters.get("platform"),
        segment=filters.get("segment"),
        since=filters.get("since", WEEK_AGO),
        limit=filters.get("limit", 10),
    )


async def test_every_term_must_match_title_or_description_ignoring_case(session):
    src = source()
    session.add_all(
        [
            item(src, "Agentes en la empresa", description="Cómo la IA cambia el trabajo"),
            item(src, "Agentes secretos"),
        ]
    )
    await session.commit()

    hits = await search(session, "Agentes IA")

    assert [h.title for h in hits] == ["Agentes en la empresa"]


@pytest.mark.parametrize(
    ("query", "hit", "miss"),
    [("100%", "100% remoto", "1000 empresas"), ("a_b", "a_b", "axb")],
    ids=["percent", "underscore"],
)
async def test_like_wildcards_are_literal(session, query, hit, miss):
    src = source()
    session.add_all([item(src, hit), item(src, miss)])
    await session.commit()

    hits = await search(session, query)

    assert [h.title for h in hits] == [hit]


async def test_latest_snapshot_metrics_and_null_without_snapshots(session):
    src = source()
    measured = item(src, "Agentes medidos", published_at=NOW - timedelta(days=2))
    unmeasured = item(src, "Agentes sin medir", published_at=NOW - timedelta(days=3))
    latest_at = NOW - timedelta(hours=1)
    # El más reciente se añade primero: la búsqueda no puede fiarse del orden de la colección.
    measured.snapshots = [
        MetricSnapshot(observed_at=latest_at, views=50, likes=5),
        MetricSnapshot(observed_at=NOW - timedelta(days=1), views=10, likes=1),
    ]
    session.add_all([measured, unmeasured])
    await session.commit()

    by_title = {h.title: h for h in await search(session, "agentes")}

    assert by_title["Agentes medidos"].metrics.views == 50
    assert by_title["Agentes medidos"].metrics.likes == 5
    assert by_title["Agentes medidos"].observed_at == latest_at
    empty = by_title["Agentes sin medir"]
    assert all(v is None for v in empty.metrics.model_dump().values())
    assert empty.observed_at == unmeasured.last_observed_at


async def test_filters_by_days_platform_segment_and_inactive_sources(session):
    youtube = source()
    inactive = source("YT apagado", active=False)
    rss = source("Blog tech", platform=Platform.RSS, segment=Segment.TECH)
    session.add_all(
        [
            item(youtube, "Agentes de esta semana"),
            item(youtube, "Agentes viejos", published_at=NOW - timedelta(days=10)),
            item(inactive, "Agentes de una fuente apagada"),
            item(rss, "Agentes en un blog"),
        ]
    )
    await session.commit()

    youtube_hits = await search(session, "agentes", platform=Platform.YOUTUBE)
    tech_hits = await search(session, "agentes", segment=Segment.TECH)

    assert [h.title for h in youtube_hits] == ["Agentes de esta semana"]
    assert [h.title for h in tech_hits] == ["Agentes en un blog"]


async def test_hits_carry_the_served_opportunity_ids(session):
    await add_run(session, fixture_results())
    src = source()
    session.add_all(
        [
            item(src, "Agentes en el ranking", url=OPP_001_URL),
            item(src, "Agentes fuera del ranking", published_at=NOW - timedelta(days=2)),
        ]
    )
    await session.commit()

    hits = await search(session, "agentes")

    assert [(h.title, h.opportunity_ids) for h in hits] == [
        ("Agentes en el ranking", ["opp_001"]),
        ("Agentes fuera del ranking", []),
    ]


async def test_query_without_valid_terms_raises(session):
    with pytest.raises(ValueError):
        await search(session, "a")
