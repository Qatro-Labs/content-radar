from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ContentItem, MetricSnapshot, Source
from app.schemas.signal import ContentSignal, SourceStatus

# Dos snapshots más juntos que esto no aportan velocidad (p. ej. dos ejecuciones seguidas).
MIN_SNAPSHOT_GAP = timedelta(minutes=30)


@dataclass
class StoreResult:
    items_upserted: int
    snapshots_inserted: int


async def store_signals(
    session: AsyncSession, source: Source, signals: list[ContentSignal]
) -> StoreResult:
    """Upsert de contenidos (dedupe por platform + external_id) y un snapshot por observación."""
    snapshots = 0
    for s in signals:
        values = {
            "source_id": source.id,
            "platform": s.platform.value,
            "external_id": s.external_id,
            "url": str(s.url),
            "target_url": str(s.target_url) if s.target_url else None,
            "title": s.title,
            "description": s.description,
            "author_name": s.author_name,
            "published_at": s.published_at,
            "first_observed_at": s.observed_at,
            "last_observed_at": s.observed_at,
            "format": s.format.value,
            "language": s.language,
            "duration_seconds": s.duration_seconds,
        }
        stmt = insert(ContentItem).values(**values)
        # En conflicto se actualiza lo que puede cambiar.
        # Una descripción ausente no borra la ya guardada.
        # first_observed_at y source_id se conservan.
        stmt = stmt.on_conflict_do_update(
            index_elements=["platform", "external_id"],
            set_={
                "title": stmt.excluded.title,
                "description": func.coalesce(stmt.excluded.description, ContentItem.description),
                "last_observed_at": stmt.excluded.last_observed_at,
                "format": stmt.excluded.format,
            },
        ).returning(ContentItem.id)
        item_id = (await session.execute(stmt)).scalar_one()

        m = s.metrics
        has_metrics = any(v is not None for v in (m.views, m.likes, m.comments, m.points, m.shares))
        if has_metrics and await _snapshot_due(session, item_id, s.observed_at):
            snap = (
                insert(MetricSnapshot)
                .values(content_item_id=item_id, observed_at=s.observed_at, **m.model_dump())
                .on_conflict_do_nothing(index_elements=["content_item_id", "observed_at"])
            )
            result = await session.execute(snap)
            snapshots += result.rowcount or 0

    await session.commit()
    return StoreResult(items_upserted=len(signals), snapshots_inserted=snapshots)


async def _snapshot_due(session: AsyncSession, item_id: int, observed_at) -> bool:
    last = await session.scalar(
        select(func.max(MetricSnapshot.observed_at)).where(
            MetricSnapshot.content_item_id == item_id
        )
    )
    return last is None or abs(observed_at - last) >= MIN_SNAPSHOT_GAP


async def sources_status(session: AsyncSession) -> list[SourceStatus]:
    stmt = (
        select(
            Source,
            func.count(ContentItem.id),
            func.max(ContentItem.last_observed_at),
        )
        .outerjoin(ContentItem, ContentItem.source_id == Source.id)
        .group_by(Source.id)
        .order_by(Source.platform, Source.name)
    )
    rows = (await session.execute(stmt)).all()
    return [
        SourceStatus(
            id=src.id,
            platform=src.platform,
            name=src.name,
            segment=src.segment,
            active=src.active,
            items=count,
            last_observed_at=last,
        )
        for src, count, last in rows
    ]
