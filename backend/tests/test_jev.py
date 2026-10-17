"""Batería de pieza de Jev y su conversión a decisiones. Sin red."""

from datetime import UTC, datetime

import pytest
from typesafe_sdk import Choice

from app.intelligence.jev import (
    cache_key,
    excluded_from_llm,
    piece_battery,
    piece_state,
    to_piece_judgment,
)
from app.intelligence.opportunities import Piece
from app.schemas.signal import Metrics, Platform, Segment

NOW = datetime(2026, 10, 17, 12, tzinfo=UTC)


def make_piece(title: str = "Agentes de IA en ventas", description: str | None = None) -> Piece:
    return Piece(
        item_id=1,
        url="https://example.com/a",
        title=title,
        description=description,
        platform=Platform.YOUTUBE,
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


def score(value: float, conf: float) -> dict:
    return {
        "type": "score",
        "score": value,
        "confidence": conf,
        "legend": {},
        "probabilities": {},
    }


def labels(question) -> list[str]:
    assert isinstance(question, Choice)
    return list(question.criteria)


def test_battery_loads_all_questions():
    battery = piece_battery()

    assert list(battery.questions) == [
        "relevant",
        "injection",
        "format",
        "format_rev",
        "hook",
        "hook_rev",
        "announcement",
        "business_case",
        "exec_readability",
        "latam_context",
    ]
    q = battery.questions
    assert labels(q["format_rev"]) == labels(q["format"])[::-1]
    assert labels(q["hook_rev"]) == labels(q["hook"])[::-1]


@pytest.mark.parametrize(
    ("p", "expected"), [(0.71, True), (0.29, False), (0.5, None)], ids=["yes", "no", "uncertain"]
)
def test_noul_thresholds(p, expected):
    assert to_piece_judgment(1, {"relevant": noul(p)}).relevant is expected


def test_choice_needs_agreement_with_rev():
    agree = {"format": choice("use_case", 0.8), "format_rev": choice("use_case", 0.7)}
    disagree = {"format": choice("use_case", 0.8), "format_rev": choice("news", 0.7)}
    weak = {"format": choice("use_case", 0.55), "format_rev": choice("use_case", 0.7)}

    assert to_piece_judgment(1, agree).format == "use_case"
    assert to_piece_judgment(1, disagree).format is None
    assert to_piece_judgment(1, weak).format is None


def test_score_needs_confidence():
    assert to_piece_judgment(1, {"exec_readability": score(2.6, 0.7)}).exec_readability == 3
    assert to_piece_judgment(1, {"exec_readability": score(2.6, 0.4)}).exec_readability is None


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
