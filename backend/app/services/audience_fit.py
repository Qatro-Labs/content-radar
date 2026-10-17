"""Audience fit de cada tema con el LLM, cacheado en `llm_evaluations` (CLAUDE.md §7).

Un tema ya evaluado no se vuelve a enviar mientras no cambie su entrada. Si el LLM falla en un
tema, ese tema queda sin fit (null y una limitación) y el resto sigue (plan intel-phase1-llm-fit,
D9).
"""

import asyncio
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.usage import UsageMeter
from app.core.config import get_settings
from app.editorial.audience import (
    PROMPT_VERSION,
    TopicEvaluation,
    TopicInput,
    build_topic_input,
    evaluation_cache_key,
)
from app.editorial.evaluator import EvaluationError, EvaluationResult, TopicEvaluator
from app.intelligence.audience_fit import apply_fit, apply_topic_name, mark_fit_failed
from app.intelligence.opportunities import TopicResult
from app.models import LlmEvaluation
from app.schemas.cost import Provider

log = structlog.get_logger()

EVALUATE_TOPIC_OPERATION = "evaluate_topic"
SKIPPED_WITHOUT_KEY = "sin LLM_API_KEY o LLM_MODEL"


@dataclass
class FitStats:
    evaluated: int
    cached: int
    failed: int
    without_evidence: int  # ninguna pieza segura que enviar al LLM
    skipped_reason: str | None = None


@dataclass(frozen=True)
class _Pending:
    key: str
    topic: TopicInput
    opportunity_id: str


async def _evaluate_one(evaluator: TopicEvaluator, pending: _Pending) -> EvaluationResult | None:
    try:
        return await evaluator.evaluate(pending.topic)
    except EvaluationError as e:
        log.warning("llm_topic_failed", opportunity_id=pending.opportunity_id, error=str(e))
        return None


async def _cached_outputs(session: AsyncSession, keys: Sequence[str]) -> dict[str, TopicEvaluation]:
    rows = await session.execute(
        select(LlmEvaluation.cache_key, LlmEvaluation.output).where(
            LlmEvaluation.cache_key.in_(keys)
        )
    )
    return {key: TopicEvaluation.model_validate(output) for key, output in rows.all()}


async def _save(
    session: AsyncSession, evaluated: dict[str, EvaluationResult], pending: dict[str, _Pending]
) -> None:
    if not evaluated:
        return
    rows = [
        {
            "cache_key": key,
            "operation": EVALUATE_TOPIC_OPERATION,
            "prompt_version": PROMPT_VERSION,
            "requested_model": get_settings().llm_model,
            "response_model": result.model,
            "opportunity_id": pending[key].opportunity_id,
            "output": result.output.model_dump(mode="json"),
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
        }
        for key, result in evaluated.items()
    ]
    stmt = insert(LlmEvaluation).values(rows).on_conflict_do_nothing(index_elements=["cache_key"])
    await session.execute(stmt)
    # Commit en cuanto llegan: si el job falla después, las llamadas ya pagadas no se pierden.
    await session.commit()


def _pending_by_key(
    results: Sequence[TopicResult],
    *,
    inputs: Sequence[TopicInput],
    keys: Sequence[str],
    cached: Mapping[str, Any],
) -> dict[str, _Pending]:
    pending: dict[str, _Pending] = {}
    for result, topic, key in zip(results, inputs, keys, strict=True):
        if topic.pieces and key not in cached:
            pending.setdefault(key, _Pending(key, topic, result.opportunity.id))
    return pending


async def _evaluate_pending(
    session: AsyncSession,
    evaluator: TopicEvaluator,
    pending: dict[str, _Pending],
    *,
    meter: UsageMeter,
) -> dict[str, EvaluationResult]:
    outcomes = await asyncio.gather(*(_evaluate_one(evaluator, p) for p in pending.values()))
    evaluated = {key: r for key, r in zip(pending, outcomes, strict=True) if r is not None}
    await _save(session, evaluated, pending)
    for r in evaluated.values():
        meter.add(
            Provider.LLM_TEXT,
            EVALUATE_TOPIC_OPERATION,
            units=r.input_tokens,
            output_units=r.output_tokens,
        )
    return evaluated


def _with_evaluation(
    result: TopicResult, evaluation: TopicEvaluation, topic: TopicInput
) -> TopicResult:
    sent_urls = {p.url for p in topic.pieces}
    fitted = apply_fit(result, evaluation.assessments(), sent_urls=sent_urls)
    return apply_topic_name(fitted, evaluation.topic_name)


async def evaluate_topics(
    session: AsyncSession,
    results: Sequence[TopicResult],
    *,
    answers: Mapping[int, dict[str, Any]],
    evaluator: TopicEvaluator | None,
    meter: UsageMeter,
) -> tuple[list[TopicResult], FitStats]:
    if evaluator is None:
        return list(results), FitStats(0, 0, 0, 0, skipped_reason=SKIPPED_WITHOUT_KEY)
    model = get_settings().llm_model
    inputs = [build_topic_input(r, answers) for r in results]
    keys = [evaluation_cache_key(t, model) for t in inputs]
    cached = await _cached_outputs(session, keys)
    pending = _pending_by_key(results, inputs=inputs, keys=keys, cached=cached)
    evaluated = await _evaluate_pending(session, evaluator, pending, meter=meter)

    outputs = {**cached, **{key: r.output for key, r in evaluated.items()}}
    fitted = [
        _with_evaluation(result, outputs[key], topic) if key in outputs else mark_fit_failed(result)
        for result, topic, key in zip(results, inputs, keys, strict=True)
    ]
    without_evidence = sum(not t.pieces for t in inputs)
    stats = FitStats(
        evaluated=sum(key in evaluated for key in keys),
        cached=sum(key in cached for key in keys),
        failed=sum(key not in outputs for key in keys) - without_evidence,
        without_evidence=without_evidence,
    )
    return fitted, stats
