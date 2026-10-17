"""Ensamblado de oportunidades a partir de piezas ya agrupadas. Sin DB ni modelo de embeddings."""

from datetime import UTC, datetime, timedelta

from app.intelligence.opportunities import Piece, build_opportunities, outlier_ratios
from app.schemas.opportunity import Collection, Lifecycle
from app.schemas.signal import Metrics, Platform, Segment, SourceKind

AS_OF = datetime(2026, 10, 17, 12, tzinfo=UTC)
STARTED = datetime(2026, 10, 16, tzinfo=UTC)


def piece(
    i,
    *,
    hours_ago,
    platform=Platform.HACKERNEWS,
    source="HN · LLM",
    points=10,
    seg=None,
    kind=SourceKind.QUERY,
):
    published = AS_OF - timedelta(hours=hours_ago)
    metrics = Metrics(points=points) if platform is Platform.HACKERNEWS else Metrics()
    snapshots = [(AS_OF - timedelta(hours=2), Metrics(points=points // 2)), (AS_OF, metrics)]
    return Piece(
        item_id=i,
        url=f"https://example.com/{i}",
        title=f"Pieza {i}",
        description=None,
        platform=platform,
        source_id=hash(source) % 1000,
        source_name=source,
        segment=seg or Segment.TECH,
        language="en",
        published_at=published,
        observed_at=AS_OF,
        metrics=metrics,
        source_kind=kind,
        snapshots=snapshots if platform is Platform.HACKERNEWS else [],
    )


def test_hn_outlier_ratios_use_p90_of_same_query():
    pieces = [piece(i, hours_ago=10, points=10) for i in range(10)]
    pieces.append(piece(99, hours_ago=10, points=100))
    ratios = outlier_ratios(pieces)
    assert ratios[99] == 10.0  # p90 de la query = 10 puntos
    assert ratios[0] == 1.0
    other = piece(50, hours_ago=10, source="HN · OpenAI", points=100)
    assert outlier_ratios([*pieces, other])[50] is None  # su query no tiene referencia


def test_rss_has_no_metrics_and_no_ratio():
    rss = piece(1, hours_ago=5, platform=Platform.RSS, source="Medio")
    assert outlier_ratios([rss]) == {1: None}


def test_build_opportunities_end_to_end():
    hn = [piece(i, hours_ago=5 + i * 6) for i in range(6)]
    rss = [
        piece(10 + i, hours_ago=3 + i, platform=Platform.RSS, source=f"Medio {i}",
              seg=Segment.LATAM_ES)
        for i in range(3)
    ]  # fmt: skip
    pieces = hn + rss
    results = build_opportunities(
        pieces,
        [list(range(len(pieces)))],
        [0],
        as_of=AS_OF,
        monitoring_started_at=STARTED,
        id_prefix="opp_t",
    )
    assert len(results) == 1
    r = results[0]
    o = r.opportunity
    assert o.id == "opp_t_001"
    assert o.source_count == 4  # HN cuenta como una sola fuente
    assert o.audience_fit_score is None and o.opportunity_score is None
    assert o.lifecycle is not Lifecycle.UNKNOWN
    assert o.audience_mix.latam_es > 0
    assert len(r.evidence) == len(pieces)
    hn_evidence = next(e for e in r.evidence if e.platform is Platform.HACKERNEWS)
    assert hn_evidence.velocity is not None and hn_evidence.velocity.unit == "points/h"
    assert all(e.velocity is None for e in r.evidence if e.platform is Platform.RSS)
    assert len(r.timeline.points) == 6
    assert sum(p.count for p in r.timeline.points) == len(pieces)


def test_inactive_topics_are_skipped():
    old = [piece(i, hours_ago=24 * 10) for i in range(6)]
    assert (
        build_opportunities(
            old, [list(range(6))], [0], as_of=AS_OF, monitoring_started_at=STARTED, id_prefix="x"
        )
        == []
    )


def test_manual_source_is_marked_manual_in_evidence():
    pieces = [piece(i, hours_ago=5 + i * 6) for i in range(5)]
    pieces.append(
        piece(9, hours_ago=4, platform=Platform.RSS, source="Curación", kind=SourceKind.MANUAL)
    )
    [r] = build_opportunities(
        pieces,
        [list(range(len(pieces)))],
        [0],
        as_of=AS_OF,
        monitoring_started_at=STARTED,
        id_prefix="opp_t",
    )
    by_url = {str(e.url): e.collection for e in r.evidence}
    assert by_url.pop("https://example.com/9") is Collection.MANUAL
    assert set(by_url.values()) == {Collection.AUTOMATIC}
