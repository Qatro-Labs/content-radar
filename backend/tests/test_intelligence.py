"""Funciones puras del motor de inteligencia. Sin DB."""

from datetime import UTC, datetime, timedelta

import pytest

from app.intelligence.audience_mix import (
    audience_mix,
    has_business_conversation,
    latam_gap,
    latam_share,
)
from app.intelligence.cross_source import (
    cross_source_score,
    outlet_key,
    percentile_scores,
    saturation_score,
)
from app.intelligence.lifecycle import ACCELERATION_MAX_P, classify
from app.intelligence.outliers import (
    MEDIAN,
    age_adjusted,
    is_outlier,
    outlier_ratio,
    reference_quantile,
)
from app.intelligence.ranking import (
    confidence,
    evidence_strength,
    growth_status,
    momentum_score,
    opportunity_score,
    recommend,
    score_breakdown,
)
from app.intelligence.velocity import (
    WindowCounts,
    acceleration_p_value,
    piece_rate,
    topic_velocity,
    window_counts,
)
from app.schemas.opportunity import (
    Confidence,
    GrowthStatus,
    Lifecycle,
    Recommendation,
    ScoreComponentName,
    ScorePenaltyName,
)
from app.schemas.signal import Platform, Segment

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


def test_log_ratio_separates_small_from_large_jumps():
    # Con el cambio relativo, 2 frente a 1 y 70 frente a 5 eran "+100 % o más" por igual.
    small = topic_velocity(WindowCounts(2, 1), corpus=WindowCounts(100, 100))
    large = topic_velocity(WindowCounts(70, 5), corpus=WindowCounts(100, 100))
    assert small.acceleration == 1.0 and large.acceleration == 13.0
    assert small.log_ratio == pytest.approx(0.585, abs=0.001)  # log2(3 / 2)
    assert large.log_ratio == pytest.approx(3.564, abs=0.001)  # log2(71 / 6)
    assert topic_velocity(WindowCounts(0, 0), corpus=WindowCounts(0, 0)).log_ratio == 0


def test_acceleration_p_value_is_exact_binomial_tail():
    # Corpus estable (p0 = 0,5): 5 frente a 0 sale por azar con probabilidad 0,5^5.
    assert acceleration_p_value(WindowCounts(5, 0), WindowCounts(100, 100)) == pytest.approx(
        0.031, abs=0.001
    )
    # 2 frente a 1 no demuestra nada: P(X ≥ 2 | n = 3) = 0,5.
    assert acceleration_p_value(WindowCounts(2, 1), WindowCounts(100, 100)) == 0.5
    # Un tema que baja nunca es significativo.
    assert acceleration_p_value(WindowCounts(1, 6), WindowCounts(100, 100)) > 0.9


def test_acceleration_p_value_uses_the_corpus_share():
    # Si el corpus se duplica en la ventana actual, 8 frente a 4 es lo esperado: no acelera.
    assert acceleration_p_value(WindowCounts(8, 4), WindowCounts(200, 100)) > 0.5
    assert acceleration_p_value(WindowCounts(8, 4), WindowCounts(100, 100)) < 0.2


def test_acceleration_p_value_handles_large_topics():
    # math.comb(2000, 1000) no cabe en un float: el cálculo va en logaritmos.
    assert acceleration_p_value(WindowCounts(1000, 1000), WindowCounts(5000, 5000)) > 0.4
    assert acceleration_p_value(WindowCounts(1500, 500), WindowCounts(5000, 5000)) < 0.001


def test_acceleration_p_value_without_data_is_one():
    assert acceleration_p_value(WindowCounts(0, 0), WindowCounts(100, 100)) == 1.0
    # Sin corpus en la ventana anterior (monitoreo recién empezado) no se puede demostrar.
    assert acceleration_p_value(WindowCounts(5, 0), WindowCounts(50, 0)) == 1.0


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


@pytest.mark.parametrize(
    ("platform", "quantile"),
    [
        (Platform.HACKERNEWS, 0.9),
        (Platform.TIKTOK, 0.9),
        (Platform.REDDIT, MEDIAN),
        (Platform.YOUTUBE, MEDIAN),
        (Platform.INSTAGRAM, MEDIAN),
    ],
)
def test_reference_quantile_per_platform(platform, quantile):
    assert reference_quantile(platform) == quantile


def test_outlier_ratio_without_reference():
    assert outlier_ratio(30, [10, 10]) is None
    assert outlier_ratio(30, [0] * 5) is None
    assert is_outlier(None) is None


def test_age_adjusted_has_one_day_floor():
    assert age_adjusted(1000, NOW - timedelta(hours=2), NOW) == 1000
    assert age_adjusted(1000, NOW - timedelta(days=4), NOW) == 250


# --- lifecycle ---


def stage(acc=0.0, sat=50.0, sources=4, items=20, p=0.01):
    return classify(
        acceleration=acc, p_value=p, saturation=sat, source_count=sources, item_count=items
    )


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


def test_accelerating_needs_a_significant_acceleration():
    # Cumple accelerating, pero la subida puede ser azar: no se afirma la etapa.
    result = stage(acc=0.6, sat=50, sources=3, p=0.27)
    assert result.lifecycle is Lifecycle.UNKNOWN
    assert not result.insufficient
    assert result.reason.startswith("Aceleración +0.60 sin demostrar: p = 0.27")
    assert stage(acc=0.6, sat=50, sources=3, p=ACCELERATION_MAX_P).lifecycle is (
        Lifecycle.ACCELERATING
    )


def test_p_value_text_never_reads_as_zero_or_ties_the_threshold():
    assert "(p < 0.01)" in stage(acc=0.6, sat=50, sources=3, p=0.004).reason
    assert "p = 0.27 > 0.10," in stage(acc=0.6, sat=50, sources=3, p=0.27).reason
    assert "p = 0.103 > 0.10," in stage(acc=0.6, sat=50, sources=3, p=0.103).reason


def test_emerging_warns_instead_of_gating():
    # Temprano por definición: queda emerging, pero la razón avisa de que puede ser azar.
    unproven = stage(acc=0.6, sat=30, sources=2, p=0.27)
    assert unproven.lifecycle is Lifecycle.EMERGING
    assert "(p = 0.27)" in unproven.reason and "puede ser azar" in unproven.reason
    proven = stage(acc=0.6, sat=30, sources=2, p=0.05)
    assert proven.lifecycle is Lifecycle.EMERGING
    assert "azar" not in proven.reason


def test_unproven_acceleration_falls_back_to_emerging():
    # 3 fuentes y saturación baja: falla accelerating por el p-valor y cumple emerging.
    assert stage(acc=0.6, sat=30, sources=3, p=0.27).lifecycle is Lifecycle.EMERGING


def test_significance_does_not_gate_saturated_or_peaking():
    assert stage(acc=-0.3, sat=80, sources=6, p=1.0).lifecycle is Lifecycle.SATURATED
    assert stage(acc=0.1, sat=65, sources=6, p=1.0).lifecycle is Lifecycle.PEAKING


# --- audience mix ---


def test_audience_mix_weighted_and_sums_to_one():
    mix = audience_mix([(Segment.TECH, 1.0), (Segment.TECH, 1.0), (Segment.BUSINESS, 2.0)])
    assert mix is not None
    assert (mix.tech, mix.business, mix.latam_es) == (0.5, 0.5, 0.0)


def test_audience_mix_empty():
    assert audience_mix([]) is None
    assert latam_share([]) is None
    assert latam_gap(True, None) is None


def test_latam_share_counts_only_latin_american_regions():
    # España (es) y global no cuentan; mx y latam sí: 1 + 3 de un peso total de 9.
    share = latam_share([("es", 2), ("mx", 1), ("global", 3), (None, 0), ("latam", 3)])
    assert share == pytest.approx(4 / 9, abs=0.001)


def test_latam_gap():
    assert latam_gap(True, 0.0) is True
    assert latam_gap(True, 0.5) is False  # ya cubierto en la región
    assert latam_gap(False, 0.5) is False
    assert latam_gap(False, 0.0) is None  # sin conversación de negocio no se decide


def test_business_conversation_comes_from_jev_when_it_judged():
    tech_sources = audience_mix([(Segment.TECH, 1)])
    business_sources = audience_mix([(Segment.BUSINESS, 1)])
    assert tech_sources is not None and business_sources is not None
    # Fuentes tech, pero 3 de 5 piezas tratan del uso en organizaciones: hay negocio.
    assert has_business_conversation(tech_sources, [True, True, True, False, False])
    # Fuentes de negocio, pero Jev no ve uso en organizaciones en ninguna pieza: no lo hay.
    assert not has_business_conversation(business_sources, [False, False, None])
    # Una sola pieza no es conversación, aunque la proporción pase el umbral.
    assert not has_business_conversation(tech_sources, [True, False, None])


def test_business_conversation_falls_back_to_the_source_segment():
    # Sin juicios de Jev (sin clave o todo incierto), decide el segmento de la fuente.
    business_sources = audience_mix([(Segment.BUSINESS, 1), (Segment.TECH, 3)])
    tech_sources = audience_mix([(Segment.TECH, 1)])
    assert business_sources is not None and tech_sources is not None
    assert has_business_conversation(business_sources, [None, None])
    assert not has_business_conversation(tech_sources, [])


def test_spanish_coverage_does_not_close_the_latam_gap():
    # Mucho latam_es, pero todo de España: el gap sigue abierto.
    share = latam_share([("global", 1), ("es", 1)])
    assert latam_gap(True, share) is True


# --- cross source / saturation ---


def test_search_queries_count_as_one_outlet():
    assert outlet_key("hackernews", "HN · LLM") == outlet_key("hackernews", "HN · OpenAI")
    assert outlet_key("tiktok", "TikTok · AI agents") == outlet_key("tiktok", "TikTok · agentes")
    assert outlet_key("rss", "A") != outlet_key("rss", "B")
    assert outlet_key("reddit", "r/OpenAI") != outlet_key("reddit", "r/ClaudeAI")


def test_cross_source_score():
    assert cross_source_score(set(), set()) == 0
    assert cross_source_score({"hackernews"}, {"hackernews"}) == 0
    assert cross_source_score({"hackernews", "rss:A", "rss:B"}, {"hackernews", "rss"}) == 55
    assert cross_source_score({f"rss:{i}" for i in range(10)}, {"rss"}) == 100


def test_percentiles():
    assert percentile_scores([]) == []
    assert percentile_scores([7]) == [50.0]
    assert percentile_scores([1, 5, 10]) == [0.0, 50.0, 100.0]


def test_saturation_is_the_share_of_the_corpus():
    # 100 = el 2 % de las notas; no depende de cuántos temas haya.
    assert saturation_score(20, 1000) == 100.0
    assert saturation_score(15, 1000) == 75.0
    assert saturation_score(5, 1000) == 25.0
    assert saturation_score(40, 1000) == 100.0
    assert saturation_score(3, 0) == 0.0


def test_declining_topic_reason():
    stage = classify(acceleration=-0.52, p_value=1.0, saturation=22, source_count=5, item_count=10)
    assert stage.lifecycle is Lifecycle.UNKNOWN
    assert stage.insufficient is False
    assert stage.reason.startswith("En descenso: aceleración -52%")
    rising = classify(acceleration=0.43, p_value=0.2, saturation=82, source_count=5, item_count=10)
    assert rising.reason.startswith("Ninguna regla se cumple")


# --- ranking ---


def test_momentum_bounds():
    assert momentum_score(0, -5, 0) == 0
    assert momentum_score(100, 5, 10) == 100


def test_momentum_grows_with_the_log_ratio_beyond_doubling():
    # Antes, todo lo que pasaba de +100 % puntuaba igual.
    doubled = momentum_score(50, 1.0, 0)
    eightfold = momentum_score(50, 3.0, 0)
    assert doubled < eightfold
    assert momentum_score(50, 0.0, 0) == 40.0  # sin cambio: aceleración neutra (50)


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


def test_score_breakdown_worked_example():
    b = score_breakdown(
        momentum=80, audience_fit=60, cross_source=50, saturation=30, actionability=40,
        source_count=1, item_count=5,
    )  # fmt: skip
    assert b is not None
    assert [(c.name, c.value, c.weight) for c in b.components] == [
        (ScoreComponentName.MOMENTUM, 80, 0.30),
        (ScoreComponentName.AUDIENCE_FIT, 60, 0.25),
        (ScoreComponentName.CROSS_SOURCE, 50, 0.20),
        (ScoreComponentName.FRESHNESS, 70, 0.15),
        (ScoreComponentName.ACTIONABILITY, 40, 0.10),
    ]
    assert [(p.name, p.points) for p in b.penalties] == [
        (ScorePenaltyName.SINGLE_SOURCE, 10),
        (ScorePenaltyName.SMALL_SAMPLE, 10),
    ]
    assert b.total == 43.5  # 24 + 15 + 10 + 10.5 + 4 − 20


def test_score_breakdown_is_none_without_fit():
    kwargs = dict(momentum=80, cross_source=60, saturation=30, source_count=4, item_count=20)
    assert score_breakdown(audience_fit=None, actionability=70, **kwargs) is None
    assert score_breakdown(audience_fit=80, actionability=None, **kwargs) is None


def test_evidence_strength():
    assert evidence_strength(0, 0) == 0
    assert evidence_strength(25, 3) == 100
    assert evidence_strength(25, 1) == pytest.approx(66.7)


def test_growth_and_confidence():
    assert growth_status(True, 5) is GrowthStatus.PRELIMINARY
    assert growth_status(False, 0) is GrowthStatus.ESTIMATED
    assert growth_status(False, 3) is GrowthStatus.OBSERVED

    assert confidence(GrowthStatus.OBSERVED, 3, 10) is Confidence.HIGH
    assert confidence(GrowthStatus.ESTIMATED, 3, 10) is Confidence.MEDIUM
    assert confidence(GrowthStatus.OBSERVED, 1, 50) is Confidence.LOW


def advise(st, conf=Confidence.HIGH, *, fit=None, org=None, gap=None) -> Recommendation:
    return recommend(st, conf, audience_fit=fit, org_application=org, latam_gap=gap).recommendation


SATURATED, ACCELERATING = stage(acc=-0.3, sat=80), stage(acc=0.6, sources=3)
NO_RULE, NO_DATA = stage(acc=0.3, sat=50), stage(sources=1)


@pytest.mark.parametrize(
    ("st", "conf", "fit", "org", "gap", "expected"),
    [
        (SATURATED, Confidence.HIGH, 90, 5, None, Recommendation.DISCARD),
        (ACCELERATING, Confidence.LOW, 90, 5, None, Recommendation.WAIT_FOR_CASE),
        (NO_DATA, Confidence.MEDIUM, None, None, None, Recommendation.WAIT_FOR_CASE),
        (ACCELERATING, Confidence.HIGH, 90, 1, None, Recommendation.WAIT_FOR_CASE),
        (NO_RULE, Confidence.MEDIUM, 90, 0, None, Recommendation.WAIT_FOR_CASE),
        (NO_RULE, Confidence.MEDIUM, 90, 3, None, Recommendation.FIND_ANGLE),
        (ACCELERATING, Confidence.HIGH, 90, 3, False, Recommendation.FIND_ANGLE),
        (ACCELERATING, Confidence.HIGH, None, None, None, Recommendation.FIND_ANGLE),
        (ACCELERATING, Confidence.HIGH, 59, 3, None, Recommendation.FIND_ANGLE),
        (ACCELERATING, Confidence.HIGH, 60, 2, True, Recommendation.PUBLISH_NOW),
    ],
    ids=[
        "saturated-discards",
        "low-confidence-waits",
        "insufficient-data-waits",
        "no-real-case-waits",
        "no-real-case-waits-before-angle",
        "unknown-with-data-finds-angle",
        "latam-covered-finds-angle",
        "no-fit-never-publishes",
        "fit-below-60-finds-angle",
        "growing-with-fit-and-case-publishes",
    ],
)
def test_recommendation_takes_the_first_rule_that_holds(st, conf, fit, org, gap, expected):
    assert advise(st, conf, fit=fit, org=org, gap=gap) is expected


def test_recommendation_says_which_rule_held():
    advice = recommend(
        ACCELERATING, Confidence.HIGH, audience_fit=90, org_application=1, latam_gap=None
    )
    assert "ninguna organización aplicándolo" in advice.reason
