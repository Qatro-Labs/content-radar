"""Detección de republicaciones con la batería de par de Jev y su caché (contra radar_test)."""

import math
from collections.abc import Mapping
from typing import Any

import numpy as np
from sqlalchemy import select

from app.collectors.usage import UsageMeter
from app.intelligence.jev import JudgeError, JudgeResult
from app.models import JevJudgment
from app.schemas.cost import Provider
from app.schemas.signal import Platform
from app.services import replicas as service
from app.services.classification import SKIPPED_WITHOUT_KEY
from app.services.replicas import detect_replicas
from tests.test_replicas import piece


class FakePairJudge:
    def __init__(self, score: float = 3.0, confidence: float = 0.9, *, fail: bool = False):
        self.score, self.confidence, self.fail = score, confidence, fail
        self.states: list[dict[str, Any]] = []

    @property
    def calls(self) -> int:
        return len(self.states)

    async def judge(self, state: dict[str, Any], questions: Mapping[str, Any]) -> JudgeResult:
        self.states.append(state)
        if self.fail:
            raise JudgeError("rate limited")
        answer = {
            "type": "score",
            "score": self.score,
            "confidence": self.confidence,
            "legend": {"0": "…", "1": "…", "2": "…", "3": "…"},
            "probabilities": {"3": 0.9, "2": 0.1},
        }
        return JudgeResult(
            model="jev-1.13.0", answers={"same_story": answer}, input_tokens=800, output_tokens=5
        )


def two_pieces(similarity: float, *, offset: int = 0):
    # La 1 se publicó antes: es la representante si hay republicación.
    a = piece(1 + offset, source=f"Medio A{offset}", hours_ago=20, title=f"Nota {offset} en A")
    b = piece(2 + offset, source=f"Medio B{offset}", hours_ago=5, title=f"Nota {offset} en B")
    vectors = np.array([[1.0, 0.0], [similarity, math.sqrt(1 - similarity**2)]])
    return [a, b], vectors


async def detect(session, similarity: float, judge, meter=None):
    pieces, vectors = two_pieces(similarity)
    return await detect_replicas(
        session, pieces, [[0, 1]], vectors, judge=judge, meter=meter or UsageMeter()
    )


async def test_jev_yes_marks_replica_and_is_cached(session):
    stories, stats = await detect(session, 0.80, FakePairJudge())
    assert stories.representative_of == {2: 1}
    assert stories.unverified == frozenset()
    assert (stats.candidates, stats.judged, stats.cached) == (1, 1, 0)

    second_judge = FakePairJudge()
    stories, stats = await detect(session, 0.80, second_judge)
    assert second_judge.calls == 0
    assert (stats.judged, stats.cached) == (0, 1)
    assert stories.representative_of == {2: 1}

    [row] = (await session.scalars(select(JevJudgment))).all()
    assert row.battery == "pair"
    assert row.content_item_id is None


async def test_jev_no_overrides_similarity_rule(session):
    # Nivel 2 seguro: el mismo hecho contado por separado, aunque el coseno pase de 0.90.
    stories, stats = await detect(session, 0.95, FakePairJudge(score=2.0))
    assert stories.replica_ids == frozenset()
    assert stats.replicas == 0


async def test_without_judge_uses_fallback_rule(session):
    stories, stats = await detect(session, 0.95, None)
    assert stories.representative_of == {2: 1}
    assert stories.unverified == frozenset({2})
    assert stats.skipped_reason == SKIPPED_WITHOUT_KEY
    assert (stats.replicas, stats.unverified) == (1, 1)

    stories, _ = await detect(session, 0.80, None)
    assert stories.replica_ids == frozenset()


async def test_without_judge_still_reads_cache(session):
    await detect(session, 0.80, FakePairJudge())
    stories, stats = await detect(session, 0.80, None)
    assert stories.representative_of == {2: 1}
    assert stories.unverified == frozenset()  # lo decidió Jev, aunque sea desde la caché
    assert stats.cached == 1


class SelectivePairJudge(FakePairJudge):
    """Falla en todos los pares salvo en `independent`, que responde nivel 2 con seguridad."""

    def __init__(self, independent: tuple[str, str]):
        super().__init__(score=2.0)
        self.independent = independent

    async def judge(self, state: dict[str, Any], questions: Mapping[str, Any]) -> JudgeResult:
        if (state["a"]["title"], state["b"]["title"]) != self.independent:
            self.states.append(state)
            raise JudgeError("rate limited")
        return await super().judge(state, questions)


async def test_jev_independent_pair_breaks_rule_chain(session):
    # 1~2 y 2~3 a 0.95 (la regla los uniría si Jev falla); 1~3 a 0.805, y Jev dice que no.
    pieces = [
        piece(1, source="Medio A", hours_ago=30, title="Nota 1"),
        piece(2, source="Medio B", hours_ago=20, title="Nota 2"),
        piece(3, source="Medio C", hours_ago=10, title="Nota 3"),
    ]
    theta = math.acos(0.95)
    vectors = np.array([[math.cos(k * theta), math.sin(k * theta)] for k in range(3)])
    judge = SelectivePairJudge(independent=("Nota 1", "Nota 3"))
    stories, stats = await detect_replicas(
        session, pieces, [[0, 1, 2]], vectors, judge=judge, meter=UsageMeter()
    )
    assert (stats.candidates, stats.judged, stats.failed) == (3, 1, 2)
    assert stories.representative_of == {}


async def test_judge_failure_falls_back(session):
    stories, stats = await detect(session, 0.95, FakePairJudge(fail=True))
    assert stats.failed == 1
    assert stories.unverified == frozenset({2})


async def test_budget_caps_new_calls(session, monkeypatch):
    monkeypatch.setattr(service, "MAX_PAIR_JUDGMENTS_PER_RUN", 1)
    low, low_vectors = two_pieces(0.80, offset=10)
    high, high_vectors = two_pieces(0.95, offset=20)
    judge = FakePairJudge()
    stories, stats = await detect_replicas(
        session,
        [*low, *high],
        [[0, 1], [2, 3]],
        np.vstack([low_vectors, high_vectors]),
        judge=judge,
        meter=UsageMeter(),
    )
    assert judge.calls == 1
    assert judge.states[0]["a"]["title"] == "Nota 20 en A"  # el par de mayor similitud
    assert (stats.judged, stats.over_budget) == (1, 1)
    # El de 0.80 queda fuera de presupuesto y la regla de respaldo no lo marca.
    assert stories.representative_of == {22: 21}


async def test_usage_is_metered_per_answer(session):
    meter = UsageMeter()
    await detect(session, 0.80, FakePairJudge(), meter)
    count = meter.counts[(Provider.TYPESAFE_JEV, "pair_battery")]
    assert (count.calls, count.units) == (1, 800)


class NoSession:
    def __getattr__(self, name: str):
        raise AssertionError(f"session.{name} sin candidatos")


async def test_no_candidates_makes_no_queries_or_calls():
    a = piece(1, platform=Platform.HACKERNEWS, source="HN · LLM")
    b = piece(2, platform=Platform.HACKERNEWS, source="HN · OpenAI")  # mismo medio
    judge = FakePairJudge()
    stories, stats = await detect_replicas(
        NoSession(),  # type: ignore[arg-type]  # falla si se toca la DB
        [a, b],
        [[0, 1]],
        np.array([[1.0, 0.0], [1.0, 0.0]]),
        judge=judge,
        meter=UsageMeter(),
    )
    assert judge.calls == 0
    assert stats.candidates == 0
    assert stories.replica_ids == frozenset()
