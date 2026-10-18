"""Jev (TypeSafe): baterías de pieza y de par, y conversión de sus respuestas en decisiones
(CLAUDE.md §7).

Jev solo emite juicios atómicos; los umbrales y la decisión están aquí, en Python (regla 4).
El texto de la pieza va solo en `state`; nuestras instrucciones, en las preguntas (regla 6).
"""

import asyncio
import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Any, Protocol

import yaml
from typesafe_sdk import AsyncTypeSafeClient, Choice, Noul, Question, Score, TypeSafeError

from app.core.config import Settings
from app.intelligence.opportunities import Piece

# Excepción base del SDK: los services la capturan sin importar typesafe_sdk.
JudgeError = TypeSafeError

PIECE_BATTERY = "piece"
PIECE_BATTERY_FILE = Path(__file__).resolve().parents[1] / "editorial/prompts/jev/piece.v3.yaml"
MAX_DESCRIPTION_CHARS = 1000

PAIR_BATTERY = "pair"
PAIR_BATTERY_FILE = Path(__file__).resolve().parents[1] / "editorial/prompts/jev/pair.v1.yaml"
# Con dos piezas por llamada, 500 caracteres mantienen el par en ~800 tokens.
MAX_PAIR_DESCRIPTION_CHARS = 500
SAME_STORY_QUESTION = "same_story"

# Umbrales de docs/jev.md, "Del juicio a la decisión". Iniciales: se ajustan con la validación.
CHOICE_MIN_PROB = 0.6
NOUL_YES = 0.7
NOUL_NO = 0.3
# Más bajo que NOUL_YES a propósito: ante la duda, la pieza no entra en el contexto del LLM.
INJECTION_EXCLUDE = 0.5

REV_SUFFIX = "_rev"
INJECTION_QUESTION = "injection"
# El cookbook de TypeSafe usa 6 workers: el endpoint limita por encima de ese ritmo (docs/jev.md).
JEV_CONCURRENCY = 6


class QuestionType(StrEnum):
    NOUL = "noul"
    CHOICE = "choice"
    SCORE = "score"


QUESTION_CLASSES: dict[QuestionType, type[Noul | Choice | Score]] = {
    QuestionType.NOUL: Noul,
    QuestionType.CHOICE: Choice,
    QuestionType.SCORE: Score,
}


@dataclass(frozen=True)
class Battery:
    name: str
    version: int
    questions: dict[str, Noul | Choice | Score]


@dataclass(frozen=True)
class PieceJudgment:
    item_id: int
    # Filtro de ruido: sale solo lo que Jev dice con seguridad que no es IA en las dos preguntas.
    about_ai: bool | None
    ai_in_title: bool | None
    injection: bool | None
    format: str | None  # None si es incierto o no coincide con format_rev
    hook: str | None  # igual con hook_rev
    launch: bool | None
    # Pistas para el LLM, que decide el audience fit (CLAUDE.md §7).
    business_use: bool | None
    dev_audience: bool | None
    business_case: bool | None
    tech_jargon: bool | None
    latam_context: bool | None


@dataclass(frozen=True)
class JudgeResult:
    model: str
    answers: dict[str, Any]  # JSON de cada respuesta, con sus probabilidades
    input_tokens: int | None
    output_tokens: int | None


class Judge(Protocol):
    async def judge(
        self, state: dict[str, Any], questions: Mapping[str, Question]
    ) -> JudgeResult: ...


class TypeSafeJudge:
    def __init__(self, client: AsyncTypeSafeClient, semaphore: asyncio.Semaphore) -> None:
        self._client = client
        self._semaphore = semaphore

    async def judge(self, state: dict[str, Any], questions: Mapping[str, Question]) -> JudgeResult:
        async with self._semaphore:
            response = await self._client.system_one(state, questions)
        return JudgeResult(
            model=response.model,
            answers={k: a.model_dump(mode="json") for k, a in response.answers.items()},
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )


def build_judge(settings: Settings) -> Judge | None:
    if not settings.typesafe_api_key:
        return None
    # Sin `retry`: los reintentos por defecto del SDK (408, 429 y 5xx con backoff) bastan.
    client = AsyncTypeSafeClient(api_key=settings.typesafe_api_key, model=settings.jev_model)
    return TypeSafeJudge(client, asyncio.Semaphore(JEV_CONCURRENCY))


def load_battery(name: str, path: Path) -> Battery:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    questions: dict[str, Noul | Choice | Score] = {}
    for entry in raw["questions"]:
        fields = {k: entry[k] for k in ("instructions", "criteria") if k in entry}
        questions[entry["id"]] = QUESTION_CLASSES[QuestionType(entry["type"])](**fields)
    return Battery(name=name, version=raw["version"], questions=questions)


@lru_cache
def piece_battery() -> Battery:
    return load_battery(PIECE_BATTERY, PIECE_BATTERY_FILE)


def piece_state(piece: Piece) -> dict[str, Any]:
    state: dict[str, Any] = {
        "title": piece.title,
        "channel": piece.source_name,
        "platform": piece.platform.value,
        "language": piece.language,
    }
    # Sin descripción se omite la clave en vez de mandar `null`: en las preguntas de la v2 no cambia
    # nada medible y evita que Jev lea el `null` como dato. Segmento y región de la fuente no entran
    # nunca: con ellos en el state, Jev contestaba a partir de la fuente y no del contenido.
    if piece.description:
        state["description"] = piece.description[:MAX_DESCRIPTION_CHARS]
    return state


@lru_cache
def pair_battery() -> Battery:
    return load_battery(PAIR_BATTERY, PAIR_BATTERY_FILE)


def _pair_side(piece: Piece) -> dict[str, Any]:
    # La fuente ayuda a reconocer "WIRED" frente a "WIRED en Español". Sin URL: Jev contestaría
    # por el dominio, como pasaba con el segmento en la batería de pieza.
    side: dict[str, Any] = {"title": piece.title, "source": piece.source_name}
    if piece.description:
        side["description"] = piece.description[:MAX_PAIR_DESCRIPTION_CHARS]
    return side


def pair_state(a: Piece, b: Piece) -> dict[str, Any]:
    # Ordenado por item_id: (a, b) y (b, a) comparten caché.
    first, second = sorted((a, b), key=lambda p: p.item_id)
    return {"a": _pair_side(first), "b": _pair_side(second)}


def cache_key(state: dict[str, Any], model: str) -> str:
    return battery_cache_key(piece_battery(), state, model)


def battery_cache_key(battery: Battery, state: dict[str, Any], model: str) -> str:
    payload = {
        "state": state,
        "battery": battery.name,
        "battery_version": battery.version,
        "model": model,
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _noul(answers: dict[str, Any], question: str) -> bool | None:
    answer = answers.get(question)
    if answer is None:
        return None
    if answer["noul"] >= NOUL_YES:
        return True
    if answer["noul"] <= NOUL_NO:
        return False
    return None


def _choice(answers: dict[str, Any], question: str) -> str | None:
    answer, reverse = answers.get(question), answers.get(question + REV_SUFFIX)
    if answer is None or reverse is None:
        return None
    if max(answer["probabilities"].values()) < CHOICE_MIN_PROB:
        return None
    return answer["choice"] if answer["choice"] == reverse["choice"] else None


def to_piece_judgment(item_id: int, answers: dict[str, Any]) -> PieceJudgment:
    return PieceJudgment(
        item_id=item_id,
        about_ai=_noul(answers, "about_ai"),
        ai_in_title=_noul(answers, "ai_in_title"),
        injection=_noul(answers, INJECTION_QUESTION),
        format=_choice(answers, "format"),
        hook=_choice(answers, "hook"),
        launch=_noul(answers, "launch"),
        business_use=_noul(answers, "business_use"),
        dev_audience=_noul(answers, "dev_audience"),
        business_case=_noul(answers, "business_case"),
        tech_jargon=_noul(answers, "tech_jargon"),
        latam_context=_noul(answers, "latam_context"),
    )


def excluded_from_llm(answers: dict[str, Any]) -> bool:
    answer = answers.get(INJECTION_QUESTION)
    # Sin respuesta de inyección no sabemos si la pieza es segura: se excluye.
    if answer is None:
        return True
    return answer["noul"] > INJECTION_EXCLUDE


def keep_about_ai(pieces: Sequence[Piece], judgments: Mapping[int, PieceJudgment]) -> list[Piece]:
    # Solo sale lo que Jev dice con seguridad que no trata de IA: incierto o sin clasificar se
    # queda, para no perder temas por un fallo de Jev. `about_ai` solo quitaba piezas buenas con la
    # IA en el título y una descripción sobre otra cosa (Jev lee el conjunto de forma literal); con
    # el título como segunda condición, las piezas buenas quitadas bajan de 24 a 9 en 200
    # etiquetadas (data/evaluations/jev_piece_v3_eval.md).
    off_topic = {
        item_id
        for item_id, j in judgments.items()
        if j.about_ai is False and j.ai_in_title is False
    }
    return [p for p in pieces if p.item_id not in off_topic]
