"""Batería de pieza de Jev y su conversión a decisiones. Sin red."""

import asyncio
import json
from dataclasses import replace
from datetime import UTC, datetime

import httpx2
import pytest
from typesafe_sdk import AsyncTypeSafeClient, Choice, Noul

from app.core.config import Settings
from app.intelligence.jev import (
    PieceJudgment,
    TypeSafeJudge,
    build_judge,
    cache_key,
    excluded_from_llm,
    keep_about_ai,
    piece_battery,
    piece_state,
    to_piece_judgment,
)
from app.intelligence.opportunities import Piece
from app.schemas.signal import Metrics, Platform, Segment, SourceKind

NOW = datetime(2026, 10, 17, 12, tzinfo=UTC)


def make_piece(title: str = "Agentes de IA en ventas", description: str | None = None) -> Piece:
    return Piece(
        item_id=1,
        url="https://example.com/a",
        title=title,
        description=description,
        platform=Platform.YOUTUBE,
        source_kind=SourceKind.CHANNEL,
        source_id=1,
        source_name="Canal Ejemplo",
        segment=Segment.LATAM_ES,
        language="es",
        published_at=NOW,
        observed_at=NOW,
        metrics=Metrics(),
    )


def noul(p: float) -> dict:
    return {"type": "noul", "noul": p}


def choice(label: str, prob: float) -> dict:
    return {
        "type": "choice",
        "choice": label,
        "confidence": prob,
        "probabilities": {label: prob, "other": 1 - prob},
    }


def labels(question) -> list[str]:
    assert isinstance(question, Choice)
    return list(question.criteria)


def test_battery_loads_all_questions():
    battery = piece_battery()

    assert list(battery.questions) == [
        "about_ai",
        "business_use",
        "dev_audience",
        "injection",
        "format",
        "format_rev",
        "hook",
        "hook_rev",
        "launch",
        "business_case",
        "tech_jargon",
        "latam_context",
    ]
    q = battery.questions
    assert labels(q["format_rev"]) == labels(q["format"])[::-1]
    assert labels(q["hook_rev"]) == labels(q["hook"])[::-1]


@pytest.mark.parametrize(
    ("p", "expected"), [(0.71, True), (0.29, False), (0.5, None)], ids=["yes", "no", "uncertain"]
)
def test_noul_thresholds(p, expected):
    assert to_piece_judgment(1, {"about_ai": noul(p)}).about_ai is expected


def test_choice_needs_agreement_with_rev():
    agree = {"format": choice("use_case", 0.8), "format_rev": choice("use_case", 0.7)}
    disagree = {"format": choice("use_case", 0.8), "format_rev": choice("news", 0.7)}
    weak = {"format": choice("use_case", 0.55), "format_rev": choice("use_case", 0.7)}

    assert to_piece_judgment(1, agree).format == "use_case"
    assert to_piece_judgment(1, disagree).format is None
    assert to_piece_judgment(1, weak).format is None


def test_missing_answers_are_uncertain():
    judgment = to_piece_judgment(1, {})
    assert all(value is None for key, value in vars(judgment).items() if key != "item_id")


def test_missing_injection_answer_excludes_piece():
    assert excluded_from_llm({}) is True


@pytest.mark.parametrize(
    ("p", "expected"), [(0.51, True), (0.5, False)], ids=["above_half", "at_half"]
)
def test_injection_excludes_above_half(p, expected):
    assert excluded_from_llm({"injection": noul(p)}) is expected


def test_state_trims_description_and_key_is_stable():
    state = piece_state(make_piece(description="x" * 1500))

    assert len(state["description"]) == 1000
    assert cache_key(state, "jev-1.13.0") == cache_key(
        piece_state(make_piece(description="x" * 1500)), "jev-1.13.0"
    )
    assert cache_key(state, "jev-1.13.0") != cache_key(state, "jev-1.14.0")


@pytest.mark.parametrize("description", [None, ""], ids=["none", "empty"])
def test_state_omits_missing_description(description):
    assert "description" not in piece_state(make_piece(description=description))


def test_state_never_carries_source_segment_or_region():
    assert {"segment", "region"}.isdisjoint(piece_state(make_piece(description="x")))


async def test_typesafe_judge_parses_response():
    received = {}

    def handler(request: httpx2.Request) -> httpx2.Response:
        received.update(json.loads(request.content))
        return httpx2.Response(
            200,
            json={
                "model": "jev-1.13.0",
                "usage": {"input_tokens": 280, "output_tokens": 20},
                "answers": {
                    "relevant": {"type": "noul", "noul": 0.9},
                    "format": {
                        "type": "choice",
                        "choice": "news",
                        "confidence": 0.8,
                        "probabilities": {"news": 0.8, "demo": 0.2},
                    },
                },
            },
        )

    client = AsyncTypeSafeClient(
        api_key="test", model="jev-1.13.0", transport=httpx2.MockTransport(handler)
    )
    judge = TypeSafeJudge(client, asyncio.Semaphore(1))
    questions = {
        "relevant": Noul(instructions="¿Trata de IA?"),
        "format": Choice(instructions="¿Formato?", criteria={"news": None, "demo": None}),
    }

    result = await judge.judge({"title": "Lanzan un agente"}, questions)

    assert received["state"] == {"title": "Lanzan un agente"}
    assert set(received["questions"]) == {"relevant", "format"}
    assert received["model"] == "jev-1.13.0"
    assert result.model == "jev-1.13.0"
    assert result.answers["relevant"]["noul"] == 0.9
    assert result.answers["format"]["choice"] == "news"
    assert (result.input_tokens, result.output_tokens) == (280, 20)


def test_build_judge_without_key_is_none():
    assert build_judge(Settings(typesafe_api_key="")) is None


def judged(item_id: int, about_ai: float) -> PieceJudgment:
    return to_piece_judgment(item_id, {"about_ai": noul(about_ai)})


def test_about_ai_filter_drops_only_pieces_judged_off_topic():
    pieces = [replace(make_piece(), item_id=i) for i in range(1, 5)]
    # 1 fuera de tema (seguro) · 2 sobre IA · 3 incierta · 4 sin clasificar.
    judgments = {1: judged(1, 0.1), 2: judged(2, 0.9), 3: judged(3, 0.5)}

    kept = keep_about_ai(pieces, judgments)

    assert [p.item_id for p in kept] == [2, 3, 4]
