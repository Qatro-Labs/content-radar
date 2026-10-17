"""De piezas agrupadas a oportunidades del contrato. Determinista: sin DB ni LLM.

Sale sin audience fit: lo añade después `intelligence.audience_fit` con los niveles del LLM.
`topic` es el título de la pieza más representativa y los textos (`description`,
`why_it_matters`, `limitations`) son plantillas con los datos medidos.
"""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TypedDict

from app.intelligence import outliers as out
from app.intelligence.audience_mix import audience_mix, latam_gap, latam_share
from app.intelligence.cross_source import cross_source_score, outlet_key, saturation_scores
from app.intelligence.lifecycle import Stage, classify
from app.intelligence.ranking import (
    confidence,
    evidence_strength,
    growth_status,
    momentum_score,
    recommend,
    score_breakdown,
)
from app.intelligence.velocity import (
    WINDOW,
    TopicVelocity,
    WindowCounts,
    piece_rate,
    topic_velocity,
    window_counts,
)
from app.schemas.opportunity import (
    AudienceMix,
    Collection,
    Confidence,
    Evidence,
    GrowthStatus,
    Lifecycle,
    Opportunity,
    OpportunityTimeline,
    Rate,
    Recommendation,
    ScoreBreakdown,
    TimelinePoint,
    TimelineWindow,
)
from app.schemas.signal import Metrics, Platform, Segment, SourceKind

# Métrica que mide el rendimiento de cada plataforma. RSS no expone métricas. El score de Reddit
# se guarda en `points`, como el de HN.
PERFORMANCE_METRIC = {
    Platform.YOUTUBE: "views",
    Platform.TIKTOK: "views",
    Platform.INSTAGRAM: "views",
    Platform.HACKERNEWS: "points",
    Platform.REDDIT: "points",
}
# Plataformas cuyas views se acumulan con los días: su rendimiento se ajusta por edad.
CUMULATIVE_VIEWS = {Platform.YOUTUBE, Platform.TIKTOK, Platform.INSTAGRAM}
MIN_RECENT_ITEMS = 3  # piezas en las dos últimas ventanas para considerar el tema activo
MIX_WEIGHT_MIN, MIX_WEIGHT_MAX = 0.5, 3.0
MAX_EVIDENCE = 25
LLM_PENDING_NOTE = "Audience fit y análisis editorial pendientes (sin LLM todavía)."
BROAD_TOPIC_NOTE = (
    "Tema amplio: las piezas comparten poco más que el término de búsqueda; tómalo como "
    "categoría, no como historia concreta."
)


@dataclass
class Piece:
    item_id: int
    url: str
    title: str
    description: str | None
    platform: Platform
    source_id: int
    source_name: str
    segment: Segment
    language: str | None
    published_at: datetime
    observed_at: datetime  # última observación
    metrics: Metrics  # último snapshot (vacío si la fuente no expone métricas)
    source_kind: SourceKind
    snapshots: list[tuple[datetime, Metrics]] = field(default_factory=list)
    region: str | None = None  # de la fuente; decide si cuenta para el LATAM Gap


@dataclass
class _ActiveTopic:
    group: list[Piece]
    rep: Piece
    counts: WindowCounts
    velocity: TopicVelocity
    broad: bool


@dataclass
class TopicResult:
    opportunity: Opportunity
    evidence: list[Evidence]
    timeline: OpportunityTimeline
    # Para añadir el audience fit después sin reconstruir la etapa ni el grupo desde el contrato.
    stage: Stage
    pieces: list[Piece]


def _performance(p: Piece) -> float | None:
    metric = PERFORMANCE_METRIC.get(p.platform)
    value = getattr(p.metrics, metric) if metric else None
    if value is None:
        return None
    if p.platform in CUMULATIVE_VIEWS:
        return out.age_adjusted(value, p.published_at, p.observed_at)
    return float(value)


def _old_enough_for_reference(p: Piece, as_of: datetime) -> bool:
    return as_of - p.published_at >= out.MIN_REFERENCE_AGE.get(p.platform, timedelta(0))


def outlier_ratios(pieces: Sequence[Piece], as_of: datetime) -> dict[int, float | None]:
    """Ratio de cada pieza frente a las otras de su fuente (canal o query) con edad suficiente:
    mediana, o p90 en HN.
    """
    perf = {p.item_id: _performance(p) for p in pieces}
    by_source: dict[int, list[tuple[int, float]]] = defaultdict(list)
    for p in pieces:
        value = perf[p.item_id]
        if value is not None and _old_enough_for_reference(p, as_of):
            by_source[p.source_id].append((p.item_id, value))
    ratios: dict[int, float | None] = {}
    for p in pieces:
        value = perf[p.item_id]
        if value is None:
            ratios[p.item_id] = None
            continue
        reference = [v for item_id, v in by_source[p.source_id] if item_id != p.item_id]
        quantile = out.HN_REFERENCE_QUANTILE if p.platform is Platform.HACKERNEWS else out.MEDIAN
        ratios[p.item_id] = out.outlier_ratio(value, reference, quantile)
    return ratios


def _rate(p: Piece) -> Rate | None:
    metric = PERFORMANCE_METRIC.get(p.platform)
    if metric is None:
        return None
    value = piece_rate([(t, getattr(m, metric)) for t, m in p.snapshots])
    return None if value is None else Rate(value=value, unit=f"{metric}/h")


def _collection(kind: SourceKind) -> Collection:
    return Collection.MANUAL if kind is SourceKind.MANUAL else Collection.AUTOMATIC


def _evidence(p: Piece, ratio: float | None) -> Evidence:
    return Evidence(
        url=p.url,  # type: ignore[arg-type]
        source=p.source_name,
        platform=p.platform,
        segment=p.segment,
        title=p.title,
        published_at=p.published_at,
        observed_at=p.observed_at,
        language=p.language,
        metrics=p.metrics,
        velocity=_rate(p),
        outlier_ratio=ratio,
        is_outlier=out.is_outlier(ratio),
        collection=_collection(p.source_kind),
    )


def _timeline(oid: str, published: Sequence[datetime], as_of: datetime) -> OpportunityTimeline:
    days = int(WINDOW / timedelta(days=1))
    points = []
    for k in range(2 * days - 1, -1, -1):
        end = as_of - timedelta(days=k)
        count = sum(1 for t in published if end - timedelta(days=1) < t <= end)
        window = TimelineWindow.CURRENT if k < days else TimelineWindow.PREVIOUS
        points.append(TimelinePoint(date=end.date(), count=count, window=window))
    return OpportunityTimeline(opportunity_id=oid, window_days=days, points=points)


def _limitations(
    growth: GrowthStatus,
    *,
    platforms: set[Platform],
    ratios: list[float | None],
    since: datetime,
    broad: bool,
) -> list[str]:
    notes = [
        f"El monitoreo comenzó el {since:%d/%m}: los periodos anteriores no son históricos.",
        LLM_PENDING_NOTE,
    ]
    if growth is not GrowthStatus.OBSERVED:
        notes.append("Crecimiento no observado en dos ventanas: es estimado o preliminar.")
    if len(platforms) == 1:
        notes.append(f"Solo aparece en una plataforma ({next(iter(platforms)).value}).")
    if all(r is None for r in ratios):
        notes.append("Ninguna pieza tiene referencia para calcular outliers.")
    if broad:
        notes.append(BROAD_TOPIC_NOTE)
    return notes


def _stable_id(group: Sequence[Piece]) -> str:
    # Anclado a la pieza más antigua: el frontend y el MCP guardan el id entre ejecuciones, y
    # sigue igual mientras esa pieza esté en el cluster y dentro del LOOKBACK.
    anchor = min(group, key=lambda p: (p.published_at, p.item_id))
    return f"opp_{anchor.item_id}"


def _active_topics(
    pieces: Sequence[Piece],
    clusters: Sequence[Sequence[int]],
    representatives: Sequence[int],
    broad: Sequence[bool],
    as_of: datetime,
) -> list[_ActiveTopic]:
    corpus = window_counts([p.published_at for p in pieces], as_of)
    topics = []
    for members, rep, is_broad in zip(clusters, representatives, broad, strict=True):
        group = [pieces[i] for i in members]
        counts = window_counts([p.published_at for p in group], as_of)
        if counts.current + counts.previous < MIN_RECENT_ITEMS:
            continue
        velocity = topic_velocity(counts, corpus)
        topics.append(_ActiveTopic(group, pieces[rep], counts, velocity, is_broad))
    return topics


def _audience(
    group: Sequence[Piece], ratios: Sequence[float | None]
) -> tuple[AudienceMix, bool | None]:
    weights = [min(max(r or 1.0, MIX_WEIGHT_MIN), MIX_WEIGHT_MAX) for r in ratios]
    mix = audience_mix([(p.segment, w) for p, w in zip(group, weights, strict=True)])
    latam = latam_share([(p.region, w) for p, w in zip(group, weights, strict=True)])
    assert mix is not None  # el grupo nunca está vacío
    return mix, latam_gap(mix, latam)


def _why_it_matters(topic: _ActiveTopic, source_count: int, outlier_count: int) -> str:
    return (
        f"Pendiente de análisis editorial. Señales medidas: {topic.counts.current} piezas en "
        f"los últimos 3 días frente a {topic.counts.previous} en los 3 anteriores "
        f"(aceleración ajustada por volumen {topic.velocity.acceleration:+.0%}), "
        f"{source_count} fuentes independientes y {outlier_count} outliers."
    )


@dataclass
class _TopicScores:
    stage: Stage
    growth: GrowthStatus
    confidence: Confidence
    momentum: float
    cross_source: float
    breakdown: ScoreBreakdown | None


def _score_topic(
    topic: _ActiveTopic,
    *,
    outlets: set[str],
    platforms: set[Platform],
    outlier_count: int,
    saturation: float,
    velocity_percentile: float,
) -> _TopicScores:
    acceleration, item_count = topic.velocity.acceleration, len(topic.group)
    source_count = len(outlets)
    stage = classify(
        acceleration=acceleration,
        saturation=saturation,
        source_count=source_count,
        item_count=item_count,
    )
    growth = growth_status(stage.insufficient, topic.counts.previous)
    momentum = momentum_score(velocity_percentile, acceleration, outlier_count)
    cross = cross_source_score(outlets, {p.value for p in platforms})
    breakdown = score_breakdown(
        momentum=momentum,
        audience_fit=None,
        cross_source=cross,
        saturation=saturation,
        actionability=None,
        source_count=source_count,
        item_count=item_count,
    )
    conf = confidence(growth, source_count, item_count)
    return _TopicScores(stage, growth, conf, momentum, cross, breakdown)


@dataclass
class _TopicFacts:
    outlets: set[str]
    platforms: set[Platform]
    ratios: list[float | None]
    outlier_count: int
    top_outlier_ratio: float | None


def _topic_facts(group: Sequence[Piece], ratios: list[float | None]) -> _TopicFacts:
    flagged = [r for r in ratios if r is not None]
    return _TopicFacts(
        outlets={outlet_key(p.platform.value, p.source_name) for p in group},
        platforms={p.platform for p in group},
        ratios=ratios,
        outlier_count=sum(r >= out.OUTLIER_RATIO for r in flagged),
        top_outlier_ratio=max(flagged) if flagged else None,
    )


# Los dos TypedDict reparten los campos de `Opportunity` por tema; pyright comprueba los nombres
# y los tipos al desempaquetarlos en el constructor.
class _TrendFields(TypedDict):
    lifecycle: Lifecycle
    lifecycle_reason: str
    growth_status: GrowthStatus
    velocity: float
    acceleration: float
    momentum_score: float
    outlier_count: int
    top_outlier_ratio: float | None


class _ScoreFields(TypedDict):
    audience_mix: AudienceMix
    latam_gap: bool | None
    cross_source_score: float
    saturation_score: float
    opportunity_score: float | None
    score_breakdown: ScoreBreakdown | None
    confidence: Confidence
    source_count: int
    evidence_strength: float
    recommendation: Recommendation
    recommendation_reason: str


def _trend_fields(topic: _ActiveTopic, facts: _TopicFacts, scores: _TopicScores) -> _TrendFields:
    return {
        "lifecycle": scores.stage.lifecycle,
        "lifecycle_reason": scores.stage.reason,
        "growth_status": scores.growth,
        "velocity": topic.velocity.velocity,
        "acceleration": topic.velocity.acceleration,
        "momentum_score": scores.momentum,
        "outlier_count": facts.outlier_count,
        "top_outlier_ratio": facts.top_outlier_ratio,
    }


def _score_fields(
    topic: _ActiveTopic, facts: _TopicFacts, scores: _TopicScores, *, saturation: float
) -> _ScoreFields:
    mix, gap = _audience(topic.group, facts.ratios)
    advice = recommend(
        scores.stage, scores.confidence, audience_fit=None, org_application=None, latam_gap=gap
    )
    return {
        "audience_mix": mix,
        "latam_gap": gap,
        "cross_source_score": scores.cross_source,
        "saturation_score": saturation,
        "opportunity_score": None if scores.breakdown is None else scores.breakdown.total,
        "score_breakdown": scores.breakdown,
        "confidence": scores.confidence,
        "source_count": len(facts.outlets),
        "evidence_strength": evidence_strength(len(topic.group), len(facts.outlets)),
        "recommendation": advice.recommendation,
        "recommendation_reason": advice.reason,
    }


def _description(group: Sequence[Piece], facts: _TopicFacts) -> str:
    platforms = ", ".join(sorted(p.value for p in facts.platforms))
    return (
        f"Tema agrupado automáticamente: {len(group)} piezas de {len(facts.outlets)} fuentes "
        f"independientes ({platforms})."
    )


def _opportunity(
    topic: _ActiveTopic,
    ratios: list[float | None],
    *,
    saturation: float,
    velocity_percentile: float,
    as_of: datetime,
    monitoring_started_at: datetime,
) -> tuple[Opportunity, Stage]:
    facts = _topic_facts(topic.group, ratios)
    scores = _score_topic(
        topic,
        outlets=facts.outlets,
        platforms=facts.platforms,
        outlier_count=facts.outlier_count,
        saturation=saturation,
        velocity_percentile=velocity_percentile,
    )
    opportunity = Opportunity(
        id=_stable_id(topic.group),
        topic=topic.rep.title,
        description=_description(topic.group, facts),
        **_trend_fields(topic, facts, scores),
        **_score_fields(topic, facts, scores, saturation=saturation),
        why_it_matters=_why_it_matters(topic, len(facts.outlets), facts.outlier_count),
        limitations=_limitations(
            scores.growth,
            platforms=facts.platforms,
            ratios=ratios,
            since=monitoring_started_at,
            broad=topic.broad,
        ),
        last_updated=as_of,
    )
    return opportunity, scores.stage


def _ranked(
    group: Sequence[Piece], ratios: Sequence[float | None]
) -> list[tuple[Piece, float | None]]:
    # Outliers primero y después lo más reciente; `item_id` desempata para que el orden (y lo
    # que se envía al LLM) no cambie entre ejecuciones.
    return sorted(
        zip(group, ratios, strict=True),
        key=lambda pair: (
            pair[1] is None,
            -(pair[1] or 0),
            -pair[0].published_at.timestamp(),
            pair[0].item_id,
        ),
    )


def build_opportunities(
    pieces: Sequence[Piece],
    clusters: Sequence[Sequence[int]],
    representatives: Sequence[int],
    *,
    as_of: datetime,
    monitoring_started_at: datetime,
    broad: Sequence[bool] | None = None,
) -> list[TopicResult]:
    ratios = outlier_ratios(pieces, as_of)
    broad_flags = broad if broad is not None else [False] * len(clusters)
    topics = _active_topics(pieces, clusters, representatives, broad_flags, as_of)
    if not topics:
        return []

    # Saturación y velocidad se normalizan entre temas: necesitan todos los temas activos.
    saturation = saturation_scores([t.counts.current + t.counts.previous for t in topics])
    velocity_pct = saturation_scores([t.velocity.current_count for t in topics])

    results = []
    for topic, sat, vel_pct in zip(topics, saturation, velocity_pct, strict=True):
        group_ratios = [ratios[p.item_id] for p in topic.group]
        opportunity, stage = _opportunity(
            topic,
            group_ratios,
            saturation=sat,
            velocity_percentile=vel_pct,
            as_of=as_of,
            monitoring_started_at=monitoring_started_at,
        )
        ranked = _ranked(topic.group, group_ratios)
        evidence = [_evidence(p, r) for p, r in ranked[:MAX_EVIDENCE]]
        timeline = _timeline(opportunity.id, [p.published_at for p in topic.group], as_of)
        results.append(
            TopicResult(opportunity, evidence, timeline, stage, pieces=[p for p, _ in ranked])
        )

    return rank(results)


# Lo que conviene publicar va primero. Al final, lo descartado (el score no mira la saturación
# como regla) y después lo que no tiene score, sin inventar dónde iría. Momentum y aceleración
# desempatan.
def rank(results: Sequence[TopicResult]) -> list[TopicResult]:
    def key(r: TopicResult) -> tuple[bool, bool, float, float, float]:
        o = r.opportunity
        scored = o.opportunity_score is not None
        kept = o.recommendation is not Recommendation.DISCARD
        return (scored, kept, o.opportunity_score or 0.0, o.momentum_score, o.acceleration)

    return sorted(results, key=key, reverse=True)
