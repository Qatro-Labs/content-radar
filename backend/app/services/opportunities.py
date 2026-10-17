"""Oportunidades: cálculo (lo usa `app.jobs.analyze`) y lectura (la usan la API y el MCP).

La lectura siempre sirve la última ejecución correcta de `analyze`; nunca recalcula.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.intelligence.clustering import cluster, representative
from app.intelligence.embeddings import embed, embedding_text
from app.intelligence.opportunities import Piece, TopicResult, build_opportunities
from app.models import ContentItem, OpportunityRecord, PipelineRun, Source
from app.schemas.opportunity import (
    Confidence,
    Evidence,
    Lifecycle,
    Opportunity,
    OpportunityList,
    OpportunityTimeline,
    Period,
)
from app.schemas.signal import Metrics, Platform, Segment, SourceKind

ANALYZE_JOB = "analyze"
LOOKBACK = timedelta(days=14)
# Día en que empezó el monitoreo con snapshots (CLAUDE.md §9): lo anterior es backfill.
MONITORING_STARTED_AT = datetime(2026, 10, 16, tzinfo=UTC)


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
        .where(Source.active.is_(True), ContentItem.published_at > as_of - LOOKBACK)
        .options(selectinload(ContentItem.snapshots))
        .order_by(ContentItem.id)
    )
    pieces = []
    for item, source in (await session.execute(stmt)).all():
        snapshots = [(s.observed_at, _metrics(s)) for s in item.snapshots]
        pieces.append(
            Piece(
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
                observed_at=item.last_observed_at,
                metrics=snapshots[-1][1] if snapshots else Metrics(),
                source_kind=SourceKind(source.kind),
                snapshots=snapshots,
                region=source.region,
            )
        )
    return pieces


async def compute_opportunities(
    session: AsyncSession, run_id: int, as_of: datetime
) -> tuple[int, list[TopicResult]]:
    """Devuelve (piezas analizadas, oportunidades). No escribe nada."""
    pieces = await load_pieces(session, as_of)
    if not pieces:
        return 0, []
    vectors = embed([embedding_text(p.title, p.description) for p in pieces])
    clusters = cluster(vectors)
    reps = [representative(vectors, c) for c in clusters]
    results = build_opportunities(
        pieces,
        clusters,
        reps,
        as_of=as_of,
        monitoring_started_at=MONITORING_STARTED_AT,
        id_prefix=f"opp_{run_id}",
    )
    return len(pieces), results


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


async def _latest_run(session: AsyncSession) -> PipelineRun | None:
    return await session.scalar(
        select(PipelineRun)
        .where(PipelineRun.job == ANALYZE_JOB, PipelineRun.status == "success")
        .order_by(PipelineRun.finished_at.desc())
        .limit(1)
    )


async def list_opportunities(
    session: AsyncSession,
    *,
    lifecycle: Lifecycle | None = None,
    confidence: Confidence | None = None,
    topic: str | None = None,
) -> OpportunityList | None:
    """None si todavía no hay ninguna ejecución de `analyze`."""
    run = await _latest_run(session)
    if run is None or run.finished_at is None:
        return None
    rows = await session.scalars(
        select(OpportunityRecord)
        .where(OpportunityRecord.run_id == run.id)
        .order_by(OpportunityRecord.rank)
    )
    items = [Opportunity.model_validate(r.payload) for r in rows]
    if lifecycle:
        items = [o for o in items if o.lifecycle is lifecycle]
    if confidence:
        items = [o for o in items if o.confidence is confidence]
    if topic:
        items = [o for o in items if topic.lower() in o.topic.lower()]
    return OpportunityList(
        items=items,
        period=Period.D7,  # ventanas de 3 + 3 días
        generated_at=run.finished_at,
        monitoring_started_at=MONITORING_STARTED_AT,
    )


async def _record(session: AsyncSession, opportunity_id: str) -> OpportunityRecord | None:
    return await session.scalar(
        select(OpportunityRecord)
        .where(OpportunityRecord.opportunity_id == opportunity_id)
        .order_by(OpportunityRecord.run_id.desc())
        .limit(1)
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
