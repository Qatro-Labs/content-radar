"""Audience fit (CLAUDE.md §7): el LLM pone un nivel 0–5 por criterio y Python lo combina.

Aquí no hay LLM ni DB: entran los niveles ya validados y salen los scores, el desglose del
Opportunity Score y la recomendación (regla 4).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from pydantic import HttpUrl

from app.intelligence.opportunities import LLM_PENDING_NOTE, TopicResult
from app.intelligence.ranking import recommendation, score_breakdown
from app.schemas.opportunity import AudienceFitCriterion, FitCriterion

MAX_LEVEL = 5
# Pesos iguales hasta que la validación con temas etiquetados justifique otros
# (plan intel-phase1-llm-fit, D6).
CRITERION_WEIGHTS: dict[FitCriterion, float] = dict.fromkeys(FitCriterion, 1.0)
SCORE_DECIMALS = 1

FIT_FAILED_NOTE = "No se pudo evaluar el encaje con la audiencia."
EDITORIAL_PENDING_NOTE = (
    "Análisis editorial pendiente: «por qué importa» es una plantilla con los datos medidos."
)


@dataclass(frozen=True)
class CriterionAssessment:
    criterion: FitCriterion
    justification: str
    cited_urls: list[str]  # tal cual las da el LLM: `apply_fit` quita las que no son del tema
    level: int


def _to_score(level: float) -> float:
    return round(level / MAX_LEVEL * 100, SCORE_DECIMALS)


def audience_fit_score(levels: Mapping[FitCriterion, int]) -> float:
    total_weight = sum(CRITERION_WEIGHTS.values())
    mean = sum(CRITERION_WEIGHTS[c] * levels[c] for c in FitCriterion) / total_weight
    return _to_score(mean)


def actionability_score(levels: Mapping[FitCriterion, int]) -> float:
    return _to_score(levels[FitCriterion.ACTIONABLE_CONTENT])


def _criteria(
    assessments: Sequence[CriterionAssessment], topic_urls: set[str]
) -> tuple[list[AudienceFitCriterion], int]:
    criteria, dropped = [], 0
    for a in sorted(assessments, key=lambda a: list(FitCriterion).index(a.criterion)):
        valid = [u for u in a.cited_urls if u in topic_urls]
        dropped += len(a.cited_urls) - len(valid)
        criteria.append(
            AudienceFitCriterion(
                criterion=a.criterion,
                justification=a.justification,
                evidence_urls=[HttpUrl(u) for u in valid],
                level=a.level,
            )
        )
    return criteria, dropped


def _limitations(notes: list[str], replacement: str, *, dropped_citations: int) -> list[str]:
    kept = [replacement if n == LLM_PENDING_NOTE else n for n in notes]
    if dropped_citations:
        citations = "1 cita" if dropped_citations == 1 else f"{dropped_citations} citas"
        kept.append(f"Se descartaron {citations} del LLM a evidencias que no son de este tema.")
    return kept


def apply_fit(result: TopicResult, assessments: Sequence[CriterionAssessment]) -> TopicResult:
    o = result.opportunity
    levels = {a.criterion: a.level for a in assessments}
    fit, action = audience_fit_score(levels), actionability_score(levels)
    criteria, dropped = _criteria(assessments, {p.url for p in result.pieces})
    breakdown = score_breakdown(
        momentum=o.momentum_score,
        audience_fit=fit,
        cross_source=o.cross_source_score,
        saturation=o.saturation_score,
        actionability=action,
        source_count=o.source_count,
        item_count=len(result.pieces),
    )
    opportunity = o.model_copy(
        update={
            "audience_fit_score": fit,
            "audience_fit_criteria": criteria,
            "actionability_score": action,
            "score_breakdown": breakdown,
            "opportunity_score": None if breakdown is None else breakdown.total,
            "recommendation": recommendation(result.stage, o.confidence, fit),
            "limitations": _limitations(
                o.limitations, EDITORIAL_PENDING_NOTE, dropped_citations=dropped
            ),
        }
    )
    return replace(result, opportunity=opportunity)


def mark_fit_failed(result: TopicResult) -> TopicResult:
    o = result.opportunity
    notes = _limitations(o.limitations, FIT_FAILED_NOTE, dropped_citations=0)
    return replace(result, opportunity=o.model_copy(update={"limitations": notes}))
