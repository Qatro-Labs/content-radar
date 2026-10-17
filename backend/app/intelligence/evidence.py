"""Evidencia de cada tema: qué piezas se guardan, en qué orden y con qué datos por pieza.

Determinista: sin DB ni LLM. La usa `intelligence.opportunities` al montar cada tema.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from pydantic import HttpUrl

from app.intelligence import outliers as out
from app.intelligence.replicas import StoryAssignment, replica_outlets
from app.intelligence.velocity import WINDOW, piece_rate
from app.schemas.opportunity import (
    Collection,
    Evidence,
    OpportunityTimeline,
    Rate,
    TimelinePoint,
    TimelineWindow,
)
from app.schemas.signal import Platform, SourceKind

if TYPE_CHECKING:
    # Solo para tipos: `opportunities` importa este módulo y un import real sería circular.
    from app.intelligence.opportunities import Piece

# Métrica que mide el rendimiento de cada plataforma. RSS no expone métricas. El score de Reddit
# se guarda en `points`, como el de HN.
PERFORMANCE_METRIC = {
    Platform.YOUTUBE: "views",
    Platform.TIKTOK: "views",
    Platform.INSTAGRAM: "views",
    Platform.HACKERNEWS: "points",
    Platform.REDDIT: "points",
}
MAX_EVIDENCE = 25


def _rate(p: Piece) -> Rate | None:
    metric = PERFORMANCE_METRIC.get(p.platform)
    if metric is None:
        return None
    value = piece_rate([(t, getattr(m, metric)) for t, m in p.snapshots])
    return None if value is None else Rate(value=value, unit=f"{metric}/h")


def _collection(kind: SourceKind) -> Collection:
    return Collection.MANUAL if kind is SourceKind.MANUAL else Collection.AUTOMATIC


def _evidence(
    p: Piece, ratio: float | None, *, replica_of: str | None, replica_count: int
) -> Evidence:
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
        replica_of=HttpUrl(replica_of) if replica_of else None,
        replica_count=replica_count,
    )


def timeline(oid: str, published: Sequence[datetime], as_of: datetime) -> OpportunityTimeline:
    days = int(WINDOW / timedelta(days=1))
    points = []
    for k in range(2 * days - 1, -1, -1):
        end = as_of - timedelta(days=k)
        count = sum(1 for t in published if end - timedelta(days=1) < t <= end)
        window = TimelineWindow.CURRENT if k < days else TimelineWindow.PREVIOUS
        points.append(TimelinePoint(date=end.date(), count=count, window=window))
    return OpportunityTimeline(opportunity_id=oid, window_days=days, points=points)


def ranked_pieces(
    group: Sequence[Piece], ratios: Sequence[float | None], replica_ids: frozenset[int]
) -> list[tuple[Piece, float | None]]:
    # Originales antes que republicaciones: con el corte de MAX_EVIDENCE, cada `replica_of`
    # apunta a una pieza guardada, y el LLM no gasta contexto en copias. Dentro de cada grupo,
    # outliers primero y después lo más reciente; `item_id` desempata para que el orden (y lo
    # que se envía al LLM) no cambie entre ejecuciones.
    return sorted(
        zip(group, ratios, strict=True),
        key=lambda pair: (
            pair[0].item_id in replica_ids,
            pair[1] is None,
            -(pair[1] or 0),
            -pair[0].published_at.timestamp(),
            pair[0].item_id,
        ),
    )


def topic_evidence(
    ranked: Sequence[tuple[Piece, float | None]],
    group: Sequence[Piece],
    stories: StoryAssignment,
) -> list[Evidence]:
    by_id = {p.item_id: p for p in group}
    # Sobre el tema completo, no sobre la evidencia recortada a MAX_EVIDENCE.
    outlets = replica_outlets(group, stories)
    evidence = []
    for p, ratio in ranked[:MAX_EVIDENCE]:
        rep_id = stories.representative_of.get(p.item_id)
        replica_of = by_id[rep_id].url if rep_id is not None else None
        count = outlets.get(p.item_id, 0)
        evidence.append(_evidence(p, ratio, replica_of=replica_of, replica_count=count))
    return evidence
