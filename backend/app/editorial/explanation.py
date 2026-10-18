"""Entrada y salida de `explain_opportunity` (CLAUDE.md §7): «por qué importa» de cada tema.

Corre después del audience fit y de la recomendación, para que el texto explique lo que ya
calculó Python. Como en `audience.py`, el texto externo va solo en el mensaje del usuario y
escapado (regla 6).
"""

import asyncio
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

from anthropic import AsyncAnthropic
from pydantic import BaseModel

from app.core.config import Settings
from app.editorial.audience import EvidencePiece, TopicInput, escape, evidence_block
from app.editorial.evaluator import LLM_CONCURRENCY, LlmResult, StructuredLlm
from app.intelligence.opportunities import TopicResult
from app.schemas.opportunity import (
    Opportunity,
    OpportunityTimeline,
    Recommendation,
    TimelineWindow,
)

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
PROMPT_VERSION = 1
PROMPT_FILE = PROMPTS_DIR / f"explain_opportunity.v{PROMPT_VERSION}.md"

# Bandas del audience fit para el texto, como las muestra la UI (CLAUDE.md §7).
FIT_BAND_MEDIUM = 40
FIT_BAND_HIGH = 60
# La aceleración cambia en cada ejecución: redondeada a decenas, la caché sirve entre ejecuciones
# cercanas y el texto no presume una precisión que no hay.
ACCELERATION_ROUNDING = -1
MIX_ROUNDING = -1

LIFECYCLE_TEXT = {
    "emerging": "emergente",
    "accelerating": "en aceleración",
    "peaking": "en su pico",
    "saturated": "saturado",
    "unknown": "sin etapa clara",
}
RECOMMENDATION_TEXT = {
    Recommendation.PUBLISH_NOW: "publicar ya",
    Recommendation.FIND_ANGLE: "buscar un ángulo propio",
    Recommendation.WAIT_FOR_CASE: "esperar a que haya un caso real",
    Recommendation.DISCARD: "descartar",
}
LATAM_GAP_TEXT = {
    True: "baja: el tema todavía no se cubre en fuentes latinoamericanas (posible oportunidad)",
    False: "alta: el tema ya se cubre en fuentes latinoamericanas",
    # Hay datos: falta conversación sobre su uso en empresas, o la cobertura regional es parcial.
    None: "sin decidir: casi no se habla de su uso en empresas, o la cobertura en fuentes "
    "latinoamericanas es parcial",
}


class Claim(BaseModel):
    text: str
    # str y no HttpUrl: una URL mal copiada se descarta sola, sin invalidar toda la respuesta.
    evidence_urls: list[str]


class OpportunityExplanation(BaseModel):
    claims: list[Claim]
    limitations: list[str]


@dataclass(frozen=True)
class FitNote:
    criterion: str
    level: int
    justification: str


@dataclass(frozen=True)
class ExplainInput:
    label: str
    facts: list[str]
    fit: list[FitNote]
    pieces: list[EvidencePiece]


def _fit_band(score: float) -> str:
    if score >= FIT_BAND_HIGH:
        return "alto"
    return "medio" if score >= FIT_BAND_MEDIUM else "bajo"


def _window_counts(timeline: OpportunityTimeline) -> tuple[int, int]:
    points = timeline.points
    current = sum(p.count for p in points if p.window is TimelineWindow.CURRENT)
    previous = sum(p.count for p in points if p.window is TimelineWindow.PREVIOUS)
    return current, previous


# Lo usan también los briefs. Cambiar el texto cambia la clave de caché de todas las
# explicaciones: el siguiente `analyze` volvería a pagar todos los temas.
def opportunity_facts(o: Opportunity, timeline: OpportunityTimeline) -> list[str]:
    current, previous = _window_counts(timeline)
    acceleration = round(o.acceleration * 100, ACCELERATION_ROUNDING)
    mix = {k: round(v * 100, MIX_ROUNDING) for k, v in o.audience_mix.model_dump().items()}
    facts = [
        f"Etapa: {LIFECYCLE_TEXT[o.lifecycle.value]} ({o.lifecycle_reason}).",
        f"Piezas publicadas: {current} en los últimos 3 días y {previous} en los 3 anteriores.",
        f"Aceleración ajustada por volumen: {acceleration:+.0f} %.",
        f"Fuentes independientes: {o.source_count}.",
        f"Piezas que rinden al menos 3 veces su referencia: {o.outlier_count}.",
        f"Audiencia de las fuentes: tecnología {mix['tech']:.0f} %, negocio "
        f"{mix['business']:.0f} %, en español {mix['latam_es']:.0f} %.",
        f"Cobertura en fuentes latinoamericanas: {LATAM_GAP_TEXT[o.latam_gap]}.",
        f"Recomendación: {RECOMMENDATION_TEXT[o.recommendation]}. {o.recommendation_reason or ''}",
    ]
    if o.audience_fit_score is not None:
        facts.append(f"Encaje con la audiencia de 30X: {_fit_band(o.audience_fit_score)}.")
    return facts


def fit_notes(o: Opportunity) -> list[FitNote]:
    return [
        FitNote(c.criterion.value, c.level, c.justification) for c in o.audience_fit_criteria or []
    ]


def build_explain_input(result: TopicResult, topic: TopicInput) -> ExplainInput:
    return ExplainInput(
        label=topic.label,
        facts=opportunity_facts(result.opportunity, result.timeline),
        fit=fit_notes(result.opportunity),
        pieces=topic.pieces,
    )


def system_prompt() -> str:
    return PROMPT_FILE.read_text(encoding="utf-8")


def facts_text(explain: ExplainInput) -> str:
    return "\n".join(explain.facts)


def fit_lines(notes: list[FitNote]) -> str:
    return "\n".join(f"- {n.criterion} (nivel {n.level}): {escape(n.justification)}" for n in notes)


def user_message(explain: ExplainInput) -> str:
    fit = fit_lines(explain.fit)
    evidence = "\n".join(evidence_block(i, p) for i, p in enumerate(explain.pieces, start=1))
    return (
        f"<topic_label>{escape(explain.label)}</topic_label>\n"
        f"<facts>\n{facts_text(explain)}\n</facts>\n"
        f"<fit>\n{fit}\n</fit>\n{evidence}"
    )


def explanation_cache_key(explain: ExplainInput, model: str) -> str:
    payload = {
        "input": asdict(explain),
        "prompt_version": PROMPT_VERSION,
        "prompt_sha256": hashlib.sha256(PROMPT_FILE.read_bytes()).hexdigest(),
        "model": model,
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


ExplanationResult = LlmResult[OpportunityExplanation]


class Explainer(Protocol):
    async def explain(self, explain: ExplainInput) -> ExplanationResult: ...


class AnthropicExplainer:
    def __init__(self, llm: StructuredLlm) -> None:
        self._llm = llm

    async def explain(self, explain: ExplainInput) -> ExplanationResult:
        return await self._llm.complete(
            system=system_prompt(), user=user_message(explain), output_type=OpportunityExplanation
        )


def build_explainer(settings: Settings) -> Explainer | None:
    if not settings.llm_api_key or not settings.llm_model:
        return None
    client = AsyncAnthropic(api_key=settings.llm_api_key)
    return AnthropicExplainer(
        StructuredLlm(client, settings.llm_model, asyncio.Semaphore(LLM_CONCURRENCY))
    )
