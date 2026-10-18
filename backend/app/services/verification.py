"""Verificación de las afirmaciones de «por qué importa» con la batería `claim` de Jev, cacheada
en `jev_judgments` (CLAUDE.md §7, Verificación).

Una afirmación ya juzgada no se vuelve a enviar mientras no cambien su `state`, la batería ni el
modelo. Sin clave, si Jev falla o si se pasa del tope por ejecución, la afirmación queda sin
veredicto (`None`) y no se publica; el job sigue.
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
from app.core.config import Settings, get_settings
from app.intelligence.explanation import ClaimDraft
from app.intelligence.jev import (
    Judge,
    JudgeError,
    JudgeResult,
    battery_cache_key,
    build_judge,
    claim_battery,
    claim_supported,
)
from app.models import JevJudgment
from app.schemas.cost import Provider
from app.services.classification import SKIPPED_WITHOUT_KEY

log = structlog.get_logger()

CLAIM_BATTERY_OPERATION = "claim_battery"
# Unas 170 afirmaciones por ejecución en frío (56 temas × 3): el tope cubre una completa y protege
# de un bucle o de un corpus inesperado. Coste: 200 × ~800 tokens, menos de 0,01 $.
MAX_CLAIM_VERIFICATIONS_PER_RUN = 200


@dataclass(frozen=True)
class ClaimVerifier:
    judge: Judge | None  # None: sin TYPESAFE_API_KEY → solo se publica lo que ya está en caché
    budget: int = MAX_CLAIM_VERIFICATIONS_PER_RUN


def build_claim_verifier(settings: Settings) -> ClaimVerifier | None:
    if not settings.jev_verify_claims:
        return None
    return ClaimVerifier(judge=build_judge(settings))


@dataclass(frozen=True)
class ClaimCheck:
    topic_index: int
    claim: ClaimDraft
    state: dict[str, Any]


@dataclass
class VerifyStats:
    # Por llamada (cache_key): dos afirmaciones con el mismo state comparten una.
    verified: int = 0  # llamadas nuevas con respuesta
    cached: int = 0
    failed: int = 0  # JudgeError
    over_budget: int = 0
    # Por afirmación y por tema.
    rejected: int = 0  # claim_supported False: no se publican
    unverified_topics: int = 0  # con alguna afirmación sin veredicto, que no se publica
    skipped_reason: str | None = None


@dataclass
class _Judged:
    answers: dict[str, dict[str, Any]]  # por cache_key, las nuevas y las de la caché
    new: set[str]
    failed: set[str]
    over_budget: set[str]


def claim_cache_key(state: dict[str, Any]) -> str:
    return battery_cache_key(claim_battery(), state, get_settings().jev_model)


async def _judge_one(judge: Judge, key: str, state: dict[str, Any]) -> JudgeResult | None:
    try:
        return await judge.judge(state, claim_battery().questions)
    except JudgeError as e:
        # Sin el state ni el mensaje: llevan la afirmación y el texto externo de las piezas.
        log.warning("jev_claim_failed", cache_key=key, error=type(e).__name__)
        return None


async def _cached_answers(session: AsyncSession, keys: Sequence[str]) -> dict[str, dict[str, Any]]:
    rows = await session.execute(
        select(JevJudgment.cache_key, JevJudgment.answers).where(JevJudgment.cache_key.in_(keys))
    )
    return {key: answers for key, answers in rows.all()}


async def _save(session: AsyncSession, judged: dict[str, JudgeResult], *, model: str) -> None:
    battery = claim_battery()
    rows = [
        {
            "cache_key": key,
            "battery": battery.name,
            "battery_version": battery.version,
            "requested_model": model,
            "response_model": result.model,
            # Una afirmación no es una pieza, y el id del tema cambia entre ejecuciones.
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
    verifier: ClaimVerifier,
    meter: UsageMeter,
) -> _Judged:
    if verifier.judge is None:
        return _Judged(cached, set(), set(), set())
    judge = verifier.judge
    # `states` sigue el orden de `rank()`: con el tope, se verifica primero lo que se ve arriba.
    missing = [key for key in states if key not in cached]
    allowed = missing[: verifier.budget]
    results = await asyncio.gather(*(_judge_one(judge, k, states[k]) for k in allowed))
    judged = {key: r for key, r in zip(allowed, results, strict=True) if r is not None}
    if judged:
        await _save(session, judged, model=get_settings().jev_model)
        for result in judged.values():
            meter.add(
                Provider.TYPESAFE_JEV, CLAIM_BATTERY_OPERATION, units=result.input_tokens or 0
            )
        # Las llamadas pagadas no se pierden si el job falla después.
        await session.commit()
    answers = {**cached, **{key: r.answers for key, r in judged.items()}}
    return _Judged(answers, set(judged), set(allowed) - set(judged), set(missing[len(allowed) :]))


def _stats(
    checks: Sequence[ClaimCheck],
    keys: Sequence[str],
    *,
    verdicts: dict[str, bool | None],
    j: _Judged,
) -> VerifyStats:
    unverified = {c.topic_index for c, k in zip(checks, keys, strict=True) if verdicts[k] is None}
    return VerifyStats(
        verified=len(j.new),
        cached=sum(key not in j.new for key in j.answers),
        failed=len(j.failed),
        over_budget=len(j.over_budget),
        rejected=sum(verdicts[k] is False for k in keys),
        unverified_topics=len(unverified),
    )


async def verify_claims(
    session: AsyncSession,
    checks: Sequence[ClaimCheck],
    *,
    verifier: ClaimVerifier,
    meter: UsageMeter,
) -> tuple[dict[str, bool | None], VerifyStats]:
    keys = [claim_cache_key(c.state) for c in checks]
    states = dict(zip(keys, (c.state for c in checks), strict=True))
    # Sin afirmaciones no hay nada que leer; sin judge, la caché conserva los veredictos de Jev.
    cached = await _cached_answers(session, list(states)) if states else {}
    judged = await _judge_missing(session, states, cached, verifier=verifier, meter=meter)

    verdicts = {key: claim_supported(judged.answers.get(key, {})) for key in states}
    stats = _stats(checks, keys, verdicts=verdicts, j=judged)
    stats.skipped_reason = SKIPPED_WITHOUT_KEY if verifier.judge is None else None
    return verdicts, stats
