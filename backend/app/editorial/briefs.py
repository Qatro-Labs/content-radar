"""Entrada y salida del brief editorial (CLAUDE.md §6, `POST /editorial/brief`).

Como en `explanation.py`, el texto externo va solo en el mensaje del usuario y escapado
(regla 6). El system prompt lleva nuestras instrucciones y el perfil de 30X.
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
from app.editorial.audience import EvidencePiece, escape, evidence_block, profile_text
from app.editorial.evaluator import LLM_CONCURRENCY, LlmResult, StructuredLlm
from app.editorial.explanation import Claim, FitNote, fit_lines
from app.schemas.editorial import BriefFormat, BriefGoal, BriefPlatform

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
PROMPT_VERSION = 1
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


class BriefDraft(BaseModel):
    # En este orden: el modelo genera primero los datos y después lo creativo, apoyado en ellos.
    key_points: list[Claim]
    why_it_fits: Claim
    angle: str
    hook: str
    structure: list[str]
    limitations: list[str]


@dataclass(frozen=True)
class BriefInput:
    platform: str
    goal: str
    format: str
    label: str
    facts: list[str]
    why_it_matters: str
    fit: list[FitNote]
    pieces: list[EvidencePiece]


def request_text(platform: BriefPlatform, goal: BriefGoal, fmt: BriefFormat) -> tuple[str, ...]:
    return PLATFORM_TEXT[platform], GOAL_TEXT[goal], FORMAT_TEXT[fmt]


@lru_cache
def system_prompt() -> str:
    return PROMPT_FILE.read_text(encoding="utf-8").replace("{{profile}}", profile_text())


def user_message(brief: BriefInput) -> str:
    evidence = "\n".join(evidence_block(i, p) for i, p in enumerate(brief.pieces, start=1))
    facts = "\n".join(brief.facts)
    return (
        f"<request>\nPlataforma: {brief.platform}\nObjetivo: {brief.goal}\n"
        f"Formato: {brief.format}\n</request>\n"
        f"<topic_label>{escape(brief.label)}</topic_label>\n"
        f"<facts>\n{facts}\n</facts>\n"
        f"<why_it_matters>{escape(brief.why_it_matters)}</why_it_matters>\n"
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
