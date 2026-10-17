from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, cast

from pydantic import HttpUrl
from sqlalchemy import ColumnElement, CursorResult, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import ContentItem, MetricSnapshot, Source
from app.schemas.signal import (
    ContentSignal,
    Metrics,
    Platform,
    Segment,
    SignalHit,
    SourceStatus,
)
from app.services.opportunities import list_served

# Dos snapshots más juntos que esto no aportan velocidad (p. ej. dos ejecuciones seguidas).
MIN_SNAPSHOT_GAP = timedelta(minutes=30)
# Una letra suelta coincide con casi todo; más de cinco palabras en AND casi nunca coincide.
MIN_SEARCH_TERM_CHARS = 2
MAX_SEARCH_TERMS = 5
LIKE_ESCAPE = "\\"


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
            # Un INSERT devuelve un CursorResult; `execute` solo lo tipa como Result.
            result = cast(CursorResult[Any], await session.execute(snap))
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
            platform=Platform(src.platform),
            name=src.name,
            segment=Segment(src.segment),
            active=src.active,
            items=count,
            last_observed_at=last,
        )
        for src, count, last in rows
    ]


def _like_pattern(term: str) -> str:
    # La búsqueda es por palabras: `%` y `_` del usuario son literales, no comodines.
    escaped = (
        term.replace(LIKE_ESCAPE, LIKE_ESCAPE * 2)
        .replace("%", f"{LIKE_ESCAPE}%")
        .replace("_", f"{LIKE_ESCAPE}_")
    )
    return f"%{escaped}%"


def _contains(term: str) -> ColumnElement[bool]:
    pattern = _like_pattern(term)
    return or_(
        ContentItem.title.ilike(pattern, escape=LIKE_ESCAPE),
        ContentItem.description.ilike(pattern, escape=LIKE_ESCAPE),
    )


async def _served_ids_by_url(session: AsyncSession) -> dict[str, list[str]]:
    served = await list_served(session)
    ids_by_url: defaultdict[str, list[str]] = defaultdict(list)
    for s in served.items if served else []:
        for e in s.evidence:
            ids_by_url[str(e.url)].append(s.opportunity.id)
    return ids_by_url


def _to_hit(item: ContentItem, source: Source, ids_by_url: dict[str, list[str]]) -> SignalHit:
    latest = max(item.snapshots, key=lambda s: s.observed_at, default=None)
    # Normalizada igual que la URL de la evidencia guardada, para que coincidan.
    url = HttpUrl(item.url)
    return SignalHit(
        url=url,
        title=item.title,
        source=source.name,
        platform=Platform(item.platform),
        segment=Segment(source.segment),
        region=source.region,
        language=item.language or source.language,
        published_at=item.published_at,
        observed_at=latest.observed_at if latest else item.last_observed_at,
        metrics=Metrics.model_validate(latest, from_attributes=True) if latest else Metrics(),
        opportunity_ids=ids_by_url.get(str(url), []),
    )


async def search_signals(
    session: AsyncSession,
    *,
    query: str,
    platform: Platform | None,
    segment: Segment | None,
    since: datetime,
    limit: int,
) -> list[SignalHit]:
    """Piezas de fuentes activas con todas las palabras en el título o la descripción.

    `ValueError` si la consulta no tiene ninguna palabra válida.
    """
    terms = [t for t in query.split() if len(t) >= MIN_SEARCH_TERM_CHARS][:MAX_SEARCH_TERMS]
    if not terms:
        raise ValueError("La consulta no tiene palabras válidas")
    stmt = (
        select(ContentItem, Source)
        .join(Source)
        .where(Source.active.is_(True), ContentItem.published_at >= since)
        .where(*(_contains(t) for t in terms))
    )
    if platform:
        stmt = stmt.where(ContentItem.platform == platform.value)
    if segment:
        stmt = stmt.where(Source.segment == segment.value)
    stmt = (
        stmt.options(selectinload(ContentItem.snapshots))
        .order_by(ContentItem.published_at.desc(), ContentItem.id.desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()
    ids_by_url = await _served_ids_by_url(session)
    return [_to_hit(item, source, ids_by_url) for item, source in rows]
