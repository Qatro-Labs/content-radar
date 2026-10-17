"""`load_pieces` contra la DB de tests: con `as_of` en el pasado no entra nada posterior."""

from datetime import UTC, datetime, timedelta

from app.models import ContentItem, MetricSnapshot, Source
from app.schemas.signal import Metrics
from app.services.opportunities import load_pieces

AS_OF = datetime(2026, 10, 17, 12, tzinfo=UTC)


def item(source: Source, n: int, *, published_at: datetime, last_observed_at: datetime):
    return ContentItem(
        source=source,
        platform="hackernews",
        external_id=str(n),
        url=f"https://news.ycombinator.com/item?id={n}",
        title=f"Story {n}",
        published_at=published_at,
        first_observed_at=published_at,
        last_observed_at=last_observed_at,
    )


async def test_load_pieces_ignores_the_future(session):
    src = Source(
        platform="hackernews", kind="query", external_id="llm", name="HN · LLM", segment="tech"
    )
    before = item(
        src, 1, published_at=AS_OF - timedelta(hours=5), last_observed_at=AS_OF + timedelta(hours=1)
    )
    before.snapshots = [
        MetricSnapshot(observed_at=AS_OF - timedelta(hours=2), points=40),
        MetricSnapshot(observed_at=AS_OF + timedelta(hours=1), points=90),
    ]
    future = item(
        src, 2, published_at=AS_OF + timedelta(hours=1), last_observed_at=AS_OF + timedelta(hours=1)
    )
    no_snapshots = item(
        src, 3, published_at=AS_OF - timedelta(hours=8), last_observed_at=AS_OF + timedelta(hours=1)
    )
    session.add_all([src, before, future, no_snapshots])
    await session.commit()

    pieces = await load_pieces(session, AS_OF)

    assert [p.item_id for p in pieces] == [before.id, no_snapshots.id]
    first, third = pieces
    assert len(first.snapshots) == 1
    assert first.metrics == Metrics(points=40)
    assert first.observed_at == AS_OF - timedelta(hours=2)
    assert third.metrics == Metrics()
    assert third.snapshots == []
    assert third.observed_at == AS_OF


async def test_load_pieces_ignores_pieces_first_observed_after_as_of(session):
    src = Source(
        platform="hackernews", kind="query", external_id="llm", name="HN · LLM", segment="tech"
    )
    late = item(
        src, 1, published_at=AS_OF - timedelta(hours=5), last_observed_at=AS_OF + timedelta(hours=3)
    )
    late.first_observed_at = AS_OF + timedelta(hours=2)  # recolectada después de as_of
    session.add_all([src, late])
    await session.commit()

    assert await load_pieces(session, AS_OF) == []


async def test_load_pieces_carries_target_url(session):
    src = Source(
        platform="hackernews", kind="query", external_id="llm", name="HN · LLM", segment="tech"
    )
    linked = item(src, 1, published_at=AS_OF - timedelta(hours=5), last_observed_at=AS_OF)
    linked.target_url = "https://arstechnica.com/ai/nota"
    text_only = item(src, 2, published_at=AS_OF - timedelta(hours=4), last_observed_at=AS_OF)
    session.add_all([src, linked, text_only])
    await session.commit()

    pieces = await load_pieces(session, AS_OF)

    assert [p.target_url for p in pieces] == ["https://arstechnica.com/ai/nota", None]
