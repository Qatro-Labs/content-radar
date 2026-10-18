"""De piezas agrupadas a oportunidades del contrato. Determinista: sin DB ni LLM.

Sale sin audience fit: lo añade después `intelligence.audience_fit` con los niveles del LLM.
`topic` es el título de la pieza más representativa y los textos (`description`,
`why_it_matters`, `limitations`) son plantillas con los datos medidos.
"""

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TypedDict

from app.intelligence import outliers as out
from app.intelligence.audience_mix import (
    audience_mix,
    has_business_conversation,
    latam_gap,
    latam_share,
)
from app.intelligence.cross_source import cross_source_score, outlet_key, saturation_scores
from app.intelligence.evidence import (
    PERFORMANCE_METRIC,
    ranked_pieces,
    timeline,
    topic_evidence,
)
from app.intelligence.lifecycle import Stage, classify
from app.intelligence.ranking import (
    confidence,
    evidence_strength,
    growth_status,
    momentum_score,
    recommend,
    score_breakdown,
)
from app.intelligence.replicas import (
    NO_REPLICAS,
    StoryAssignment,
    replica_notes,
)
from app.intelligence.velocity import (
    TopicVelocity,
    WindowCounts,
    acceleration_p_value,
    topic_velocity,
    window_counts,
)
from app.schemas.opportunity import (
    AudienceMix,
    Confidence,
    Evidence,
    GrowthStatus,
    Lifecycle,
    Opportunity,
    OpportunityTimeline,
    Recommendation,
    ScoreBreakdown,
)
from app.schemas.signal import Metrics, Platform, Segment, SourceKind

# Plataformas cuyas views se acumulan con los días: su rendimiento se ajusta por edad.
CUMULATIVE_VIEWS = {Platform.YOUTUBE, Platform.TIKTOK, Platform.INSTAGRAM}
MIN_RECENT_ITEMS = 3  # piezas en las dos últimas ventanas para considerar el tema activo
MIX_WEIGHT_MIN, MIX_WEIGHT_MAX = 0.5, 3.0
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
    target_url: str | None = None  # enlace externo de HN y Reddit: delata republicaciones


@dataclass
class _ActiveTopic:
    group: list[Piece]
    rep: Piece
    counts: WindowCounts
    velocity: TopicVelocity
    broad: bool
    story_counts: WindowCounts  # solo notas originales: son las muestras independientes
    p_value: float  # de la aceleración, sobre las notas originales


@dataclass
class TopicResult:
    opportunity: Opportunity
    evidence: list[Evidence]
    timeline: OpportunityTimeline
    # Para añadir el audience fit después sin reconstruir la etapa ni el grupo desde el contrato.
    stage: Stage
    pieces: list[Piece]
    replica_ids: frozenset[int] = field(default_factory=frozenset)
    ratios: dict[int, float | None] = field(default_factory=dict)  # outlier_ratio por item_id

    # Sin las republicaciones de la misma nota, que no cuentan como muestra (CLAUDE.md §7).
    @property
    def story_count(self) -> int:
        return len(self.pieces) - len(self.replica_ids & {p.item_id for p in self.pieces})


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


def outlier_ratios(
    pieces: Sequence[Piece], as_of: datetime, *, reference: Sequence[Piece] | None = None
) -> dict[int, float | None]:
    """Ratio de cada pieza de `pieces` frente a las otras de su fuente (canal o query) en
    `reference` (por defecto, `pieces`) con edad suficiente: mediana, o p90 en HN y TikTok.
    """
    by_source: dict[int, list[tuple[int, float]]] = defaultdict(list)
    for p in pieces if reference is None else reference:
        value = _performance(p)
        if value is not None and _old_enough_for_reference(p, as_of):
            by_source[p.source_id].append((p.item_id, value))
    ratios: dict[int, float | None] = {}
    for p in pieces:
        value = _performance(p)
        if value is None:
            ratios[p.item_id] = None
            continue
        others = [v for item_id, v in by_source[p.source_id] if item_id != p.item_id]
        ratios[p.item_id] = out.outlier_ratio(value, others, out.reference_quantile(p.platform))
    return ratios


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
    stories: StoryAssignment,
) -> list[_ActiveTopic]:
    corpus = window_counts([p.published_at for p in pieces], as_of)
    # Una republicación no es una observación independiente: el test de la aceleración cuenta
    # notas, en el tema y en el corpus (CLAUDE.md §7, "Cross-source").
    story_corpus = window_counts([p.published_at for p in _originals(pieces, stories)], as_of)
    topics = []
    for members, rep, is_broad in zip(clusters, representatives, broad, strict=True):
        group = [pieces[i] for i in members]
        counts = window_counts([p.published_at for p in group], as_of)
        if counts.current + counts.previous < MIN_RECENT_ITEMS:
            continue
        velocity = topic_velocity(counts, corpus)
        story_counts = window_counts([p.published_at for p in _originals(group, stories)], as_of)
        p_value = acceleration_p_value(story_counts, story_corpus)
        topics.append(
            _ActiveTopic(group, pieces[rep], counts, velocity, is_broad, story_counts, p_value)
        )
    return topics


def _audience(
    group: Sequence[Piece], ratios: Sequence[float | None], business_use: Sequence[bool | None]
) -> tuple[AudienceMix, bool | None]:
    weights = [min(max(r or 1.0, MIX_WEIGHT_MIN), MIX_WEIGHT_MAX) for r in ratios]
    mix = audience_mix([(p.segment, w) for p, w in zip(group, weights, strict=True)])
    latam = latam_share([(p.region, w) for p, w in zip(group, weights, strict=True)])
    assert mix is not None  # el grupo nunca está vacío
    return mix, latam_gap(has_business_conversation(mix, business_use), latam)


def _why_it_matters(topic: _ActiveTopic, source_count: int, outlier_count: int) -> str:
    return (
        f"Pendiente de análisis editorial. Señales medidas: {topic.counts.current} piezas en "
        f"los últimos 3 días frente a {topic.counts.previous} en los 3 anteriores "
        f"(aceleración ajustada por volumen {topic.velocity.acceleration:+.0%}), "
        f"{source_count} fuentes independientes y {outlier_count} outliers."
    )


@dataclass
class _TopicFacts:
    outlets: set[str]  # solo de las piezas originales
    original_platforms: set[Platform]
    ratios: list[float | None]
    outlier_count: int
    top_outlier_ratio: float | None
    replica_ids: frozenset[int]
    story_count: int
    unverified: bool  # alguna republicación decidida solo por título o similitud
    business_use: list[bool | None]  # juicio de Jev por pieza; None = incierto o sin juicio

    @property
    def replica_count(self) -> int:
        return len(self.replica_ids)


def _topic_facts(
    group: Sequence[Piece],
    ratios: list[float | None],
    stories: StoryAssignment,
    business_use: Mapping[int, bool | None],
) -> _TopicFacts:
    flagged = [r for r in ratios if r is not None]
    originals = _originals(group, stories)
    replica_ids = frozenset(p.item_id for p in group) & stories.replica_ids
    return _TopicFacts(
        outlets={outlet_key(p.platform.value, p.source_name) for p in originals},
        original_platforms={p.platform for p in originals},
        ratios=ratios,
        outlier_count=sum(r >= out.OUTLIER_RATIO for r in flagged),
        top_outlier_ratio=max(flagged) if flagged else None,
        replica_ids=replica_ids,
        story_count=len(originals),
        unverified=bool(replica_ids & stories.unverified),
        business_use=[business_use.get(p.item_id) for p in group],
    )


def _originals(group: Sequence[Piece], stories: StoryAssignment) -> list[Piece]:
    return [p for p in group if p.item_id not in stories.replica_ids]


def _limitations(
    growth: GrowthStatus, facts: _TopicFacts, *, since: datetime, broad: bool
) -> list[str]:
    platforms, ratios = facts.original_platforms, facts.ratios
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
    return notes + replica_notes(facts.replica_count, unverified=facts.unverified)


@dataclass
class _TopicScores:
    stage: Stage
    growth: GrowthStatus
    confidence: Confidence
    momentum: float
    cross_source: float
    breakdown: ScoreBreakdown | None


def _score_topic(
    topic: _ActiveTopic, facts: _TopicFacts, *, saturation: float, velocity_percentile: float
) -> _TopicScores:
    # Fuentes y muestra sin republicaciones; velocidad y momentum siguen por pieza
    # (CLAUDE.md §7, "Cross-source").
    acceleration, item_count = topic.velocity.acceleration, facts.story_count
    source_count = len(facts.outlets)
    stage = classify(
        acceleration=acceleration,
        p_value=topic.p_value,
        saturation=saturation,
        source_count=source_count,
        item_count=item_count,
    )
    growth = growth_status(stage.insufficient, topic.counts.previous)
    momentum = momentum_score(velocity_percentile, topic.velocity.log_ratio, facts.outlier_count)
    cross = cross_source_score(facts.outlets, {p.value for p in facts.original_platforms})
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
    mix, gap = _audience(topic.group, facts.ratios, facts.business_use)
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
        "evidence_strength": evidence_strength(facts.story_count, len(facts.outlets)),
        "recommendation": advice.recommendation,
        "recommendation_reason": advice.reason,
    }


def _description(group: Sequence[Piece], facts: _TopicFacts) -> str:
    platforms = ", ".join(sorted(p.value for p in facts.original_platforms))
    replicas = ""
    if facts.replica_count == 1:
        replicas = " (1 republicación)"
    elif facts.replica_count > 1:
        replicas = f" ({facts.replica_count} republicaciones)"
    text = (
        f"Tema agrupado automáticamente: {len(group)} piezas{replicas} de "
        f"{len(facts.outlets)} fuentes independientes ({platforms})."
    )
    return text + _business_note(facts.business_use)


def _business_note(business_use: Sequence[bool | None]) -> str:
    # El hueco LATAM se decide con este conteo, no con el segmento de las fuentes: sin decirlo,
    # "negocio 0 %" junto a "hueco en LATAM" parecería una contradicción.
    decided = [label for label in business_use if label is not None]
    if not decided:
        return ""
    return (
        f" {sum(decided)} de {len(decided)} piezas clasificadas tratan del uso de la IA en "
        "organizaciones."
    )


def _opportunity(
    topic: _ActiveTopic,
    facts: _TopicFacts,
    *,
    saturation: float,
    velocity_percentile: float,
    as_of: datetime,
    monitoring_started_at: datetime,
) -> tuple[Opportunity, Stage]:
    scores = _score_topic(
        topic, facts, saturation=saturation, velocity_percentile=velocity_percentile
    )
    opportunity = Opportunity(
        id=_stable_id(topic.group),
        topic=topic.rep.title,
        description=_description(topic.group, facts),
        **_trend_fields(topic, facts, scores),
        **_score_fields(topic, facts, scores, saturation=saturation),
        why_it_matters=_why_it_matters(topic, len(facts.outlets), facts.outlier_count),
        limitations=_limitations(
            scores.growth, facts, since=monitoring_started_at, broad=topic.broad
        ),
        last_updated=as_of,
    )
    return opportunity, scores.stage


def _topic_result(
    topic: _ActiveTopic,
    ratios: Mapping[int, float | None],
    stories: StoryAssignment,
    business_use: Mapping[int, bool | None],
    *,
    saturation: float,
    velocity_percentile: float,
    as_of: datetime,
    monitoring_started_at: datetime,
) -> TopicResult:
    group_ratios = [ratios[p.item_id] for p in topic.group]
    facts = _topic_facts(topic.group, group_ratios, stories, business_use)
    opportunity, stage = _opportunity(
        topic,
        facts,
        saturation=saturation,
        velocity_percentile=velocity_percentile,
        as_of=as_of,
        monitoring_started_at=monitoring_started_at,
    )
    ranked = ranked_pieces(topic.group, group_ratios, facts.replica_ids)
    evidence = topic_evidence(ranked, topic.group, stories)
    points = timeline(opportunity.id, [p.published_at for p in topic.group], as_of)
    pieces = [p for p, _ in ranked]
    return TopicResult(
        opportunity,
        evidence,
        points,
        stage,
        pieces,
        facts.replica_ids,
        {p.item_id: r for p, r in ranked},
    )


def _across_topics(topics: Sequence[_ActiveTopic]) -> list[tuple[float, float]]:
    # Saturación y percentil de velocidad se normalizan entre temas: necesitan todos los activos.
    # La saturación cuenta notas, no copias (CLAUDE.md §7); la velocidad sigue por pieza.
    saturation = saturation_scores(
        [t.story_counts.current + t.story_counts.previous for t in topics]
    )
    velocity_pct = saturation_scores([t.velocity.current_count for t in topics])
    return list(zip(saturation, velocity_pct, strict=True))


def build_opportunities(
    pieces: Sequence[Piece],
    clusters: Sequence[Sequence[int]],
    representatives: Sequence[int],
    *,
    as_of: datetime,
    monitoring_started_at: datetime,
    broad: Sequence[bool] | None = None,
    reference: Sequence[Piece] | None = None,
    stories: StoryAssignment | None = None,
    business_use: Mapping[int, bool | None] | None = None,
) -> list[TopicResult]:
    """`business_use`: juicio de Jev por pieza (CLAUDE.md §7, LATAM Gap); sin él, el segmento."""
    stories = stories if stories is not None else NO_REPLICAS
    broad_flags = broad if broad is not None else [False] * len(clusters)
    topics = _active_topics(pieces, clusters, representatives, broad_flags, as_of, stories)
    ratios = outlier_ratios(pieces, as_of, reference=reference)
    results = [
        _topic_result(
            topic,
            ratios,
            stories,
            business_use or {},
            saturation=sat,
            velocity_percentile=vel_pct,
            as_of=as_of,
            monitoring_started_at=monitoring_started_at,
        )
        for topic, (sat, vel_pct) in zip(topics, _across_topics(topics), strict=True)
    ]
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
