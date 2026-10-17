"""Momentum, Opportunity Score, confianza y recomendación (CLAUDE.md §7). Heurísticas ajustables."""

from app.intelligence.lifecycle import Stage
from app.schemas.opportunity import (
    Confidence,
    GrowthStatus,
    Lifecycle,
    Recommendation,
    ScoreBreakdown,
    ScoreComponent,
    ScoreComponentName,
    ScorePenalty,
    ScorePenaltyName,
)

# Momentum: velocidad (percentil entre temas), aceleración y outliers.
W_VELOCITY = 0.4
W_ACCELERATION = 0.4
W_OUTLIERS = 0.2
ACCELERATION_CAP = 1.0  # +100 % o más = máximo
POINTS_PER_OUTLIER = 25

# Opportunity Score.
W_MOMENTUM = 0.30
W_FIT = 0.25
W_CROSS = 0.20
W_FRESHNESS = 0.15  # 100 − saturación
W_ACTION = 0.10
PENALTY_SINGLE_SOURCE = 10
PENALTY_SMALL_SAMPLE = 10
SMALL_SAMPLE = 8

PUBLISH_MIN_FIT = 60
EVIDENCE_POINTS_PER_ITEM = 4
EVIDENCE_FULL_SOURCES = 3


def momentum_score(velocity_percentile: float, acceleration: float, outlier_count: int) -> float:
    accel = max(-ACCELERATION_CAP, min(acceleration, ACCELERATION_CAP))
    accel_norm = 50 + 50 * accel / ACCELERATION_CAP
    outliers_norm = min(100, POINTS_PER_OUTLIER * outlier_count)
    score = (
        W_VELOCITY * velocity_percentile + W_ACCELERATION * accel_norm + W_OUTLIERS * outliers_norm
    )
    return round(score, 1)


def evidence_strength(item_count: int, source_count: int) -> float:
    """Cuánta evidencia hay, sin sumar métricas entre plataformas."""
    volume = min(100, EVIDENCE_POINTS_PER_ITEM * item_count)
    diversity = 0.5 + 0.5 * min(1.0, source_count / EVIDENCE_FULL_SOURCES)
    return round(volume * diversity, 1)


def score_breakdown(
    *,
    momentum: float,
    audience_fit: float | None,
    cross_source: float,
    saturation: float,
    actionability: float | None,
    source_count: int,
    item_count: int,
) -> ScoreBreakdown | None:
    """None si falta el audience fit o la accionabilidad: no se rellena con un supuesto."""
    if audience_fit is None or actionability is None:
        return None
    components = [
        ScoreComponent(name=ScoreComponentName.MOMENTUM, value=momentum, weight=W_MOMENTUM),
        ScoreComponent(name=ScoreComponentName.AUDIENCE_FIT, value=audience_fit, weight=W_FIT),
        ScoreComponent(name=ScoreComponentName.CROSS_SOURCE, value=cross_source, weight=W_CROSS),
        ScoreComponent(
            name=ScoreComponentName.FRESHNESS, value=100 - saturation, weight=W_FRESHNESS
        ),
        ScoreComponent(name=ScoreComponentName.ACTIONABILITY, value=actionability, weight=W_ACTION),
    ]
    penalties = []
    if source_count < 2:
        penalties.append(
            ScorePenalty(name=ScorePenaltyName.SINGLE_SOURCE, points=PENALTY_SINGLE_SOURCE)
        )
    if item_count < SMALL_SAMPLE:
        penalties.append(
            ScorePenalty(name=ScorePenaltyName.SMALL_SAMPLE, points=PENALTY_SMALL_SAMPLE)
        )
    score = sum(c.value * c.weight for c in components) - sum(p.points for p in penalties)
    total = round(max(0.0, min(100.0, score)), 1)
    return ScoreBreakdown(components=components, penalties=penalties, total=total)


def opportunity_score(
    *,
    momentum: float,
    audience_fit: float | None,
    cross_source: float,
    saturation: float,
    actionability: float | None,
    source_count: int,
    item_count: int,
) -> float | None:
    breakdown = score_breakdown(
        momentum=momentum,
        audience_fit=audience_fit,
        cross_source=cross_source,
        saturation=saturation,
        actionability=actionability,
        source_count=source_count,
        item_count=item_count,
    )
    return None if breakdown is None else breakdown.total


def growth_status(insufficient: bool, previous_count: int) -> GrowthStatus:
    """Según los datos, no según la etapa: preliminary = datos insuficientes ·
    estimated = solo la ventana actual · observed = dos ventanas medidas.
    """
    if insufficient:
        return GrowthStatus.PRELIMINARY
    if previous_count == 0:
        return GrowthStatus.ESTIMATED
    return GrowthStatus.OBSERVED


def confidence(growth: GrowthStatus, source_count: int, item_count: int) -> Confidence:
    if growth is GrowthStatus.PRELIMINARY or source_count < 2:
        return Confidence.LOW
    if growth is GrowthStatus.OBSERVED and source_count >= 3 and item_count >= 10:
        return Confidence.HIGH
    return Confidence.MEDIUM


def recommendation(
    stage: Stage, confidence: Confidence, audience_fit: float | None
) -> Recommendation:
    if stage.lifecycle is Lifecycle.SATURATED:
        return Recommendation.DISCARD
    if stage.insufficient or confidence is Confidence.LOW:
        return Recommendation.WAIT_FOR_CASE
    # peaking, o unknown porque ninguna regla se cumple: hay datos, falta ángulo.
    if stage.lifecycle in (Lifecycle.PEAKING, Lifecycle.UNKNOWN):
        return Recommendation.FIND_ANGLE
    # emerging / accelerating: publicar solo si sabemos que encaja con 30X.
    if audience_fit is not None and audience_fit >= PUBLISH_MIN_FIT:
        return Recommendation.PUBLISH_NOW
    return Recommendation.FIND_ANGLE
