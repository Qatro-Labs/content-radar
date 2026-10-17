"""Agente del Radar: límites, tools, bucle y ruta SSE (plan data-radar-agent)."""

from datetime import UTC, datetime, timedelta

import pytest

from app.agent.limits import LimitResult, RateLimiter
from app.agent.tools import Seen, execute_tool
from app.schemas.agent import ActionEvent, RadarPatch, StepKind
from tests.test_opportunity_routes import add_run, fixture_results

T0 = datetime(2026, 10, 17, 12, tzinfo=UTC)


def _ask_many(limiter: RateLimiter, count: int, *, ip: str = "1.1.1.1", at: datetime = T0) -> None:
    for _ in range(count):
        assert limiter.check(ip, at) is LimitResult.OK


def _ask_from_distinct_ips(limiter: RateLimiter, count: int) -> None:
    for n in range(count):
        assert limiter.check(f"10.0.{n // 256}.{n % 256}", T0) is LimitResult.OK


@pytest.mark.parametrize(
    ("prepare", "ip", "at", "expected"),
    [
        (lambda lim: _ask_many(lim, 19), "1.1.1.1", T0, LimitResult.OK),
        (lambda lim: _ask_many(lim, 20), "1.1.1.1", T0 + timedelta(minutes=59), LimitResult.IP),
        (
            lambda lim: _ask_many(lim, 20),
            "1.1.1.1",
            T0 + timedelta(hours=1, seconds=1),
            LimitResult.OK,
        ),
        (lambda lim: _ask_from_distinct_ips(lim, 300), "9.9.9.9", T0, LimitResult.GLOBAL),
    ],
    ids=["under", "ip-limit", "window-slides", "global-limit"],
)
def test_rate_limiter(prepare, ip, at, expected):
    limiter = RateLimiter(per_ip_per_hour=20, global_per_day=300)
    prepare(limiter)

    assert limiter.check(ip, at) is expected


def test_action_patch_keeps_explicit_nulls():
    event = ActionEvent(step_id=1, patch=RadarPatch(selected=None, gap=False))

    dumped = event.model_dump(mode="json", exclude_unset=True)

    assert dumped["patch"] == {"selected": None, "gap": False}
    assert "lifecycle" not in dumped["patch"]


@pytest.fixture
async def seeded(session):
    await add_run(session, fixture_results())


async def test_list_tool_filters_and_records_seen_ids(session, seeded):
    seen = Seen()

    outcome = await execute_tool("list_opportunities", {"lifecycle": ["emerging"]}, session, seen)

    assert outcome.kind is StepKind.DATA
    assert not outcome.is_error
    assert outcome.content.startswith("<datos>")
    assert '"opp_002"' in outcome.content
    assert '"opp_001"' not in outcome.content
    assert set(seen.opportunities) == {"opp_002"}


async def test_view_tool_rejects_unknown_id(session, seeded):
    outcome = await execute_tool("select_opportunity", {"id": "opp_nope"}, session, Seen())

    assert outcome.kind is StepKind.VIEW
    assert outcome.is_error
    assert outcome.patch is None


async def test_set_filters_label_and_patch(session, seeded):
    outcome = await execute_tool("set_filters", {"gap": True}, session, Seen())

    assert outcome.label == "Pulsando «Hueco en LATAM»"
    assert outcome.patch is not None
    assert outcome.patch.model_dump(mode="json", exclude_unset=True) == {"gap": True}


async def test_reset_view_patch(session, seeded):
    outcome = await execute_tool("reset_view", {}, session, Seen())

    assert outcome.patch is not None
    assert outcome.patch.model_dump(mode="json", exclude_unset=True) == {
        "lifecycle": [],
        "confidence": None,
        "topic": None,
        "gap": False,
        "sort": "opportunity",
        "selected": None,
        "highlight": [],
    }
