"""Clasificación de piezas con la batería de pieza de Jev, cacheada en `jev_judgments`.

Una pieza ya clasificada no se vuelve a enviar mientras no cambien su `state`, la batería ni el
modelo. Si Jev falla en una pieza, esa pieza queda sin clasificar y el resto sigue.
"""

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.usage import UsageMeter
from app.core.config import get_settings
from app.intelligence.jev import (
    Judge,
    JudgeError,
    JudgeResult,
    cache_key,
    piece_battery,
    piece_state,
)
from app.intelligence.opportunities import Piece
from app.models import JevJudgment
from app.schemas.cost import Provider

log = structlog.get_logger()

PIECE_BATTERY_OPERATION = "piece_battery"
SKIPPED_WITHOUT_KEY = "sin TYPESAFE_API_KEY"


@dataclass
class ClassificationStats:
    classified: int
    cached: int
    failed: int
    skipped_reason: str | None = None


@dataclass(frozen=True)
class _Request:
    state: dict[str, Any]
    item_id: int


async def _judge_one(judge: Judge, request: _Request) -> JudgeResult | None:
    try:
        return await judge.judge(request.state, piece_battery().questions)
    except JudgeError as e:
        # Sin el state ni el mensaje: pueden llevar texto externo de la pieza.
        log.warning("jev_piece_failed", item_id=request.item_id, error=type(e).__name__)
        return None


async def _cached_keys(session: AsyncSession, keys: Sequence[str]) -> set[str]:
    rows = await session.scalars(
        select(JevJudgment.cache_key).where(JevJudgment.cache_key.in_(keys))
    )
    return set(rows)


async def _save(
    session: AsyncSession, judged: dict[str, JudgeResult], requests: dict[str, _Request], model: str
) -> None:
    if not judged:
        return
    battery = piece_battery()
    rows = [
        {
            "cache_key": key,
            "battery": battery.name,
            "battery_version": battery.version,
            "requested_model": model,
            "response_model": result.model,
            "content_item_id": requests[key].item_id,
            "answers": result.answers,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
        }
        for key, result in judged.items()
    ]
    stmt = insert(JevJudgment).values(rows).on_conflict_do_nothing(index_elements=["cache_key"])
    await session.execute(stmt)


def _requests_by_key(pieces: Sequence[Piece], model: str) -> tuple[list[str], dict[str, _Request]]:
    piece_keys: list[str] = []
    # Una sola llamada por clave: dos piezas con el mismo state comparten juicio y fila.
    requests: dict[str, _Request] = {}
    for p in pieces:
        state = piece_state(p)
        key = cache_key(state, model)
        piece_keys.append(key)
        requests.setdefault(key, _Request(state=state, item_id=p.item_id))
    return piece_keys, requests


async def classify_pieces(
    session: AsyncSession, pieces: Sequence[Piece], judge: Judge | None, meter: UsageMeter
) -> ClassificationStats:
    if judge is None:
        return ClassificationStats(
            classified=0, cached=0, failed=len(pieces), skipped_reason=SKIPPED_WITHOUT_KEY
        )
    model = get_settings().jev_model
    piece_keys, requests = _requests_by_key(pieces, model)
    cached = await _cached_keys(session, list(requests))
    missing = [key for key in requests if key not in cached]
    results = await asyncio.gather(*(_judge_one(judge, requests[key]) for key in missing))
    judged = {key: r for key, r in zip(missing, results, strict=True) if r is not None}

    await _save(session, judged, requests, model)
    for result in judged.values():
        meter.add(Provider.TYPESAFE_JEV, PIECE_BATTERY_OPERATION, units=result.input_tokens or 0)
    await session.commit()

    classified = sum(key in judged for key in piece_keys)
    from_cache = sum(key in cached for key in piece_keys)
    return ClassificationStats(
        classified=classified, cached=from_cache, failed=len(piece_keys) - classified - from_cache
    )
