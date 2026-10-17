"""Clasificación de piezas con Jev y su caché en `jev_judgments` (contra radar_test)."""

from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any

from app.collectors.usage import UsageMeter
from app.intelligence.jev import JudgeError, JudgeResult
from app.intelligence.opportunities import Piece
from app.models import ContentItem, Source
from app.schemas.cost import Provider
from app.schemas.signal import Metrics, Platform, Segment
from app.services.classification import classify_pieces

NOW = datetime(2026, 10, 17, 12, tzinfo=UTC)
ANSWERS = {"relevant": {"type": "noul", "noul": 0.9}}


class FakeJudge:
    def __init__(self, fail_titles: frozenset[str] = frozenset(), input_tokens: int = 100):
        self.calls = 0
        self.fail_titles = fail_titles
        self.input_tokens = input_tokens

    async def judge(self, state: dict[str, Any], questions: Mapping[str, Any]) -> JudgeResult:
        self.calls += 1
        if state["title"] in self.fail_titles:
            raise JudgeError("rate limited")
        return JudgeResult(
            model="jev-1.13.0", answers=ANSWERS, input_tokens=self.input_tokens, output_tokens=20
        )


async def make_pieces(session, n: int = 3) -> list[Piece]:
    src = Source(
        platform="youtube",
        kind="channel",
        external_id="UC123",
        name="Canal Ejemplo",
        segment="latam_es",
        language="es",
    )
    session.add(src)
    await session.flush()
    items = [
        ContentItem(
            source_id=src.id,
            platform="youtube",
            external_id=f"vid{i}",
            url=f"https://www.youtube.com/watch?v=vid{i}",
            title=f"Agentes de IA, parte {i}",
            published_at=NOW - timedelta(days=1),
            first_observed_at=NOW,
            last_observed_at=NOW,
        )
        for i in range(n)
    ]
    session.add_all(items)
    await session.commit()
    return [
        Piece(
            item_id=item.id,
            url=item.url,
            title=item.title,
            description=None,
            platform=Platform.YOUTUBE,
            source_id=src.id,
            source_name=src.name,
            segment=Segment.LATAM_ES,
            language="es",
            published_at=item.published_at,
            observed_at=NOW,
            metrics=Metrics(),
        )
        for item in items
    ]


async def test_second_run_uses_cache(session):
    pieces = await make_pieces(session)
    judge = FakeJudge()

    first = await classify_pieces(session, pieces, judge, UsageMeter())
    second = await classify_pieces(session, pieces, judge, UsageMeter())

    assert (first.classified, first.cached) == (3, 0)
    assert judge.calls == 3
    assert (second.classified, second.cached) == (0, 3)


async def test_changed_state_is_reclassified(session):
    pieces = await make_pieces(session)
    await classify_pieces(session, pieces, FakeJudge(), UsageMeter())
    judge = FakeJudge()

    pieces[0] = replace(pieces[0], title="Título nuevo")
    stats = await classify_pieces(session, pieces, judge, UsageMeter())

    assert judge.calls == 1
    assert (stats.classified, stats.cached) == (1, 2)


async def test_failure_in_one_piece_does_not_abort(session):
    pieces = await make_pieces(session)
    judge = FakeJudge(fail_titles=frozenset({pieces[1].title}))

    stats = await classify_pieces(session, pieces, judge, UsageMeter())

    assert (stats.classified, stats.failed) == (2, 1)


async def test_without_judge_nothing_is_called(session):
    pieces = await make_pieces(session)

    stats = await classify_pieces(session, pieces, None, UsageMeter())

    assert stats.failed == len(pieces)
    assert stats.skipped_reason


async def test_usage_counted_only_for_real_calls(session):
    pieces = await make_pieces(session)
    judge = FakeJudge(input_tokens=100)
    meter = UsageMeter()

    await classify_pieces(session, pieces, judge, meter)
    second_meter = UsageMeter()
    await classify_pieces(session, pieces, judge, second_meter)

    count = meter.counts[(Provider.TYPESAFE_JEV, "piece_battery")]
    assert (count.calls, count.units) == (3, 300)
    assert not second_meter.counts
