"""«Por qué importa» de cada tema con el LLM, cacheado en `llm_evaluations` (CLAUDE.md §7).

Solo se explican los temas con audience fit: la explicación se apoya en sus justificaciones. Si
el LLM falla en un tema, ese tema conserva la plantilla con los datos medidos y una limitación.
Con `JEV_VERIFY_CLAIMS`, Jev verifica cada afirmación que pasó las comprobaciones de Python y solo
se publica lo que respalda (`services.verification`).
"""

import asyncio
from collections import defaultdict
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
    UNVERIFIED_NOTE,
    ClaimDraft,
    apply_explanation,
    compose_explanation,
    jev_drop_note,
    known_numbers,
    mark_explanation_failed,
    python_checked,
    python_drop_note,
)
from app.intelligence.jev import CitedEvidence, claim_state
from app.intelligence.opportunities import TopicResult, rank
from app.schemas.cost import Provider
from app.services.llm_cache import load_cached, save_results
from app.services.verification import (
    ClaimCheck,
    ClaimVerifier,
    VerifyStats,
    claim_cache_key,
    verify_claims,
)

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
    verification: VerifyStats | None = None  # None: JEV_VERIFY_CLAIMS apagado


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


@dataclass(frozen=True)
class _Ready:
    explain: ExplainInput
    output: OpportunityExplanation

    @property
    def drafts(self) -> list[ClaimDraft]:
        return [ClaimDraft(c.text, c.evidence_urls) for c in self.output.claims]

    @property
    def sent_urls(self) -> set[str]:
        return {p.url for p in self.explain.pieces}

    @property
    def numbers(self) -> set[str]:
        pieces = [f"{p.title} {p.description or ''}" for p in self.explain.pieces]
        return known_numbers([facts_text(self.explain), *pieces])


def _apply(result: TopicResult, ready: _Ready) -> TopicResult:
    return apply_explanation(
        result,
        ready.drafts,
        ready.output.limitations,
        sent_urls=ready.sent_urls,
        numbers=ready.numbers,
    )


def _cited_evidence(claim: ClaimDraft, explain: ExplainInput) -> list[CitedEvidence]:
    # Las mismas URLs que acepta `python_checked`, sin repetir y en el orden de cita.
    by_url = {p.url: p for p in explain.pieces}
    cited = [by_url[u] for u in dict.fromkeys(claim.cited_urls) if u in by_url]
    return [CitedEvidence(p.source, p.title, p.description) for p in cited]


def _topic_checks(topic_index: int, ready: _Ready) -> list[ClaimCheck]:
    valid = python_checked(ready.drafts, sent_urls=ready.sent_urls, numbers=ready.numbers)
    facts = ready.explain.facts
    return [
        ClaimCheck(
            topic_index,
            c,
            claim_state(c.text, facts=facts, evidence=_cited_evidence(c, ready.explain)),
        )
        for c in valid
    ]


def _claim_checks(results: Sequence[TopicResult], ready: Mapping[int, _Ready]) -> list[ClaimCheck]:
    # En el orden de `rank()` solo para repartir el presupuesto de Jev; por identidad porque dos
    # TopicResult pueden ser iguales.
    position = {id(r): i for i, r in enumerate(results)}
    indices = [position[id(r)] for r in rank(results)]
    return [check for i in indices if i in ready for check in _topic_checks(i, ready[i])]


def _apply_verified(
    result: TopicResult,
    ready: _Ready,
    checks: Sequence[ClaimCheck],
    verdicts: Mapping[str, bool | None],
) -> TopicResult:
    valid = [c.claim for c in checks]
    python_note = python_drop_note(len(ready.drafts) - len(valid))
    topic_verdicts = [verdicts[claim_cache_key(c.state)] for c in checks]
    # Un tema se verifica entero o queda «no verificado»: mezclar frases verificadas y no
    # verificadas en el mismo texto presentaría como verificado lo que no lo está.
    if any(v is None for v in topic_verdicts):
        published, jev_note = valid, UNVERIFIED_NOTE
    else:
        published = [c for c, v in zip(valid, topic_verdicts, strict=True) if v]
        jev_note = jev_drop_note(len(valid) - len(published))
    return compose_explanation(
        result,
        published,
        ready.output.limitations,
        numbers=ready.numbers,
        notes=[python_note, jev_note],
    )


async def _verify_and_apply(
    session: AsyncSession,
    results: Sequence[TopicResult],
    ready: Mapping[int, _Ready],
    *,
    verifier: ClaimVerifier,
    meter: UsageMeter,
) -> tuple[dict[int, TopicResult], VerifyStats]:
    checks = _claim_checks(results, ready)
    verdicts, stats = await verify_claims(session, checks, verifier=verifier, meter=meter)
    by_topic: defaultdict[int, list[ClaimCheck]] = defaultdict(list)
    for check in checks:
        by_topic[check.topic_index].append(check)
    applied = {i: _apply_verified(results[i], r, by_topic[i], verdicts) for i, r in ready.items()}
    return applied, stats


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
    verifier: ClaimVerifier | None = None,
) -> tuple[list[TopicResult], ExplainStats]:
    if explainer is None:
        return list(results), ExplainStats(0, 0, 0, 0, skipped_reason=SKIPPED_WITHOUT_KEY)
    requests = _requests(results, answers, get_settings().llm_model)
    keys = [r.key for r in requests.values()]
    cached = await load_cached(session, keys, OpportunityExplanation)
    pending = {r.key: r for r in requests.values() if r.key not in cached}
    explained = await _explain_pending(session, explainer, pending, meter=meter)

    outputs = {**cached, **{key: r.output for key, r in explained.items()}}
    ready = {i: _Ready(r.explain, outputs[r.key]) for i, r in requests.items() if r.key in outputs}
    verification = None
    if verifier is None:
        applied = {i: _apply(results[i], r) for i, r in ready.items()}
    else:
        applied, verification = await _verify_and_apply(
            session, results, ready, verifier=verifier, meter=meter
        )
    final = [_final(i, result, requests, applied) for i, result in enumerate(results)]
    stats = ExplainStats(
        explained=sum(r.key in explained for r in requests.values()),
        cached=sum(r.key in cached for r in requests.values()),
        failed=sum(r.key not in outputs for r in requests.values()),
        without_fit=len(results) - len(requests),
        verification=verification,
    )
    return final, stats


def _requests(
    results: Sequence[TopicResult], answers: Mapping[int, dict[str, Any]], model: str
) -> dict[int, _Request]:
    requests: dict[int, _Request] = {}
    for i, result in enumerate(results):
        topic = build_topic_input(result, answers)
        if result.opportunity.audience_fit_criteria and topic.pieces:
            explain = build_explain_input(result, topic)
            key = explanation_cache_key(explain, model)
            requests[i] = _Request(key, explain, result.opportunity.id)
    return requests


def _final(
    i: int,
    result: TopicResult,
    requests: Mapping[int, _Request],
    applied: Mapping[int, TopicResult],
) -> TopicResult:
    if i in applied:
        return applied[i]
    # Pedido al LLM y sin salida: falló.
    return mark_explanation_failed(result) if i in requests else result
