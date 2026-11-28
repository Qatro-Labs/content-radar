"""Entrada y salida del brief editorial (CLAUDE.md §6, `POST /editorial/brief`).

Como en `explanation.py`, el texto externo va solo en el mensaje del usuario y escapado
(regla 6). El perfil de marca también: lo escribe una persona del equipo, así que va como dato
delimitado en el mensaje del usuario y nunca en el system prompt.
"""

import asyncio
import hashlib
import json
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from anthropic import AsyncAnthropic
from pydantic import BaseModel

from app.core.config import Settings
from app.editorial.audience import EvidencePiece, escape, evidence_block
from app.editorial.evaluator import LLM_CONCURRENCY, LlmResult, StructuredLlm
from app.editorial.explanation import Claim, FitNote, fit_lines
from app.schemas.editorial import BriefFormat, BriefGoal, BriefPlatform
from app.schemas.profile import RadarProfile

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
PROMPT_VERSION = 2
PROMPT_FILE = PROMPTS_DIR / f"editorial_brief.v{PROMPT_VERSION}.md"

PLATFORM_TEXT = {
    BriefPlatform.LINKEDIN: "LinkedIn",
    BriefPlatform.INSTAGRAM: "Instagram",
    BriefPlatform.YOUTUBE: "YouTube",
    BriefPlatform.NEWSLETTER: "newsletter por correo",
}
GOAL_TEXT = {
    BriefGoal.EDUCATE: "educar: que el directivo entienda qué cambia y qué hacer",
    BriefGoal.SPARK_CONVERSATION: "abrir conversación: que el directivo opine y comparta su caso",
    BriefGoal.GENERATE_LEADS: "captar clientes: que el directivo quiera saber más de 30X",
}
FORMAT_TEXT = {
    BriefFormat.POST: "post de texto",
    BriefFormat.CAROUSEL: "carrusel de imágenes",
    BriefFormat.SHORT_VIDEO: "vídeo corto (reel o short)",
    BriefFormat.LONG_VIDEO: "vídeo largo",
    BriefFormat.ARTICLE: "artículo",
}

NO_EXPLANATION = "(sin explicación comprobada)"
UNDEFINED = "(sin definir)"


class BriefDraft(BaseModel):
    # En este orden: el modelo genera primero los datos y después lo creativo, apoyado en ellos.
    key_points: list[Claim]
    why_it_fits: Claim
    angle: str
    hook: str
    structure: list[str]
    limitations: list[str]


@dataclass(frozen=True)
class BrandContext:
    name: str
    creates_about: str
    audience: str
    target_region: str
    tone: tuple[str, ...]
    call_to_action: str
    never_say: str
    out_of_scope: str
    version: int  # en la clave de caché: un perfil nuevo da un brief nuevo


def brand_context(name: str, profile: RadarProfile, version: int) -> BrandContext:
    return BrandContext(
        name=name,
        creates_about=profile.creates_about,
        audience=profile.audience,
        target_region=profile.target_region,
        tone=tuple(profile.tone),
        call_to_action=profile.call_to_action,
        never_say=profile.never_say,
        out_of_scope=profile.out_of_scope,
        version=version,
    )


@dataclass(frozen=True)
class BriefInput:
    platform: str
    goal: str
    format: str
    label: str
    facts: list[str]
    why_it_matters: str | None  # None si no hay una explicación comprobada
    fit: list[FitNote]
    pieces: list[EvidencePiece]
    brand: BrandContext | None = None  # None si el workspace no tiene perfil


def request_text(platform: BriefPlatform, goal: BriefGoal, fmt: BriefFormat) -> tuple[str, ...]:
    return PLATFORM_TEXT[platform], GOAL_TEXT[goal], FORMAT_TEXT[fmt]


@lru_cache
def system_prompt() -> str:
    return PROMPT_FILE.read_text(encoding="utf-8")


def brand_block(brand: BrandContext | None) -> str:
    if brand is None:
        return ""
    fields = [
        ("Marca", brand.name),
        ("Crea contenido sobre", brand.creates_about),
        ("Su cliente", brand.audience),
        ("Región", brand.target_region),
        ("Tono", ", ".join(brand.tone)),
        ("Cierre que busca", brand.call_to_action),
        ("Nunca dice", brand.never_say),
        ("Fuera de alcance", brand.out_of_scope),
    ]
    lines = "\n".join(f"{label}: {escape(text) if text else UNDEFINED}" for label, text in fields)
    return f"<brand_profile>\n{lines}\n</brand_profile>\n"


def user_message(brief: BriefInput) -> str:
    evidence = "\n".join(evidence_block(i, p) for i, p in enumerate(brief.pieces, start=1))
    facts = "\n".join(brief.facts)
    return (
        f"<request>\nPlataforma: {brief.platform}\nObjetivo: {brief.goal}\n"
        f"Formato: {brief.format}\n</request>\n"
        f"{brand_block(brief.brand)}"
        f"<topic_label>{escape(brief.label)}</topic_label>\n"
        f"<facts>\n{facts}\n</facts>\n"
        f"<why_it_matters>{escape(brief.why_it_matters or NO_EXPLANATION)}</why_it_matters>\n"
        f"<fit>\n{fit_lines(brief.fit)}\n</fit>\n{evidence}"
    )


def brief_cache_key(brief: BriefInput, model: str) -> str:
    payload = {
        "input": asdict(brief),
        "prompt_version": PROMPT_VERSION,
        "prompt_sha256": hashlib.sha256(system_prompt().encode("utf-8")).hexdigest(),
        "model": model,
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


BriefResult = LlmResult[BriefDraft]


class Briefer(Protocol):
    async def write(self, brief: BriefInput) -> BriefResult: ...


class AnthropicBriefer:
    def __init__(self, llm: StructuredLlm) -> None:
        self._llm = llm

    async def write(self, brief: BriefInput) -> BriefResult:
        return await self._llm.complete(
            system=system_prompt(), user=user_message(brief), output_type=BriefDraft
        )


def build_briefer(settings: Settings) -> Briefer | None:
    if not settings.llm_api_key or not settings.llm_model:
        return None
    client = AsyncAnthropic(api_key=settings.llm_api_key)
    return AnthropicBriefer(
        StructuredLlm(client, settings.llm_model, asyncio.Semaphore(LLM_CONCURRENCY))
    )
