"""Momentum, Opportunity Score, confianza y recomendación (CLAUDE.md §7). Heurísticas ajustables."""

from app.schemas.opportunity import Confidence, GrowthStatus, Lifecycle, Recommendation

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
    """None si falta el audience fit o la accionabilidad: no se rellena con un supuesto."""
    if audience_fit is None or actionability is None:
        return None
    score = (
        W_MOMENTUM * momentum
        + W_FIT * audience_fit
        + W_CROSS * cross_source
        + W_FRESHNESS * (100 - saturation)
        + W_ACTION * actionability
    )
    if source_count < 2:
        score -= PENALTY_SINGLE_SOURCE
    if item_count < SMALL_SAMPLE:
        score -= PENALTY_SMALL_SAMPLE
    return round(max(0.0, min(100.0, score)), 1)


def growth_status(lifecycle: Lifecycle, previous_count: int) -> GrowthStatus:
    """observed = dos ventanas medidas · estimated = solo la actual · preliminary = sin etapa."""
    if lifecycle is Lifecycle.UNKNOWN:
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
    lifecycle: Lifecycle, confidence: Confidence, audience_fit: float | None
) -> Recommendation:
    if lifecycle is Lifecycle.SATURATED:
        return Recommendation.DISCARD
    if lifecycle is Lifecycle.UNKNOWN or confidence is Confidence.LOW:
        return Recommendation.WAIT_FOR_CASE
    if lifecycle is Lifecycle.PEAKING:
        return Recommendation.FIND_ANGLE
    # emerging / accelerating: publicar solo si sabemos que encaja con 30X.
    if audience_fit is not None and audience_fit >= PUBLISH_MIN_FIT:
        return Recommendation.PUBLISH_NOW
    return Recommendation.FIND_ANGLE
