"""Brief editorial de una oportunidad servida, cacheado en `llm_evaluations` (CLAUDE.md §6).

Lo usan `POST /editorial/brief` y la tool MCP `generate_editorial_brief`. Lee la
oportunidad de la ejecución servida (DEMO_RUN_ID o la última correcta) y solo manda al LLM texto de
piezas que Jev marcó como seguras, igual que el audience fit (regla 6).
"""

from dataclasses import dataclass
from datetime import datetime

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.usage import UsageMeter
from app.core.config import get_settings
from app.editorial.audience import MAX_PIECES, evidence_piece, safe_label
from app.editorial.briefs import (
    PROMPT_VERSION,
    BriefDraft,
    Briefer,
    BriefInput,
    BriefResult,
    brief_cache_key,
    request_text,
)
from app.editorial.evaluator import EvaluationError
from app.editorial.explanation import fit_notes, opportunity_facts
from app.intelligence.audience_fit import EDITORIAL_PENDING_NOTE
from app.intelligence.briefs import BriefDraftParts, CheckedBrief, check_brief
from app.intelligence.explanation import (
    EXPLANATION_FAILED_NOTE,
    NO_VALID_CLAIM_NOTE,
    VERIFICATION_INCOMPLETE_NOTE,
    ClaimDraft,
    known_numbers,
)
from app.intelligence.jev import excluded_from_llm
from app.intelligence.opportunities import Piece
from app.schemas.cost import Provider
from app.schemas.editorial import BriefPoint, BriefRequest, EditorialBrief
from app.schemas.opportunity import Evidence
from app.services.classification import load_judgments
from app.services.costs import record_meter
from app.services.llm_cache import load_cached, save_results
from app.services.opportunities import ServedOpportunity, get_served, load_evidence_pieces

log = structlog.get_logger()

EDITORIAL_BRIEF_OPERATION = "editorial_brief"
# El prompt pide el ángulo "de 30X": el 30 de la marca no es una cifra inventada.
BRAND_NAME = "30X"
# `explain_opportunity` solo corre con audience fit; con fit y alguna de estas notas,
# `why_it_matters` sigue siendo la plantilla y no un texto comprobado.
UNCHECKED_EXPLANATION_NOTES = {
    EDITORIAL_PENDING_NOTE,
    EXPLANATION_FAILED_NOTE,
    NO_VALID_CLAIM_NOTE,
    VERIFICATION_INCOMPLETE_NOTE,
}


class BriefError(Exception):
    """El mensaje se puede mostrar al usuario: nunca lleva texto de la evidencia."""


class OpportunityNotFound(BriefError):
    pass


class BriefUnavailable(BriefError):
    pass


class NoSafeEvidence(BriefError):
    pass


class BriefFailed(BriefError):
    pass


@dataclass(frozen=True)
class _Prepared:
    served: ServedOpportunity
    brief: BriefInput
    evidence_by_url: dict[str, Evidence]


async def _safe_pieces(
    session: AsyncSession, served: ServedOpportunity, now: datetime
) -> list[tuple[Piece, Evidence]]:
    found = await load_evidence_pieces(session, served.evidence, as_of=now)
    answers = await load_judgments(session, [p for p, _ in found])
    safe = [(p, e) for p, e in found if not excluded_from_llm(answers.get(p.item_id, {}))]
    return safe[:MAX_PIECES]


async def _prepare(session: AsyncSession, request: BriefRequest, now: datetime) -> _Prepared:
    served = await get_served(session, request.opportunity_id)
    if served is None:
        raise OpportunityNotFound("Oportunidad no encontrada")
    safe = await _safe_pieces(session, served, now)
    if not safe:
        raise NoSafeEvidence("Esta oportunidad no tiene piezas comprobadas para escribir un brief")
    o = served.opportunity
    platform, goal, fmt = request_text(request.platform, request.goal, request.format)
    checked_why = bool(o.audience_fit_criteria) and not UNCHECKED_EXPLANATION_NOTES & set(
        o.limitations
    )
    brief = BriefInput(
        platform=platform,
        goal=goal,
        format=fmt,
        # El nombre del tema puede ser el título de una pieza que Jev no marcó como segura.
        label=safe_label(o.topic, [p for p, _ in safe]),
        facts=opportunity_facts(o, served.timeline),
        why_it_matters=o.why_it_matters if checked_why else None,
        fit=fit_notes(o),
        pieces=[evidence_piece(p) for p, _ in safe],
    )
    return _Prepared(served, brief, {p.url: e for p, e in safe})


async def _draft(
    session: AsyncSession, prepared: _Prepared, *, briefer: Briefer, meter: UsageMeter
) -> tuple[str, BriefDraft, BriefResult | None]:
    key = brief_cache_key(prepared.brief, get_settings().llm_model)
    if cached := (await load_cached(session, [key], BriefDraft)).get(key):
        return key, cached, None
    try:
        result = await briefer.write(prepared.brief)
    except EvaluationError as e:
        log.warning("llm_brief_failed", opportunity_id=prepared.served.opportunity.id, error=str(e))
        raise BriefFailed("No se pudo generar el brief; inténtalo de nuevo") from e
    meter.add(
        Provider.LLM_TEXT,
        EDITORIAL_BRIEF_OPERATION,
        units=result.input_tokens,
        output_units=result.output_tokens,
    )
    return key, result.output, result


def _check(prepared: _Prepared, draft: BriefDraft) -> CheckedBrief | None:
    b = prepared.brief
    texts = [*b.facts, b.why_it_matters or "", b.platform, b.goal, b.format, BRAND_NAME]
    texts += [f"{p.title} {p.description or ''}" for p in b.pieces]
    parts = BriefDraftParts(
        angle=draft.angle,
        hook=draft.hook,
        structure=draft.structure,
        key_points=[ClaimDraft(c.text, c.evidence_urls) for c in draft.key_points],
        why_it_fits=ClaimDraft(draft.why_it_fits.text, draft.why_it_fits.evidence_urls),
        limitations=draft.limitations,
    )
    return check_brief(parts, sent_urls=set(prepared.evidence_by_url), numbers=known_numbers(texts))


def _cited_evidence(checked: CheckedBrief, by_url: dict[str, Evidence]) -> list[Evidence]:
    claims = [*checked.key_points, *([checked.why_it_fits] if checked.why_it_fits else [])]
    cited = {u for c in claims for u in c.cited_urls}
    return [e for url, e in by_url.items() if url in cited]


def _to_brief(request: BriefRequest, prepared: _Prepared, checked: CheckedBrief) -> EditorialBrief:
    o = prepared.served.opportunity
    points = [
        BriefPoint.model_validate({"text": p.text, "evidence_urls": p.cited_urls})
        for p in checked.key_points
    ]
    return EditorialBrief(
        opportunity_id=o.id,
        topic=o.topic,
        platform=request.platform,
        goal=request.goal,
        format=request.format,
        recommendation=o.recommendation,
        recommendation_reason=o.recommendation_reason,
        angle=checked.angle,
        hook=checked.hook,
        structure=checked.structure,
        key_points=points,
        why_it_fits=checked.why_it_fits.text if checked.why_it_fits else None,
        evidence=_cited_evidence(checked, prepared.evidence_by_url),
        limitations=checked.limitations,
        model=get_settings().llm_model,
    )


async def generate_brief(
    session: AsyncSession,
    request: BriefRequest,
    *,
    briefer: Briefer | None,
    meter: UsageMeter,
    now: datetime,
) -> EditorialBrief:
    """`BriefError` con un mensaje para el usuario si no hay brief que dar."""
    if briefer is None:
        raise BriefUnavailable("Los briefs no están disponibles: falta configurar el LLM")
    prepared = await _prepare(session, request, now)
    key, draft, fresh = await _draft(session, prepared, briefer=briefer, meter=meter)
    checked = _check(prepared, draft)
    if checked is None:
        raise BriefFailed("El brief generado no superó la comprobación de evidencia")
    if fresh is not None:
        # Solo se cachea lo que pasó la comprobación: un brief rechazado se puede volver a pedir.
        await save_results(
            session,
            {key: fresh},
            operation=EDITORIAL_BRIEF_OPERATION,
            prompt_version=PROMPT_VERSION,
            opportunity_ids={key: prepared.served.opportunity.id},
        )
    return _to_brief(request, prepared, checked)


async def generate_metered_brief(
    session: AsyncSession,
    request: BriefRequest,
    *,
    briefer: Briefer | None,
    now: datetime,
) -> EditorialBrief:
    """`generate_brief` con su consumo del LLM registrado en `usage_events`, falle o no."""
    meter = UsageMeter()
    try:
        return await generate_brief(session, request, briefer=briefer, meter=meter, now=now)
    finally:
        # El LLM cobra aunque el brief no supere la comprobación.
        if meter.counts:
            await record_meter(session, meter)
