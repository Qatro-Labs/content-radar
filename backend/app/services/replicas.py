"""Republicaciones de la misma nota con la batería de par de Jev, cacheada en `jev_judgments`.

Un par ya juzgado no se vuelve a enviar mientras no cambien su `state`, la batería ni el modelo.
Sin clave, si Jev falla en un par o si se pasa del tope por ejecución, ese par lo decide la regla
de respaldo de `intelligence.replicas` y el job sigue.
"""

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import structlog
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.usage import UsageMeter
from app.core.config import get_settings
from app.intelligence.jev import (
    SAME_STORY_QUESTION,
    Judge,
    JudgeError,
    JudgeResult,
    battery_cache_key,
    pair_battery,
    pair_state,
)
from app.intelligence.opportunities import Piece
from app.intelligence.replicas import (
    CandidatePair,
    ReplicaEdge,
    StoryAssignment,
    decide_pair,
    group_stories,
    same_story_verdict,
    topic_pairs,
)
from app.models import JevJudgment
from app.schemas.cost import Provider
from app.services.classification import SKIPPED_WITHOUT_KEY

log = structlog.get_logger()

PAIR_BATTERY_OPERATION = "pair_battery"
# Protege latencia y rate limits, no dinero: un tema amplio crece de forma cuadrática en pares.
MAX_PAIR_JUDGMENTS_PER_RUN = 250


@dataclass
class ReplicaStats:
    candidates: int
    judged: int  # llamadas nuevas con respuesta
    cached: int
    failed: int  # JudgeError
    over_budget: int
    replicas: int  # piezas marcadas como republicación
    unverified: int
    skipped_reason: str | None = None


@dataclass
class _Judged:
    answers: dict[str, dict[str, Any]]  # por cache_key, las nuevas y las de la caché
    new: set[str]
    failed: set[str]
    over_budget: set[str]


async def _judge_one(judge: Judge, key: str, state: dict[str, Any]) -> JudgeResult | None:
    try:
        return await judge.judge(state, pair_battery().questions)
    except JudgeError as e:
        # Sin el state ni el mensaje: pueden llevar texto externo de las piezas.
        log.warning("jev_pair_failed", cache_key=key, error=type(e).__name__)
        return None


async def _cached_answers(session: AsyncSession, keys: Sequence[str]) -> dict[str, dict[str, Any]]:
    rows = await session.execute(
        select(JevJudgment.cache_key, JevJudgment.answers).where(JevJudgment.cache_key.in_(keys))
    )
    return {key: answers for key, answers in rows.all()}


async def _save(session: AsyncSession, judged: dict[str, JudgeResult], *, model: str) -> None:
    battery = pair_battery()
    rows = [
        {
            "cache_key": key,
            "battery": battery.name,
            "battery_version": battery.version,
            "requested_model": model,
            "response_model": result.model,
            # Un par no es una pieza: la clave identifica el par por su state canónico.
            "content_item_id": None,
            "answers": result.answers,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
        }
        for key, result in judged.items()
    ]
    stmt = insert(JevJudgment).values(rows).on_conflict_do_nothing(index_elements=["cache_key"])
    await session.execute(stmt)


async def _judge_missing(
    session: AsyncSession,
    states: dict[str, dict[str, Any]],
    cached: dict[str, dict[str, Any]],
    *,
    judge: Judge,
    meter: UsageMeter,
) -> _Judged:
    # `states` sigue el orden de los candidatos: con el tope, se juzgan los más parecidos.
    missing = [key for key in states if key not in cached]
    allowed = missing[:MAX_PAIR_JUDGMENTS_PER_RUN]
    results = await asyncio.gather(*(_judge_one(judge, k, states[k]) for k in allowed))
    judged = {key: r for key, r in zip(allowed, results, strict=True) if r is not None}
    if judged:
        model = get_settings().jev_model
        await _save(session, judged, model=model)
        for result in judged.values():
            meter.add(Provider.TYPESAFE_JEV, PAIR_BATTERY_OPERATION, units=result.input_tokens or 0)
        await session.commit()
    answers = {**cached, **{key: r.answers for key, r in judged.items()}}
    return _Judged(answers, set(judged), set(allowed) - set(judged), set(missing[len(allowed) :]))


def _decided_edges(
    candidates: Sequence[CandidatePair], keys: Sequence[str], answers: dict[str, dict[str, Any]]
) -> list[ReplicaEdge]:
    edges = []
    for pair, key in zip(candidates, keys, strict=True):
        verdict = same_story_verdict(answers.get(key, {}).get(SAME_STORY_QUESTION))
        basis = decide_pair(pair, verdict)
        if basis is not None:
            edges.append(ReplicaEdge(pair.a.item_id, pair.b.item_id, basis))
    return edges


async def detect_replicas(
    session: AsyncSession,
    pieces: Sequence[Piece],
    clusters: Sequence[Sequence[int]],
    vectors: np.ndarray,
    *,
    judge: Judge | None,
    meter: UsageMeter,
) -> tuple[StoryAssignment, ReplicaStats]:
    edges, candidates = topic_pairs(pieces, clusters, vectors)
    model = get_settings().jev_model
    states = [pair_state(c.a, c.b) for c in candidates]
    keys = [battery_cache_key(pair_battery(), s, model) for s in states]
    # Sin candidatos no hay nada que leer; sin judge, la caché conserva los veredictos de Jev.
    cached = await _cached_answers(session, keys) if keys else {}
    by_key = dict(zip(keys, states, strict=True))
    if judge is None:
        judged = _Judged(cached, set(), set(), set())
    else:
        judged = await _judge_missing(session, by_key, cached, judge=judge, meter=meter)

    stories = group_stories(pieces, edges + _decided_edges(candidates, keys, judged.answers))
    return stories, ReplicaStats(
        candidates=len(candidates),
        judged=sum(key in judged.new for key in keys),
        cached=sum(key in cached for key in keys),
        failed=sum(key in judged.failed for key in keys),
        over_budget=sum(key in judged.over_budget for key in keys),
        replicas=len(stories.replica_ids),
        unverified=len(stories.unverified),
        skipped_reason=SKIPPED_WITHOUT_KEY if judge is None else None,
    )
