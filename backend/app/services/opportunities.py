"""Oportunidades: cálculo (lo usa `app.jobs.analyze`) y lectura (la usan la API y el MCP).

La lectura sirve la ejecución fijada en DEMO_RUN_ID o, sin ella, la última correcta de `analyze`;
nunca recalcula.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.intelligence.clustering import cluster, is_broad, representative
from app.intelligence.embeddings import embed, embedding_text
from app.intelligence.jev import PieceJudgment, keep_about_ai
from app.intelligence.opportunities import Piece, TopicResult, build_opportunities
from app.models import ContentItem, MetricSnapshot, OpportunityRecord, PipelineRun, Source
from app.schemas.opportunity import (
    Confidence,
    Evidence,
    Lifecycle,
    Opportunity,
    OpportunityList,
    OpportunityTimeline,
    Period,
    TopicEvidence,
)
from app.schemas.signal import Metrics, Platform, Segment, SourceKind

ANALYZE_JOB = "analyze"
LOOKBACK = timedelta(days=14)
# Día en que empezó el monitoreo con snapshots (CLAUDE.md §9): lo anterior es backfill.
MONITORING_STARTED_AT = datetime(2026, 10, 16, tzinfo=UTC)
# Lo que cubren las ventanas de 3 + 3 días de `analyze`: es el único periodo que se calcula.
SERVED_PERIOD = Period.D7


def _metrics(snapshot) -> Metrics:
    return Metrics(
        views=snapshot.views,
        likes=snapshot.likes,
        comments=snapshot.comments,
        points=snapshot.points,
        shares=snapshot.shares,
    )


async def load_pieces(session: AsyncSession, as_of: datetime) -> list[Piece]:
    stmt = (
        select(ContentItem, Source)
        .join(Source)
        # Solo lo publicado, recolectado y observado hasta `as_of`: el mismo `as_of` tiene que
        # dar el mismo resultado. `Source.active` y los textos de cada pieza no tienen historial
        # y se leen como están hoy; por eso la demo usa una ejecución guardada (CLAUDE.md §13).
        .where(
            Source.active.is_(True),
            ContentItem.published_at > as_of - LOOKBACK,
            ContentItem.published_at <= as_of,
            ContentItem.first_observed_at <= as_of,
        )
        .options(selectinload(ContentItem.snapshots.and_(MetricSnapshot.observed_at <= as_of)))
        .order_by(ContentItem.id)
    )
    pieces = []
    for item, source in (await session.execute(stmt)).all():
        # El filtro del loader no se aplica a colecciones ya cargadas en la sesión: se repite aquí.
        kept = sorted(
            (s for s in item.snapshots if s.observed_at <= as_of), key=lambda s: s.observed_at
        )
        snapshots = [(s.observed_at, _metrics(s)) for s in kept]
        pieces.append(_to_piece(item, source, snapshots, as_of=as_of))
    return pieces


def _to_piece(
    item: ContentItem,
    source: Source,
    snapshots: list[tuple[datetime, Metrics]],
    *,
    as_of: datetime,
) -> Piece:
    return Piece(
        item_id=item.id,
        url=item.url,
        title=item.title,
        description=item.description,
        platform=Platform(item.platform),
        source_id=source.id,
        source_name=source.name,
        segment=Segment(source.segment),
        language=item.language or source.language,
        published_at=item.published_at,
        observed_at=snapshots[-1][0] if snapshots else min(item.last_observed_at, as_of),
        metrics=snapshots[-1][1] if snapshots else Metrics(),
        source_kind=SourceKind(source.kind),
        snapshots=snapshots,
        region=source.region,
    )


async def load_evidence_pieces(
    session: AsyncSession, evidence: Sequence[Evidence], *, as_of: datetime
) -> list[tuple[Piece, Evidence]]:
    """Las piezas de la evidencia guardada, en su orden, con el texto con que las juzgó Jev."""
    urls = [str(e.url) for e in evidence]
    rows = await session.execute(
        select(ContentItem, Source).join(Source).where(ContentItem.url.in_(urls))
    )
    # La misma URL puede estar en dos fuentes: la evidencia dice de cuál es.
    by_key = {(item.url, source.name): (item, source) for item, source in rows.all()}
    found = []
    for e in evidence:
        if match := by_key.get((str(e.url), e.source)):
            found.append((_to_piece(*match, [], as_of=as_of), e))
    return found


@dataclass
class ComputedOpportunities:
    analyzed: int  # piezas que entran al clustering
    off_topic_removed: int  # piezas que Jev dice con seguridad que no tratan de IA
    results: list[TopicResult]


async def compute_opportunities(
    session: AsyncSession,
    as_of: datetime,
    *,
    pieces: list[Piece] | None = None,
    judgments: Mapping[int, PieceJudgment] | None = None,
) -> ComputedOpportunities:
    """No escribe nada."""
    if pieces is None:
        pieces = await load_pieces(session, as_of)
    loaded = len(pieces)
    pieces = keep_about_ai(pieces, judgments or {})
    removed = loaded - len(pieces)
    if not pieces:
        return ComputedOpportunities(0, removed, [])
    vectors = embed([embedding_text(p.title, p.description) for p in pieces])
    clusters = cluster(vectors)
    reps = [representative(vectors, c) for c in clusters]
    results = build_opportunities(
        pieces,
        clusters,
        reps,
        as_of=as_of,
        monitoring_started_at=MONITORING_STARTED_AT,
        broad=[is_broad(vectors, c) for c in clusters],
    )
    return ComputedOpportunities(len(pieces), removed, results)


async def save_opportunities(session: AsyncSession, run_id: int, results: list[TopicResult]):
    for rank, r in enumerate(results, start=1):
        session.add(
            OpportunityRecord(
                run_id=run_id,
                opportunity_id=r.opportunity.id,
                rank=rank,
                payload=r.opportunity.model_dump(mode="json"),
                evidence=[e.model_dump(mode="json") for e in r.evidence],
                timeline=r.timeline.model_dump(mode="json"),
            )
        )


async def _served_run(session: AsyncSession) -> PipelineRun | None:
    successful = select(PipelineRun).where(
        PipelineRun.job == ANALYZE_JOB, PipelineRun.status == "success"
    )
    demo_run_id = get_settings().demo_run_id
    if demo_run_id is not None:
        # Sin caer a la última: una demo fijada a una ejecución que no existe tiene que notarse.
        return await session.scalar(successful.where(PipelineRun.id == demo_run_id))
    return await session.scalar(successful.order_by(PipelineRun.finished_at.desc()).limit(1))


def _matches(
    o: Opportunity,
    *,
    lifecycle: Lifecycle | None,
    confidence: Confidence | None,
    topic: str | None,
) -> bool:
    return (
        (lifecycle is None or o.lifecycle is lifecycle)
        and (confidence is None or o.confidence is confidence)
        and (not topic or topic.lower() in o.topic.lower())
    )


async def _ranked_records(session: AsyncSession, run: PipelineRun) -> list[OpportunityRecord]:
    rows = await session.scalars(
        select(OpportunityRecord)
        .where(OpportunityRecord.run_id == run.id)
        .order_by(OpportunityRecord.rank)
    )
    return list(rows)


async def list_opportunities(
    session: AsyncSession,
    *,
    lifecycle: Lifecycle | None = None,
    confidence: Confidence | None = None,
    topic: str | None = None,
) -> OpportunityList | None:
    """None si todavía no hay ninguna ejecución de `analyze`."""
    run = await _served_run(session)
    if run is None or run.finished_at is None:
        return None
    items = [Opportunity.model_validate(r.payload) for r in await _ranked_records(session, run)]
    return OpportunityList(
        items=[
            o for o in items if _matches(o, lifecycle=lifecycle, confidence=confidence, topic=topic)
        ],
        period=SERVED_PERIOD,
        generated_at=run.finished_at,
        monitoring_started_at=MONITORING_STARTED_AT,
    )


async def _record(session: AsyncSession, opportunity_id: str) -> OpportunityRecord | None:
    # De la misma ejecución que el listado: los ids y los scores cambian entre ejecuciones.
    run = await _served_run(session)
    if run is None:
        return None
    return await session.scalar(
        select(OpportunityRecord).where(
            OpportunityRecord.run_id == run.id,
            OpportunityRecord.opportunity_id == opportunity_id,
        )
    )


@dataclass(frozen=True)
class ServedOpportunity:
    opportunity: Opportunity
    evidence: list[Evidence]
    timeline: OpportunityTimeline


@dataclass(frozen=True)
class ServedRun:
    generated_at: datetime
    items: list[ServedOpportunity]


def _served(r: OpportunityRecord) -> ServedOpportunity:
    return ServedOpportunity(
        opportunity=Opportunity.model_validate(r.payload),
        evidence=[Evidence.model_validate(e) for e in r.evidence],
        timeline=OpportunityTimeline.model_validate(r.timeline),
    )


async def get_served(session: AsyncSession, opportunity_id: str) -> ServedOpportunity | None:
    r = await _record(session, opportunity_id)
    return None if r is None else _served(r)


async def list_served(
    session: AsyncSession,
    *,
    lifecycle: Lifecycle | None = None,
    confidence: Confidence | None = None,
    topic: str | None = None,
) -> ServedRun | None:
    """Como `list_opportunities`, con evidencia y timeline (sin una query por oportunidad)."""
    run = await _served_run(session)
    if run is None or run.finished_at is None:
        return None
    served = [_served(r) for r in await _ranked_records(session, run)]
    return ServedRun(
        generated_at=run.finished_at,
        items=[
            s
            for s in served
            if _matches(s.opportunity, lifecycle=lifecycle, confidence=confidence, topic=topic)
        ],
    )


async def get_opportunity(session: AsyncSession, opportunity_id: str) -> Opportunity | None:
    r = await _record(session, opportunity_id)
    return None if r is None else Opportunity.model_validate(r.payload)


async def get_evidence(session: AsyncSession, opportunity_id: str) -> list[Evidence] | None:
    r = await _record(session, opportunity_id)
    return None if r is None else [Evidence.model_validate(e) for e in r.evidence]


async def get_timeline(session: AsyncSession, opportunity_id: str) -> OpportunityTimeline | None:
    r = await _record(session, opportunity_id)
    return None if r is None else OpportunityTimeline.model_validate(r.timeline)


def _strongest_outlier_first(e: Evidence) -> tuple[bool, float, datetime]:
    # Para ordenar con reverse=True: primero las piezas con ratio, de mayor a menor; en empate
    # y entre las que no tienen ratio, la más reciente.
    return (e.outlier_ratio is not None, e.outlier_ratio or 0, e.published_at)


async def list_all_evidence(session: AsyncSession) -> list[TopicEvidence] | None:
    """None si todavía no hay ninguna ejecución de `analyze`."""
    run = await _served_run(session)
    if run is None:
        return None
    evidence = [
        TopicEvidence.model_validate({**e, "opportunity_id": r.opportunity_id})
        for r in await _ranked_records(session, run)
        for e in r.evidence
    ]
    return sorted(evidence, key=_strongest_outlier_first, reverse=True)


async def list_timelines(session: AsyncSession) -> list[OpportunityTimeline] | None:
    """En el orden del ranking; None si todavía no hay ninguna ejecución de `analyze`."""
    run = await _served_run(session)
    if run is None:
        return None
    records = await _ranked_records(session, run)
    return [OpportunityTimeline.model_validate(r.timeline) for r in records]
