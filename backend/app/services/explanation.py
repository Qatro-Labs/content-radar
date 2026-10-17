"""«Por qué importa» de cada tema con el LLM, cacheado en `llm_evaluations` (CLAUDE.md §7).

Solo se explican los temas con audience fit: la explicación se apoya en sus justificaciones. Si
el LLM falla en un tema, ese tema conserva la plantilla con los datos medidos y una limitación.
"""

import asyncio
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.usage import UsageMeter
from app.core.config import get_settings
from app.editorial.audience import build_topic_input
from app.editorial.evaluator import EvaluationError
from app.editorial.explanation import (
    PROMPT_VERSION,
    Explainer,
    ExplainInput,
    ExplanationResult,
    OpportunityExplanation,
    build_explain_input,
    explanation_cache_key,
    facts_text,
)
from app.intelligence.explanation import (
    ClaimDraft,
    apply_explanation,
    known_numbers,
    mark_explanation_failed,
)
from app.intelligence.opportunities import TopicResult
from app.schemas.cost import Provider
from app.services.llm_cache import load_cached, save_results

log = structlog.get_logger()

EXPLAIN_OPPORTUNITY_OPERATION = "explain_opportunity"
SKIPPED_WITHOUT_KEY = "sin LLM_API_KEY o LLM_MODEL"


@dataclass
class ExplainStats:
    explained: int
    cached: int
    failed: int
    without_fit: int  # sin audience fit no hay justificaciones que explicar
    skipped_reason: str | None = None


@dataclass(frozen=True)
class _Request:
    key: str
    explain: ExplainInput
    opportunity_id: str


async def _explain_one(explainer: Explainer, request: _Request) -> ExplanationResult | None:
    try:
        return await explainer.explain(request.explain)
    except EvaluationError as e:
        log.warning("llm_explain_failed", opportunity_id=request.opportunity_id, error=str(e))
        return None


def _apply(result: TopicResult, explain: ExplainInput, output: OpportunityExplanation):
    texts = [facts_text(explain)] + [f"{p.title} {p.description or ''}" for p in explain.pieces]
    return apply_explanation(
        result,
        [ClaimDraft(c.text, c.evidence_urls) for c in output.claims],
        output.limitations,
        sent_urls={p.url for p in explain.pieces},
        numbers=known_numbers(texts),
    )


async def _explain_pending(
    session: AsyncSession,
    explainer: Explainer,
    pending: dict[str, _Request],
    *,
    meter: UsageMeter,
) -> dict[str, ExplanationResult]:
    outcomes = await asyncio.gather(*(_explain_one(explainer, r) for r in pending.values()))
    explained = {key: r for key, r in zip(pending, outcomes, strict=True) if r is not None}
    await save_results(
        session,
        explained,
        operation=EXPLAIN_OPPORTUNITY_OPERATION,
        prompt_version=PROMPT_VERSION,
        opportunity_ids={key: r.opportunity_id for key, r in pending.items()},
    )
    for r in explained.values():
        meter.add(
            Provider.LLM_TEXT,
            EXPLAIN_OPPORTUNITY_OPERATION,
            units=r.input_tokens,
            output_units=r.output_tokens,
        )
    return explained


async def explain_topics(
    session: AsyncSession,
    results: Sequence[TopicResult],
    *,
    answers: Mapping[int, dict[str, Any]],
    explainer: Explainer | None,
    meter: UsageMeter,
) -> tuple[list[TopicResult], ExplainStats]:
    if explainer is None:
        return list(results), ExplainStats(0, 0, 0, 0, skipped_reason=SKIPPED_WITHOUT_KEY)
    model = get_settings().llm_model
    requests: dict[int, _Request] = {}
    for i, result in enumerate(results):
        topic = build_topic_input(result, answers)
        if result.opportunity.audience_fit_criteria and topic.pieces:
            explain = build_explain_input(result, topic)
            key = explanation_cache_key(explain, model)
            requests[i] = _Request(key, explain, result.opportunity.id)
    keys = [r.key for r in requests.values()]
    cached = await load_cached(session, keys, OpportunityExplanation)
    pending = {r.key: r for r in requests.values() if r.key not in cached}
    explained = await _explain_pending(session, explainer, pending, meter=meter)

    outputs = {**cached, **{key: r.output for key, r in explained.items()}}
    final = []
    for i, result in enumerate(results):
        request = requests.get(i)
        if request is None:
            final.append(result)
        elif request.key in outputs:
            final.append(_apply(result, request.explain, outputs[request.key]))
        else:
            final.append(mark_explanation_failed(result))
    stats = ExplainStats(
        explained=sum(r.key in explained for r in requests.values()),
        cached=sum(r.key in cached for r in requests.values()),
        failed=sum(r.key not in outputs for r in requests.values()),
        without_fit=len(results) - len(requests),
    )
    return final, stats
