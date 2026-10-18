"""Batería de pieza de Jev y su conversión a decisiones. Sin red."""

import asyncio
import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime

import httpx2
import pytest
from typesafe_sdk import AsyncTypeSafeClient, Choice, Noul, Score

from app.core.config import Settings
from app.intelligence.jev import (
    CitedEvidence,
    PieceJudgment,
    TypeSafeJudge,
    battery_cache_key,
    build_judge,
    cache_key,
    claim_battery,
    claim_state,
    claim_supported,
    excluded_from_llm,
    keep_about_ai,
    pair_battery,
    pair_state,
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
        "ai_in_title",
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


def test_piece_cache_key_is_unchanged():
    # Las filas de pieza ya guardadas se leen por esta clave: el payload no puede cambiar.
    state = piece_state(make_piece(description="x"))
    payload = {"state": state, "battery": "piece", "battery_version": 3, "model": "jev-1.13.0"}
    expected = hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    assert cache_key(state, "jev-1.13.0") == expected


def test_pair_battery_loads_same_story_score():
    battery = pair_battery()
    assert battery.name == "pair"
    assert list(battery.questions) == ["same_story"]
    question = battery.questions["same_story"]
    assert isinstance(question, Score)
    assert len(question.criteria) == 4


def pair_piece(item_id: int, title: str, description: str | None = None) -> Piece:
    return replace(make_piece(title, description), item_id=item_id, source_name=f"Medio {item_id}")


def test_pair_state_is_canonical():
    a, b = pair_piece(2, "WIRED: agentes"), pair_piece(1, "WIRED en Español: agentes")
    assert pair_state(a, b) == pair_state(b, a)
    assert pair_state(a, b)["a"]["title"] == "WIRED en Español: agentes"  # item_id menor
    key = battery_cache_key(pair_battery(), pair_state(a, b), "jev-1.13.0")
    assert key == battery_cache_key(pair_battery(), pair_state(b, a), "jev-1.13.0")
    assert key != cache_key(pair_state(a, b), "jev-1.13.0")  # otra batería, otra clave


def test_pair_state_trims_and_omits_description():
    state = pair_state(pair_piece(1, "A", "x" * 900), pair_piece(2, "B"))
    assert state["a"] == {"title": "A", "source": "Medio 1", "description": "x" * 500}
    assert state["b"] == {"title": "B", "source": "Medio 2"}


def test_pair_state_never_carries_url_segment_or_region():
    a = replace(pair_piece(1, "A", "x"), region="co", target_url="https://example.com/t")
    state = pair_state(a, pair_piece(2, "B", "y"))
    for side in state.values():
        assert {"url", "target_url", "segment", "region", "metrics"}.isdisjoint(side)


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


def judged(item_id: int, about_ai: float, ai_in_title: float) -> PieceJudgment:
    return to_piece_judgment(
        item_id, {"about_ai": noul(about_ai), "ai_in_title": noul(ai_in_title)}
    )


def test_about_ai_filter_drops_only_pieces_off_topic_in_both_questions():
    pieces = [replace(make_piece(), item_id=i) for i in range(1, 7)]
    judgments = {
        1: judged(1, 0.1, 0.05),  # fuera de tema en las dos: sale
        2: judged(2, 0.9, 0.9),
        # "La IA se compra. La gerencia para usarla, no": la descripción habla de otra cosa.
        3: judged(3, 0.27, 0.98),
        4: judged(4, 0.1, 0.5),  # título incierto
        5: judged(5, 0.5, 0.1),  # about_ai incierto
    }  # 6: sin clasificar

    kept = keep_about_ai(pieces, judgments)

    assert [p.item_id for p in kept] == [2, 3, 4, 5, 6]


def test_about_ai_filter_keeps_pieces_judged_without_title_question():
    # Un juicio sin `ai_in_title` (incompleto) no basta para quitar la pieza.
    pieces = [make_piece()]
    judgments = {1: to_piece_judgment(1, {"about_ai": noul(0.05)})}

    assert keep_about_ai(pieces, judgments) == pieces


def test_claim_battery_has_support_and_its_reverse():
    battery = claim_battery()

    assert battery.name == "claim"
    assert list(battery.questions) == ["support", "support_rev"]
    assert labels(battery.questions["support"]) == ["supports", "contradicts", "says_nothing"]
    assert labels(battery.questions["support_rev"]) == labels(battery.questions["support"])[::-1]


@pytest.mark.parametrize(
    ("answers", "expected"),
    [
        ({"support": choice("supports", 0.6), "support_rev": choice("supports", 0.8)}, True),
        ({"support": choice("supports", 0.59), "support_rev": choice("supports", 0.9)}, False),
        ({"support": choice("supports", 0.9), "support_rev": choice("says_nothing", 0.7)}, False),
        (
            {"support": choice("contradicts", 0.95), "support_rev": choice("contradicts", 0.9)},
            False,
        ),
        (
            {"support": choice("says_nothing", 0.9), "support_rev": choice("says_nothing", 0.9)},
            False,
        ),
        ({}, None),
        ({"support": choice("supports", 0.9)}, None),
    ],
    ids=[
        "supported",
        "low_confidence",
        "rev_disagrees",
        "contradicts",
        "says_nothing",
        "no_answers",
        "missing_rev",
    ],
)
def test_claim_supported(answers, expected):
    assert claim_supported(answers) is expected


FACTS = ["Etapa: saturado.", "Fuentes independientes: 4."]


def test_claim_state_carries_only_claim_facts_and_cited_text():
    evidence = [CitedEvidence("Canal Ejemplo", "Agentes en ventas", "Un caso en retail.")]

    state = claim_state("Las empresas usan agentes.", facts=FACTS, evidence=evidence)

    assert state == {
        "claim": "Las empresas usan agentes.",
        "measured_facts": FACTS,
        "evidence": [
            {
                "source": "Canal Ejemplo",
                "title": "Agentes en ventas",
                "description": "Un caso en retail.",
            }
        ],
    }


@pytest.mark.parametrize("description", [None, ""], ids=["none", "empty"])
def test_claim_state_omits_missing_description(description):
    evidence = [CitedEvidence("Canal Ejemplo", "Agentes en ventas", description)]

    state = claim_state("Algo.", facts=FACTS, evidence=evidence)

    assert state["evidence"] == [{"source": "Canal Ejemplo", "title": "Agentes en ventas"}]


def test_cache_key_depends_on_battery():
    state = claim_state("Algo.", facts=FACTS, evidence=[CitedEvidence("A", "B", None)])

    assert battery_cache_key(claim_battery(), state, "jev-1.13.0") != cache_key(state, "jev-1.13.0")
    # La clave de pieza no cambia: las filas de `piece` ya guardadas siguen valiendo.
    assert cache_key(state, "jev-1.13.0") == battery_cache_key(piece_battery(), state, "jev-1.13.0")
