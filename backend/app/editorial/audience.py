"""Entrada del LLM para el audience fit de un tema (CLAUDE.md §7) y su salida validada.

El texto de las piezas es externo y no confiable (regla 6): va solo en el mensaje del usuario,
escapado dentro de bloques delimitados. El system prompt solo lleva texto nuestro (instrucciones,
rúbrica y perfil).
"""

import hashlib
import html
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from app.intelligence.audience_fit import MAX_LEVEL, CriterionAssessment
from app.intelligence.jev import PieceJudgment, excluded_from_llm, to_piece_judgment
from app.intelligence.opportunities import Piece, TopicResult
from app.schemas.opportunity import FitCriterion

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
PROMPT_VERSION = 2
PROMPT_FILE = PROMPTS_DIR / f"evaluate_topic.v{PROMPT_VERSION}.md"
RUBRIC_FILE = PROMPTS_DIR / "audience_fit_rubric.v1.yaml"
PROFILE_FILE = Path(__file__).resolve().parents[3] / "data" / "audiences" / "30x.yaml"

MAX_PIECES = 10
MAX_DESCRIPTION_CHARS = 500
MIX_DECIMALS = 2  # el mix redondeado no cambia la clave de caché por ruido entre ejecuciones

# Pistas de Jev que recibe el LLM, con el texto que las describe (batería piece.v2).
HINTS = {
    "business_use": "tratan del uso, la adopción o el impacto de la IA en organizaciones",
    "business_case": "describen cómo una organización concreta usa la IA",
    "dev_audience": "se dirigen sobre todo a desarrolladores o investigadores",
    "tech_jargon": "usan jerga técnica de software o de IA",
    "latam_context": "mencionan Latinoamérica o un país, empresa o persona de la región",
    "launch": "anuncian un producto, modelo, función o versión nueva",
}


class CriterionOutput(BaseModel):
    # Justificación antes que nivel: el modelo genera en este orden y razona antes de puntuar.
    justification: str
    # str y no HttpUrl: una URL mal copiada se descarta sola, sin invalidar toda la respuesta.
    evidence_urls: list[str]
    level: int = Field(ge=0, le=MAX_LEVEL)


class TopicEvaluation(BaseModel):
    """Salida estructurada del LLM: un campo por `FitCriterion`, así no puede faltar ninguno."""

    business_impact: CriterionOutput
    org_application: CriterionOutput
    exec_readability: CriterionOutput
    latam_relevance: CriterionOutput
    pillar_fit: CriterionOutput
    actionable_content: CriterionOutput
    # Al final: el nombre sale de haber leído la evidencia para los seis criterios.
    topic_name: str

    def assessments(self) -> list[CriterionAssessment]:
        return [
            CriterionAssessment(
                criterion=c,
                justification=(out := getattr(self, c.value)).justification,
                # El modelo puede devolver la URL tal como la vio, con el escapado del bloque.
                cited_urls=[html.unescape(u) for u in out.evidence_urls],
                level=out.level,
            )
            for c in FitCriterion
        ]


@dataclass(frozen=True)
class EvidencePiece:
    url: str
    source: str
    platform: str
    language: str | None
    title: str
    description: str | None


@dataclass(frozen=True)
class HintCount:
    hint: str
    yes: int
    classified: int  # sí + no; lo incierto o sin clasificar no cuenta
    unclassified: int


@dataclass(frozen=True)
class TopicInput:
    label: str
    audience_mix: dict[str, float]
    hints: list[HintCount]
    formats: dict[str, int]
    unclassified_formats: int
    pieces: list[EvidencePiece]


def evidence_piece(p: Piece) -> EvidencePiece:
    return EvidencePiece(
        url=p.url,
        source=p.source_name,
        platform=p.platform.value,
        language=p.language,
        title=p.title,
        description=p.description[:MAX_DESCRIPTION_CHARS] if p.description else None,
    )


def _hint_counts(judgments: Sequence[PieceJudgment | None]) -> list[HintCount]:
    counts = []
    for hint in HINTS:
        values = [getattr(j, hint) if j else None for j in judgments]
        classified = sum(v is not None for v in values)
        counts.append(
            HintCount(hint, sum(v is True for v in values), classified, len(values) - classified)
        )
    return counts


def safe_label(label: str, safe: Sequence[Piece]) -> str:
    # El rótulo es el título de la pieza representativa: si esa pieza no es segura, no entra en
    # el prompt y se rotula con la primera pieza segura (regla 6).
    if any(p.title == label for p in safe):
        return label
    return safe[0].title if safe else ""


def build_topic_input(result: TopicResult, answers: Mapping[int, dict[str, Any]]) -> TopicInput:
    """Piezas en el orden de la evidencia, sin las que Jev no marca como seguras."""
    judgments = [
        to_piece_judgment(p.item_id, answers[p.item_id]) if p.item_id in answers else None
        for p in result.pieces
    ]
    safe = [p for p in result.pieces if not excluded_from_llm(answers.get(p.item_id, {}))]
    formats = Counter(j.format for j in judgments if j and j.format)
    mix = result.opportunity.audience_mix.model_dump()
    return TopicInput(
        label=safe_label(result.opportunity.topic, safe),
        audience_mix={k: round(v, MIX_DECIMALS) for k, v in mix.items()},
        hints=_hint_counts(judgments),
        formats=dict(sorted(formats.items())),
        unclassified_formats=len(judgments) - formats.total(),
        pieces=[evidence_piece(p) for p in safe[:MAX_PIECES]],
    )


@lru_cache
def rubric() -> dict[str, Any]:
    return yaml.safe_load(RUBRIC_FILE.read_text(encoding="utf-8"))


@lru_cache
def profile_text() -> str:
    return PROFILE_FILE.read_text(encoding="utf-8")


def _rubric_text() -> str:
    blocks = []
    for c in rubric()["criteria"]:
        levels = "\n".join(f"  - {n}: {text}" for n, text in c["levels"].items())
        blocks.append(f"### `{c['id']}` · {c['name']}\n\n{c['question']}\n\n{levels}")
    return "\n\n".join(blocks)


@lru_cache
def system_prompt() -> str:
    template = PROMPT_FILE.read_text(encoding="utf-8")
    return template.replace("{{rubric}}", _rubric_text()).replace("{{profile}}", profile_text())


def escape(text: str) -> str:
    return html.escape(text, quote=True)


def evidence_block(index: int, p: EvidencePiece) -> str:
    attrs = (
        f'id="{index}" url="{escape(p.url)}" source="{escape(p.source)}" '
        f'platform="{p.platform}" language="{escape(p.language or "")}"'
    )
    description = escape(p.description) if p.description else "(sin descripción)"
    return (
        f"<evidence {attrs}>\n<title>{escape(p.title)}</title>\n"
        f"<description>{description}</description>\n</evidence>"
    )


def _hints_block(topic: TopicInput) -> str:
    lines = [
        f"- {h.yes} de {h.classified} piezas clasificadas {HINTS[h.hint]} "
        f"({h.unclassified} inciertas o sin clasificar)."
        for h in topic.hints
    ]
    formats = ", ".join(f"{name} {n}" for name, n in topic.formats.items()) or "ninguno"
    unclassified = topic.unclassified_formats
    lines.append(f"- Formatos: {formats} ({unclassified} inciertos o sin clasificar).")
    return "\n".join(lines)


def user_message(topic: TopicInput) -> str:
    mix = topic.audience_mix
    evidence = "\n".join(evidence_block(i, p) for i, p in enumerate(topic.pieces, start=1))
    return (
        f"<topic_label>{escape(topic.label)}</topic_label>\n"
        f"<audience_mix>tecnología {mix['tech']:.0%} · negocio {mix['business']:.0%} · "
        f"en español {mix['latam_es']:.0%}</audience_mix>\n"
        f"<jev_hints>\n{_hints_block(topic)}\n</jev_hints>\n{evidence}"
    )


def evaluation_cache_key(topic: TopicInput, model: str) -> str:
    payload = {
        "input": asdict(topic),
        "prompt_version": PROMPT_VERSION,
        # Hash y no solo la versión: editar la rúbrica sin subir la versión dejaría la caché vieja.
        "rubric_sha256": hashlib.sha256(RUBRIC_FILE.read_bytes()).hexdigest(),
        "profile_sha256": hashlib.sha256(profile_text().encode("utf-8")).hexdigest(),
        "model": model,
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
