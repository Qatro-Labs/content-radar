"""Funciones puras del motor de inteligencia. Sin DB."""

from datetime import UTC, datetime, timedelta

import pytest

from app.intelligence.audience_mix import audience_mix, latam_gap
from app.intelligence.cross_source import cross_source_score, outlet_key, saturation_scores
from app.intelligence.lifecycle import classify
from app.intelligence.outliers import age_adjusted, is_outlier, outlier_ratio
from app.intelligence.ranking import (
    confidence,
    evidence_strength,
    growth_status,
    momentum_score,
    opportunity_score,
    recommendation,
)
from app.intelligence.velocity import WindowCounts, piece_rate, topic_velocity, window_counts
from app.schemas.opportunity import Confidence, GrowthStatus, Lifecycle, Recommendation
from app.schemas.signal import Segment

NOW = datetime(2026, 10, 17, 12, tzinfo=UTC)


# --- velocity ---


def test_window_counts_splits_current_and_previous():
    published = [NOW - timedelta(hours=h) for h in (1, 30, 71, 73, 140, 200)]
    published.append(NOW + timedelta(hours=1))  # futuro: no cuenta
    assert window_counts(published, NOW) == WindowCounts(current=3, previous=2)


def test_window_counts_empty():
    assert window_counts([], NOW) == WindowCounts(0, 0)


def test_acceleration_is_adjusted_by_corpus_volume():
    # El tema pasa de 5 a 10 piezas, pero el corpus también se duplica: no acelera.
    flat = topic_velocity(WindowCounts(10, 5), corpus=WindowCounts(200, 100))
    assert flat.acceleration == 0
    assert flat.velocity == pytest.approx(3.33)
    # Con el corpus estable, el mismo tema acelera +100 %.
    assert topic_velocity(WindowCounts(10, 5), corpus=WindowCounts(100, 100)).acceleration == 1.0


def test_acceleration_with_empty_previous_window():
    # (v − 0) / max(0, 1): no divide por cero.
    assert topic_velocity(WindowCounts(4, 0), corpus=WindowCounts(50, 0)).acceleration == 4.0
    assert topic_velocity(WindowCounts(0, 0), corpus=WindowCounts(0, 0)).acceleration == 0


def test_piece_rate_needs_two_snapshots():
    assert piece_rate([]) is None
    assert piece_rate([(NOW, 100)]) is None
    assert piece_rate([(NOW, 100), (NOW + timedelta(hours=2), None)]) is None
    assert piece_rate([(NOW + timedelta(hours=2), 160), (NOW, 100)]) == 30.0


# --- outliers ---


def test_outlier_ratio_against_median():
    assert outlier_ratio(30, [10, 10, 10, 20, 5]) == 3.0
    assert is_outlier(3.0) is True
    assert is_outlier(2.9) is False


def test_outlier_ratio_with_quantile_reference():
    # p90 de [1..10] = 9.1
    assert outlier_ratio(91, list(range(1, 11)), quantile=0.9) == 10.0


def test_outlier_ratio_without_reference():
    assert outlier_ratio(30, [10, 10]) is None
    assert outlier_ratio(30, [0] * 5) is None
    assert is_outlier(None) is None


def test_age_adjusted_has_one_day_floor():
    assert age_adjusted(1000, NOW - timedelta(hours=2), NOW) == 1000
    assert age_adjusted(1000, NOW - timedelta(days=4), NOW) == 250


# --- lifecycle ---


def stage(acc=0.0, sat=50.0, sources=4, items=20):
    return classify(acceleration=acc, saturation=sat, source_count=sources, item_count=items)


def test_unknown_goes_first():
    # Cumpliría `emerging`, pero con una sola fuente no hay datos suficientes.
    assert stage(acc=1.0, sat=10, sources=1).insufficient
    assert stage(acc=1.0, sat=10, sources=2, items=4).lifecycle is Lifecycle.UNKNOWN
    no_rule = stage(acc=0.3, sat=50)
    assert no_rule.lifecycle is Lifecycle.UNKNOWN and not no_rule.insufficient


@pytest.mark.parametrize(
    ("acc", "sat", "sources", "expected"),
    [
        (-0.3, 80, 6, Lifecycle.SATURATED),
        (0.1, 65, 6, Lifecycle.PEAKING),
        (0.6, 50, 3, Lifecycle.ACCELERATING),
        (0.6, 30, 2, Lifecycle.EMERGING),
        (0.3, 50, 5, Lifecycle.UNKNOWN),  # ninguna regla
    ],
)
def test_lifecycle_rules(acc, sat, sources, expected):
    result = stage(acc=acc, sat=sat, sources=sources)
    assert result.lifecycle is expected
    assert result.reason


# --- audience mix ---


def test_audience_mix_weighted_and_sums_to_one():
    mix = audience_mix([(Segment.TECH, 1.0), (Segment.TECH, 1.0), (Segment.BUSINESS, 2.0)])
    assert mix is not None
    assert (mix.tech, mix.business, mix.latam_es) == (0.5, 0.5, 0.0)


def test_audience_mix_empty():
    assert audience_mix([]) is None
    assert latam_gap(None) is None


def test_latam_gap():
    gap = audience_mix([(Segment.BUSINESS, 1), (Segment.TECH, 3)])
    covered = audience_mix([(Segment.LATAM_ES, 1), (Segment.TECH, 1)])
    tech_only = audience_mix([(Segment.TECH, 1)])
    assert latam_gap(gap) is True
    assert latam_gap(covered) is False
    assert latam_gap(tech_only) is None


# --- cross source / saturation ---


def test_hn_queries_count_as_one_outlet():
    assert outlet_key("hackernews", "HN · LLM") == outlet_key("hackernews", "HN · OpenAI")
    assert outlet_key("rss", "A") != outlet_key("rss", "B")


def test_cross_source_score():
    assert cross_source_score(set(), set()) == 0
    assert cross_source_score({"hackernews"}, {"hackernews"}) == 0
    assert cross_source_score({"hackernews", "rss:A", "rss:B"}, {"hackernews", "rss"}) == 55
    assert cross_source_score({f"rss:{i}" for i in range(10)}, {"rss"}) == 100


def test_saturation_percentiles():
    assert saturation_scores([]) == []
    assert saturation_scores([7]) == [50.0]
    assert saturation_scores([1, 5, 10]) == [0.0, 50.0, 100.0]


# --- ranking ---


def test_momentum_bounds():
    assert momentum_score(0, -5, 0) == 0
    assert momentum_score(100, 5, 10) == 100


def test_opportunity_score_is_none_without_fit():
    kwargs = dict(momentum=80, cross_source=60, saturation=30, source_count=4, item_count=20)
    assert opportunity_score(audience_fit=None, actionability=70, **kwargs) is None
    assert opportunity_score(audience_fit=80, actionability=None, **kwargs) is None
    assert opportunity_score(audience_fit=80, actionability=70, **kwargs) == 73.5


def test_opportunity_score_penalties_and_floor():
    score = opportunity_score(
        momentum=0, audience_fit=0, cross_source=0, saturation=100, actionability=0,
        source_count=1, item_count=3,
    )  # fmt: skip
    assert score == 0


def test_evidence_strength():
    assert evidence_strength(0, 0) == 0
    assert evidence_strength(25, 3) == 100
    assert evidence_strength(25, 1) == pytest.approx(66.7)


def test_growth_confidence_and_recommendation():
    assert growth_status(True, 5) is GrowthStatus.PRELIMINARY
    assert growth_status(False, 0) is GrowthStatus.ESTIMATED
    assert growth_status(False, 3) is GrowthStatus.OBSERVED

    assert confidence(GrowthStatus.OBSERVED, 3, 10) is Confidence.HIGH
    assert confidence(GrowthStatus.ESTIMATED, 3, 10) is Confidence.MEDIUM
    assert confidence(GrowthStatus.OBSERVED, 1, 50) is Confidence.LOW

    saturated, accelerating = stage(acc=-0.3, sat=80), stage(acc=0.6, sources=3)
    no_rule, no_data = stage(acc=0.3, sat=50), stage(sources=1)
    assert recommendation(saturated, Confidence.HIGH, 90) is Recommendation.DISCARD
    assert recommendation(accelerating, Confidence.LOW, 90) is Recommendation.WAIT_FOR_CASE
    assert recommendation(accelerating, Confidence.HIGH, 70) is Recommendation.PUBLISH_NOW
    # Sin audience fit no se recomienda publicar.
    assert recommendation(accelerating, Confidence.HIGH, None) is Recommendation.FIND_ANGLE
    # unknown sin regla tiene datos: buscar ángulo. Unknown por falta de datos: esperar.
    assert recommendation(no_rule, Confidence.MEDIUM, None) is Recommendation.FIND_ANGLE
    assert recommendation(no_data, Confidence.MEDIUM, None) is Recommendation.WAIT_FOR_CASE
