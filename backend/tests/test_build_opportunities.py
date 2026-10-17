"""Ensamblado de oportunidades a partir de piezas ya agrupadas. Sin DB ni modelo de embeddings."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import numpy as np

from app.intelligence.opportunities import Piece, build_opportunities, outlier_ratios
from app.intelligence.outliers import is_outlier
from app.intelligence.replicas import (
    REPLICAS_UNVERIFIED_NOTE,
    ReplicaBasis,
    ReplicaEdge,
    group_stories,
    topic_pairs,
)
from app.schemas.opportunity import Collection, Confidence, GrowthStatus, Lifecycle
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
    assert outlier_ratios(pieces, AS_OF)[99] == 10.0  # p90 de las otras diez = 10 puntos
    other = piece(50, hours_ago=10, source="HN · OpenAI", points=100)
    assert outlier_ratios([*pieces, other], AS_OF)[50] is None  # su query no tiene referencia


def test_piece_is_excluded_from_its_own_reference():
    pieces = [piece(i, hours_ago=10, points=10) for i in range(10)]
    pieces.append(piece(99, hours_ago=10, points=100))
    # Referencia de una de 10: nueve de 10 + la de 100 → p90 = 19 → 10 / 19.
    assert outlier_ratios(pieces, AS_OF)[0] == 0.53


def test_young_pieces_are_scored_but_not_in_reference():
    old = [piece(i, hours_ago=10, points=10) for i in range(6)]
    young = [piece(10 + i, hours_ago=2, points=50) for i in range(5)]
    hit = piece(99, hours_ago=2, points=100)
    ratios = outlier_ratios([*old, *young, hit], AS_OF)
    # p90 de las seis de 10 h = 10. Si las de 2 h contaran, el p90 sería 50 y el ratio 2.0.
    assert ratios[99] == 10.0
    assert all(ratios[p.item_id] is not None for p in young)


def test_youtube_reference_needs_two_days():
    def video(i, hours_ago):
        p = piece(i, hours_ago=hours_ago, platform=Platform.YOUTUBE, source="Canal")
        return replace(p, metrics=Metrics(views=1000))

    videos = [video(i, 72) for i in range(4)] + [video(10 + i, 24) for i in range(3)]
    assert set(outlier_ratios(videos, AS_OF).values()) == {None}  # referencia de 4 < 5


def test_tiktok_ratio_uses_views_per_day_against_same_search():
    def video(i, days_ago, views):
        p = piece(i, hours_ago=24 * days_ago, platform=Platform.TIKTOK, source="TikTok · AI")
        return replace(p, metrics=Metrics(views=views))

    reference = [video(i, 4, 4000) for i in range(5)]  # 1.000 views/día cada uno
    hit = video(99, 2, 12000)  # 6.000 views/día
    assert outlier_ratios([*reference, hit], AS_OF)[99] == 6.0


def test_tiktok_reference_is_the_p90_of_the_search():
    def video(i, views):
        p = piece(i, hours_ago=24 * 4, platform=Platform.TIKTOK, source="TikTok · AI")
        return replace(p, metrics=Metrics(views=views))

    # 1.000 views/día la mayoría y 4.000 los dos de arriba: mediana 1.000, p90 4.000.
    reference = [video(i, 4000) for i in range(8)] + [video(10 + i, 16000) for i in range(2)]
    hit = video(99, 24000)  # 6.000 views/día: 6× la mediana, 1,5× el p90
    ratios = outlier_ratios([*reference, hit], AS_OF)
    assert ratios[99] == 1.5
    assert is_outlier(ratios[99]) is False


def test_instagram_ratio_uses_views_per_day_against_same_profile():
    def reel(i, days_ago, views):
        p = piece(i, hours_ago=24 * days_ago, platform=Platform.INSTAGRAM, source="@creadora")
        return replace(p, metrics=Metrics(views=views))

    reference = [reel(i, 5, 10000) for i in range(5)]  # 2.000 views/día cada uno
    hit = reel(99, 3, 30000)  # 10.000 views/día
    assert outlier_ratios([*reference, hit], AS_OF)[99] == 5.0


def test_reddit_ratio_uses_score_against_same_subreddit():
    def post(i, score):
        p = piece(i, hours_ago=24, platform=Platform.REDDIT, source="r/OpenAI")
        return replace(p, metrics=Metrics(points=score))

    reference = [post(i, 100) for i in range(5)]
    assert outlier_ratios([*reference, post(99, 400)], AS_OF)[99] == 4.0  # mediana 100


def test_rss_has_no_metrics_and_no_ratio():
    rss = piece(1, hours_ago=5, platform=Platform.RSS, source="Medio")
    assert outlier_ratios([rss], AS_OF) == {1: None}


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
    )
    assert len(results) == 1
    r = results[0]
    o = r.opportunity
    assert o.id == "opp_5"  # la pieza HN más antigua
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
        build_opportunities(old, [list(range(6))], [0], as_of=AS_OF, monitoring_started_at=STARTED)
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
    )
    by_url = {str(e.url): e.collection for e in r.evidence}
    assert by_url.pop("https://example.com/9") is Collection.MANUAL
    assert set(by_url.values()) == {Collection.AUTOMATIC}


def build_one(pieces):
    [r] = build_opportunities(
        pieces,
        [list(range(len(pieces)))],
        [0],
        as_of=AS_OF,
        monitoring_started_at=STARTED,
    )
    return r


def test_zero_snapshots():
    pieces = [
        replace(piece(i, hours_ago=5 + i * 10), metrics=Metrics(), snapshots=[]) for i in range(6)
    ]
    r = build_one(pieces)
    assert all(e.velocity is None for e in r.evidence)
    assert all(e.outlier_ratio is None and e.is_outlier is None for e in r.evidence)
    assert r.opportunity.outlier_count == 0
    assert r.opportunity.top_outlier_ratio is None


def test_single_source():
    o = build_one([piece(i, hours_ago=5 + i * 10) for i in range(6)]).opportunity
    assert o.lifecycle is Lifecycle.UNKNOWN
    assert o.confidence is Confidence.LOW
    assert any("una plataforma" in note for note in o.limitations)


def test_empty_previous_window():
    hn = [piece(i, hours_ago=5 + i * 10) for i in range(3)]
    rss = [
        piece(10 + i, hours_ago=3 + i, platform=Platform.RSS, source=f"Medio {i}") for i in range(3)
    ]
    o = build_one(hn + rss).opportunity
    assert o.growth_status is GrowthStatus.ESTIMATED


def test_missing_metric():
    pieces = [piece(i, hours_ago=10) for i in range(6)]
    pieces.append(replace(piece(9, hours_ago=10), metrics=Metrics(points=None)))
    ratios = {str(e.url): e.outlier_ratio for e in build_one(pieces).evidence}
    assert ratios.pop("https://example.com/9") is None
    assert None not in ratios.values()


def test_id_is_anchored_to_the_oldest_piece():
    pieces = [piece(i, hours_ago=5 + i * 10) for i in range(1, 7)]  # la más antigua es la 6
    assert build_one(pieces).opportunity.id == "opp_6"
    newer = piece(7, hours_ago=1)
    assert build_one([*pieces, newer]).opportunity.id == "opp_6"
    tie = piece(0, hours_ago=5 + 6 * 10)  # mismo published_at que la 6, item_id menor
    assert build_one([*pieces, tie]).opportunity.id == "opp_0"


def test_broad_topic_has_limitation():
    pieces = [piece(i, hours_ago=5 + i * 10) for i in range(6)]
    [r] = build_opportunities(
        pieces,
        [list(range(len(pieces)))],
        [0],
        as_of=AS_OF,
        monitoring_started_at=STARTED,
        broad=[True],
    )
    assert any(note.startswith("Tema amplio") for note in r.opportunity.limitations)
    assert not any(
        note.startswith("Tema amplio") for note in build_one(pieces).opportunity.limitations
    )


def _reel(i, days_ago, views):
    p = piece(i, hours_ago=24 * days_ago, platform=Platform.INSTAGRAM, source="@amplia")
    return replace(p, metrics=Metrics(views=views))


def test_off_topic_pieces_complete_the_reference():
    on_topic = [_reel(i, 5, 10000) for i in range(3)]  # 2.000 views/día
    off_topic = [_reel(10 + i, 5, 10000) for i in range(3)]
    hit = _reel(99, 3, 30000)  # 10.000 views/día
    assert outlier_ratios([*on_topic, hit], AS_OF)[99] is None  # referencia de 3 < 5
    ratios = outlier_ratios([*on_topic, hit], AS_OF, reference=[*on_topic, *off_topic, hit])
    assert ratios[99] == 5.0
    assert set(ratios) == {0, 1, 2, 99}  # las de fuera de tema no reciben ratio


def test_off_topic_pieces_never_become_evidence():
    # Menos de dos días: no entran en la referencia, que es solo la de fuera de tema.
    on_topic = [_reel(i, 1.2 + i * 0.1, 10000) for i in range(3)]
    off_topic = [_reel(10 + i, 5, 1000) for i in range(5)]  # 200 views/día
    hit = _reel(99, 1, 30000)
    pieces = [*on_topic, hit]
    [r] = build_opportunities(
        pieces,
        [list(range(len(pieces)))],
        [0],
        as_of=AS_OF,
        monitoring_started_at=STARTED,
        reference=[*pieces, *off_topic],
    )
    assert {str(e.url) for e in r.evidence} == {f"https://example.com/{p.item_id}" for p in pieces}
    assert {p.item_id for p in r.pieces} == {0, 1, 2, 99}
    assert r.opportunity.outlier_count == 4  # todas rinden ≥3× la referencia de 200 views/día


def test_reference_without_off_topic_pieces_changes_nothing():
    pieces = [piece(i, hours_ago=5 + i * 6, points=10 + i) for i in range(6)]
    pieces.append(piece(99, hours_ago=8, points=200))
    clusters, reps = [list(range(len(pieces)))], [0]
    before = build_opportunities(pieces, clusters, reps, as_of=AS_OF, monitoring_started_at=STARTED)
    after = build_opportunities(
        pieces, clusters, reps, as_of=AS_OF, monitoring_started_at=STARTED, reference=pieces
    )
    assert after == before


def test_empty_pieces_with_reference():
    off_topic = [_reel(i, 5, 10000) for i in range(6)]
    assert outlier_ratios([], AS_OF, reference=off_topic) == {}
    assert (
        build_opportunities(
            [], [], [], as_of=AS_OF, monitoring_started_at=STARTED, reference=off_topic
        )
        == []
    )


def build_with(pieces, stories=None):
    [r] = build_opportunities(
        pieces,
        [list(range(len(pieces)))],
        [0],
        as_of=AS_OF,
        monitoring_started_at=STARTED,
        stories=stories,
    )
    return r


def replicated_topic():
    """3 stories de HN (un medio) + 3 RSS de 3 medios; las RSS 11 y 12 republican la 10."""
    hn = [piece(i, hours_ago=5 + i * 6) for i in range(3)]
    rss = [
        piece(10, hours_ago=20, platform=Platform.RSS, source="Medio 0"),
        piece(11, hours_ago=4, platform=Platform.RSS, source="Medio 1"),
        piece(12, hours_ago=3, platform=Platform.RSS, source="Medio 2"),
    ]
    pieces = hn + rss
    edges = [ReplicaEdge(10, 11, ReplicaBasis.JEV), ReplicaEdge(10, 12, ReplicaBasis.JEV)]
    return pieces, group_stories(pieces, edges)


def test_replicas_do_not_count_as_independent_sources():
    pieces, stories = replicated_topic()
    before, after = build_with(pieces).opportunity, build_with(pieces, stories).opportunity
    # Antes: 4 medios y 2 plataformas → 20·3 + 15·1 = 75; 6 piezas → 24 × (0,5 + 0,5·1) = 24.
    assert (before.source_count, before.cross_source_score, before.evidence_strength) == (
        4,
        75.0,
        24.0,
    )
    # Después: HN y Medio 0 → 20·1 + 15·1 = 35; 4 piezas → 16 × (0,5 + 0,5·2/3) = 13,3.
    assert (after.source_count, after.cross_source_score, after.evidence_strength) == (
        2,
        35.0,
        13.3,
    )
    assert "6 piezas (2 republicaciones) de 2 fuentes independientes" in after.description
    assert "republicaciones" not in before.description


def test_replica_on_another_platform_adds_no_platform():
    hn = [piece(i, hours_ago=5 + i * 6) for i in range(4)]
    rss = [piece(10 + i, hours_ago=3 + i, platform=Platform.RSS, source="Medio") for i in range(2)]
    # La única pieza de YouTube republica la RSS 11: no suma plataforma al cross-source.
    video = piece(20, hours_ago=1, platform=Platform.YOUTUBE, source="Canal")
    pieces = hn + rss + [video]
    stories = group_stories(pieces, [ReplicaEdge(11, 20, ReplicaBasis.JEV)])
    o = build_with(pieces, stories).opportunity
    assert (o.source_count, o.cross_source_score) == (2, 35.0)  # 20·1 + 15·1
    assert o.description.endswith("de 2 fuentes independientes (hackernews, rss).")


def test_copy_on_another_platform_keeps_the_single_platform_note():
    hn = [piece(i, hours_ago=5 + i * 6) for i in range(5)]
    # La única pieza de YouTube republica la HN 0: el tema sigue en una sola plataforma.
    video = piece(20, hours_ago=1, platform=Platform.YOUTUBE, source="Canal")
    pieces = [*hn, video]
    stories = group_stories(pieces, [ReplicaEdge(0, 20, ReplicaBasis.JEV)])
    o = build_with(pieces, stories).opportunity
    assert "Solo aparece en una plataforma (hackernews)." in o.limitations


def test_replicas_do_not_raise_saturation():
    plain = [piece(i, hours_ago=5 + i * 6, platform=Platform.RSS, source=f"A{i}") for i in range(6)]
    copied = [
        piece(10 + i, hours_ago=5 + i * 6, platform=Platform.RSS, source=f"B{i}") for i in range(6)
    ]
    pieces = plain + copied
    edges = [ReplicaEdge(15, 10 + i, ReplicaBasis.SAME_LINK) for i in range(3)]
    plain_r, copied_r = (
        {r.opportunity.id: r for r in build_opportunities(
            pieces,
            [list(range(6)), list(range(6, 12))],
            [0, 6],
            as_of=AS_OF,
            monitoring_started_at=STARTED,
            stories=group_stories(pieces, edges),
        )}[oid]
        for oid in ("opp_5", "opp_15")
    )  # fmt: skip
    # 6 piezas en las dos ventanas cada uno, pero el segundo solo tiene 3 notas.
    assert copied_r.opportunity.saturation_score < plain_r.opportunity.saturation_score


def test_all_replicas_single_story_is_low_confidence():
    pieces = [
        piece(i, hours_ago=5 + i * 6, platform=Platform.RSS, source=f"Medio {i}") for i in range(5)
    ]
    edges = [ReplicaEdge(4, i, ReplicaBasis.SAME_LINK) for i in range(4)]
    o = build_with(pieces, group_stories(pieces, edges)).opportunity
    assert o.source_count == 1
    assert o.lifecycle is Lifecycle.UNKNOWN
    assert o.confidence is Confidence.LOW


def test_single_source_gives_no_pairs():
    pieces = [piece(i, hours_ago=5 + i * 10) for i in range(6)]
    same = np.tile([1.0, 0.0], (len(pieces), 1))  # todas iguales, pero del mismo medio
    edges, candidates = topic_pairs(pieces, [list(range(len(pieces)))], same)
    assert (edges, candidates) == ([], [])


def test_evidence_marks_replicas_and_count():
    pieces, stories = replicated_topic()
    by_url = {str(e.url): e for e in build_with(pieces, stories).evidence}
    original = by_url["https://example.com/10"]
    assert (original.replica_of, original.replica_count) == (None, 2)
    for i in (11, 12):
        copy = by_url[f"https://example.com/{i}"]
        assert str(copy.replica_of) == "https://example.com/10"
        assert copy.replica_count == 0
    assert all(by_url[f"https://example.com/{i}"].replica_of is None for i in range(3))


def test_replicas_go_after_originals_in_evidence():
    hn = [piece(i, hours_ago=10 + i) for i in range(5)]
    hit = piece(5, hours_ago=12, points=200)  # outlier: 20× el p90 de su query
    original = piece(20, hours_ago=40, platform=Platform.RSS, source="Medio")
    pieces = [*hn, hit, original]
    stories = group_stories(pieces, [ReplicaEdge(5, 20, ReplicaBasis.SAME_LINK)])
    r = build_with(pieces, stories)
    assert r.evidence[-1].is_outlier is True
    assert str(r.evidence[-1].replica_of) == "https://example.com/20"
    assert all(e.replica_of is None for e in r.evidence[:-1])
    assert r.pieces[-1].item_id == 5  # lo que recibe el LLM sigue el mismo orden


def test_replica_limitations():
    pieces, stories = replicated_topic()
    notes = build_with(pieces, stories).opportunity.limitations
    assert any(n.startswith("2 piezas son republicaciones") for n in notes)
    assert REPLICAS_UNVERIFIED_NOTE not in notes

    by_rule = group_stories(pieces, [ReplicaEdge(10, 11, ReplicaBasis.SIMILARITY)])
    o = build_with(pieces, by_rule).opportunity
    notes = o.limitations
    assert any(n.startswith("1 pieza es una republicación") for n in notes)
    assert "6 piezas (1 republicación) de 3 fuentes independientes" in o.description
    assert REPLICAS_UNVERIFIED_NOTE in notes


def test_velocity_and_timeline_still_count_pieces():
    pieces, stories = replicated_topic()
    before, after = build_with(pieces), build_with(pieces, stories)
    assert after.opportunity.velocity == before.opportunity.velocity
    assert after.opportunity.acceleration == before.opportunity.acceleration
    assert sum(p.count for p in after.timeline.points) == len(pieces)
