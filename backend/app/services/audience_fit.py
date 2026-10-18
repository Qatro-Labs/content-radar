"""Audience fit de cada tema con el LLM, cacheado en `llm_evaluations` (CLAUDE.md §7).

Un tema ya evaluado no se vuelve a enviar mientras no cambie su entrada. Si el LLM falla en un
tema, ese tema queda sin fit (null y una limitación) y el resto sigue (plan intel-phase1-llm-fit,
D9). El nombre del tema es siempre el `topic_name` del LLM o el título de una pieza segura.
"""

import asyncio
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import structlog
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
from app.intelligence.audience_fit import (
    apply_fit,
    apply_safe_topic,
    apply_topic_name,
    mark_fit_failed,
)
from app.intelligence.opportunities import TopicResult
from app.schemas.cost import Provider
from app.services.llm_cache import load_cached, save_results

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
    await save_results(
        session,
        evaluated,
        operation=EVALUATE_TOPIC_OPERATION,
        prompt_version=PROMPT_VERSION,
        opportunity_ids={key: p.opportunity_id for key, p in pending.items()},
    )
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
    inputs = [build_topic_input(r, answers) for r in results]
    # Antes del LLM: sin él, o si falla o su nombre no vale, el tema conserva este rótulo.
    results = [apply_safe_topic(r, t.label) for r, t in zip(results, inputs, strict=True)]
    if evaluator is None:
        return results, FitStats(0, 0, 0, 0, skipped_reason=SKIPPED_WITHOUT_KEY)
    model = get_settings().llm_model
    keys = [evaluation_cache_key(t, model) for t in inputs]
    cached = await load_cached(session, keys, TopicEvaluation)
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
