"""De piezas agrupadas a oportunidades del contrato. Determinista: sin DB ni LLM.

Mientras no haya LLM, `topic` es el título de la pieza más representativa y los textos
(`description`, `why_it_matters`, `limitations`) son plantillas con los datos medidos.
"""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from app.intelligence import outliers as out
from app.intelligence.audience_mix import audience_mix, latam_gap, latam_share
from app.intelligence.cross_source import cross_source_score, outlet_key, saturation_scores
from app.intelligence.lifecycle import classify
from app.intelligence.ranking import (
    confidence,
    evidence_strength,
    growth_status,
    momentum_score,
    recommendation,
    score_breakdown,
)
from app.intelligence.velocity import WINDOW, piece_rate, topic_velocity, window_counts
from app.schemas.opportunity import (
    Evidence,
    GrowthStatus,
    Opportunity,
    OpportunityTimeline,
    Rate,
    TimelinePoint,
    TimelineWindow,
)
from app.schemas.signal import Metrics, Platform, Segment

# Métrica que mide el rendimiento de cada plataforma. RSS no expone métricas.
PERFORMANCE_METRIC = {Platform.YOUTUBE: "views", Platform.HACKERNEWS: "points"}
MIN_RECENT_ITEMS = 3  # piezas en las dos últimas ventanas para considerar el tema activo
MIX_WEIGHT_MIN, MIX_WEIGHT_MAX = 0.5, 3.0
MAX_EVIDENCE = 25


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
    snapshots: list[tuple[datetime, Metrics]] = field(default_factory=list)
    region: str | None = None  # de la fuente; decide si cuenta para el LATAM Gap


@dataclass
class TopicResult:
    opportunity: Opportunity
    evidence: list[Evidence]
    timeline: OpportunityTimeline


def _performance(p: Piece) -> float | None:
    metric = PERFORMANCE_METRIC.get(p.platform)
    value = getattr(p.metrics, metric) if metric else None
    if value is None:
        return None
    if p.platform is Platform.YOUTUBE:  # views se acumulan: se ajusta por edad
        return out.age_adjusted(value, p.published_at, p.observed_at)
    return float(value)


def outlier_ratios(pieces: Sequence[Piece]) -> dict[int, float | None]:
    """Ratio de cada pieza frente a su misma fuente (canal o query): mediana, o p90 en HN."""
    by_source: dict[int, list[float]] = defaultdict(list)
    perf = {p.item_id: _performance(p) for p in pieces}
    for p in pieces:
        if perf[p.item_id] is not None:
            by_source[p.source_id].append(perf[p.item_id])  # type: ignore[arg-type]
    return {
        p.item_id: None
        if perf[p.item_id] is None
        else out.outlier_ratio(
            perf[p.item_id],  # type: ignore[arg-type]
            by_source[p.source_id],
            out.HN_REFERENCE_QUANTILE if p.platform is Platform.HACKERNEWS else out.MEDIAN,
        )
        for p in pieces
    }


def _rate(p: Piece) -> Rate | None:
    metric = PERFORMANCE_METRIC.get(p.platform)
    if metric is None:
        return None
    value = piece_rate([(t, getattr(m, metric)) for t, m in p.snapshots])
    return None if value is None else Rate(value=value, unit=f"{metric}/h")


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
    growth: GrowthStatus, platforms: set[Platform], ratios: list[float | None], since: datetime
) -> list[str]:
    notes = [
        f"El monitoreo comenzó el {since:%d/%m}: los periodos anteriores no son históricos.",
        "Audience fit y análisis editorial pendientes (sin LLM todavía).",
    ]
    if growth is not GrowthStatus.OBSERVED:
        notes.append("Crecimiento no observado en dos ventanas: es estimado o preliminar.")
    if len(platforms) == 1:
        notes.append(f"Solo aparece en una plataforma ({next(iter(platforms)).value}).")
    if all(r is None for r in ratios):
        notes.append("Ninguna pieza tiene referencia para calcular outliers.")
    return notes


def build_opportunities(
    pieces: Sequence[Piece],
    clusters: Sequence[Sequence[int]],
    representatives: Sequence[int],
    *,
    as_of: datetime,
    monitoring_started_at: datetime,
    id_prefix: str,
) -> list[TopicResult]:
    corpus = window_counts([p.published_at for p in pieces], as_of)
    ratios = outlier_ratios(pieces)

    # Primera pasada: métricas por tema, para normalizar saturación y velocidad entre temas.
    topics = []
    for members, rep in zip(clusters, representatives, strict=True):
        group = [pieces[i] for i in members]
        counts = window_counts([p.published_at for p in group], as_of)
        if counts.current + counts.previous < MIN_RECENT_ITEMS:
            continue
        topics.append((group, pieces[rep], counts, topic_velocity(counts, corpus)))
    if not topics:
        return []

    saturation = saturation_scores([c.current + c.previous for _, _, c, _ in topics])
    velocity_pct = saturation_scores([v.current_count for *_, v in topics])

    results = []
    for n, (group, rep, counts, vel) in enumerate(topics, start=1):
        oid = f"{id_prefix}_{n:03d}"
        outlets = {outlet_key(p.platform.value, p.source_name) for p in group}
        platforms = {p.platform for p in group}
        group_ratios = [ratios[p.item_id] for p in group]
        flagged = [r for r in group_ratios if r is not None]
        outlier_count = sum(r >= out.OUTLIER_RATIO for r in flagged)

        weights = [min(max(r or 1.0, MIX_WEIGHT_MIN), MIX_WEIGHT_MAX) for r in group_ratios]
        mix = audience_mix([(p.segment, w) for p, w in zip(group, weights, strict=True)])
        latam = latam_share([(p.region, w) for p, w in zip(group, weights, strict=True)])
        assert mix is not None  # el grupo nunca está vacío
        stage = classify(
            acceleration=vel.acceleration,
            saturation=saturation[n - 1],
            source_count=len(outlets),
            item_count=len(group),
        )
        growth = growth_status(stage.insufficient, counts.previous)
        conf = confidence(growth, len(outlets), len(group))
        momentum = momentum_score(velocity_pct[n - 1], vel.acceleration, outlier_count)
        cross = cross_source_score(outlets, {p.value for p in platforms})
        breakdown = score_breakdown(
            momentum=momentum,
            audience_fit=None,
            cross_source=cross,
            saturation=saturation[n - 1],
            actionability=None,
            source_count=len(outlets),
            item_count=len(group),
        )

        opportunity = Opportunity(
            id=oid,
            topic=rep.title,
            description=(
                f"Tema agrupado automáticamente: {len(group)} piezas de {len(outlets)} fuentes "
                f"independientes ({', '.join(sorted(p.value for p in platforms))})."
            ),
            lifecycle=stage.lifecycle,
            lifecycle_reason=stage.reason,
            growth_status=growth,
            velocity=vel.velocity,
            acceleration=vel.acceleration,
            momentum_score=momentum,
            outlier_count=outlier_count,
            top_outlier_ratio=max(flagged) if flagged else None,
            audience_mix=mix,
            audience_fit_score=None,
            cross_source_score=cross,
            saturation_score=saturation[n - 1],
            actionability_score=None,
            opportunity_score=None if breakdown is None else breakdown.total,
            score_breakdown=breakdown,
            confidence=conf,
            source_count=len(outlets),
            evidence_strength=evidence_strength(len(group), len(outlets)),
            latam_gap=latam_gap(mix, latam),
            recommendation=recommendation(stage, conf, None),
            why_it_matters=(
                f"Pendiente de análisis editorial. Señales medidas: {counts.current} piezas en "
                f"los últimos 3 días frente a {counts.previous} en los 3 anteriores "
                f"(aceleración ajustada por volumen {vel.acceleration:+.0%}), "
                f"{len(outlets)} fuentes independientes y {outlier_count} outliers."
            ),
            limitations=_limitations(growth, platforms, group_ratios, monitoring_started_at),
            last_updated=as_of,
        )
        evidence = sorted(
            (_evidence(p, r) for p, r in zip(group, group_ratios, strict=True)),
            key=lambda e: (
                e.outlier_ratio is None,
                -(e.outlier_ratio or 0),
                -e.published_at.timestamp(),
            ),
        )[:MAX_EVIDENCE]
        timeline = _timeline(oid, [p.published_at for p in group], as_of)
        results.append(TopicResult(opportunity, evidence, timeline))

    results.sort(
        key=lambda r: (r.opportunity.momentum_score, r.opportunity.acceleration), reverse=True
    )
    return results
