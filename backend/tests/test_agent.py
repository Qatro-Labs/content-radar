"""Agente del Radar: límites, tools, bucle y ruta SSE (plan data-radar-agent)."""

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

import anthropic
import httpx
import pytest
from anthropic.types import MessageParam, ToolUseBlock
from httpx import ASGITransport, AsyncClient

from app.agent.limits import MAX_STEPS, LimitResult, RateLimiter
from app.agent.model import ModelTurn, ToolCall
from app.agent.runner import AGENT_OPERATION, DEFAULT_UNKNOWN, run_agent
from app.agent.tools import FINAL_ANSWER, Seen, execute_tool
from app.api.routes.agent import get_agent_model, get_rate_limiter, get_session_factory
from app.collectors.usage import UsageMeter
from app.main import app
from app.schemas.agent import (
    ActionEvent,
    AnswerEvent,
    DoneEvent,
    ErrorCode,
    ErrorEvent,
    RadarPatch,
    StepKind,
)
from app.schemas.cost import Provider
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


def turn(*calls: tuple[str, dict], tokens: tuple[int, int] = (100, 20)) -> ModelTurn:
    tool_calls = [ToolCall(f"toolu_{n}", name, args) for n, (name, args) in enumerate(calls)]
    blocks = [
        ToolUseBlock(id=c.id, name=c.name, input=c.input, type="tool_use") for c in tool_calls
    ]
    return ModelTurn(list(blocks), tool_calls, tokens[0], tokens[1])


def final(
    text: str = "Agentes de IA acelera.",
    cited: list[str] | None = None,
    unknowns: list[str] | None = None,
    tokens: tuple[int, int] = (100, 20),
) -> ModelTurn:
    args = {
        "text": text,
        "cited_ids": cited or [],
        "unknowns": ["Sin datos de LinkedIn."] if unknowns is None else unknowns,
    }
    return turn((FINAL_ANSWER, args), tokens=tokens)


class ScriptedModel:
    def __init__(self, turns: list[ModelTurn | Exception]) -> None:
        self.turns = list(turns)
        self.force_finals: list[bool] = []
        self.messages: list[list[MessageParam]] = []

    async def next_turn(self, messages: list[MessageParam], *, force_final: bool) -> ModelTurn:
        self.force_finals.append(force_final)
        self.messages.append(list(messages))
        next_turn = self.turns.pop(0)
        if isinstance(next_turn, Exception):
            raise next_turn
        return next_turn


async def run(session, model, meter: UsageMeter | None = None, question: str = "¿Qué acelera?"):
    return [
        e
        async for e in run_agent(
            question, model=model, session=session, meter=meter or UsageMeter()
        )
    ]


def kinds(events) -> list[str]:
    names = {
        "StepEvent": "step",
        "ActionEvent": "action",
        "AnswerEvent": "answer",
        "ErrorEvent": "error",
        "DoneEvent": "done",
    }
    return [names[type(e).__name__] for e in events]


async def test_run_emits_steps_actions_and_answer(session, seeded):
    model = ScriptedModel(
        [
            turn(("list_opportunities", {})),
            turn(("select_opportunity", {"id": "opp_001"})),
            final(cited=["opp_001", "opp_inventado"]),
        ]
    )

    events = await run(session, model)

    assert kinds(events) == ["step", "step", "step", "step", "action", "answer", "done"]
    answer = events[-2]
    assert isinstance(answer, AnswerEvent)
    assert [c.id for c in answer.cited] == ["opp_001"]
    assert events[-1] == DoneEvent(steps=2, data_steps=1, view_steps=1)


async def test_answer_drops_unseen_urls(session, seeded):
    text = "Mira https://example.com/mock/1 y https://evil.example/x"
    model = ScriptedModel([turn(("get_evidence", {"id": "opp_001"})), final(text=text)])

    answer = (await run(session, model))[-2]

    assert isinstance(answer, AnswerEvent)
    assert "https://example.com/mock/1" in answer.text
    assert "evil.example" not in answer.text


async def test_forces_final_answer_after_max_steps(session, seeded):
    listing = [turn(("list_opportunities", {})) for _ in range(MAX_STEPS + 1)]
    model = ScriptedModel([*listing, final()])

    events = await run(session, model)

    assert model.force_finals == [False] * MAX_STEPS + [True, True]
    assert events[-1].steps == MAX_STEPS


async def test_missing_unknowns_get_default_note(session, seeded):
    model = ScriptedModel([turn(("list_opportunities", {})), final(unknowns=[])])

    answer = (await run(session, model))[-2]

    assert isinstance(answer, AnswerEvent)
    assert answer.unknowns == [DEFAULT_UNKNOWN]


async def test_llm_error_emits_error_then_done(session, seeded):
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    model = ScriptedModel([anthropic.APIConnectionError(request=request)])

    events = await run(session, model)

    assert kinds(events) == ["error", "done"]
    assert isinstance(events[0], ErrorEvent)
    assert events[0].code is ErrorCode.LLM_UNAVAILABLE


async def test_no_data_emits_error(session):
    events = await run(session, ScriptedModel([]))

    assert kinds(events) == ["error", "done"]
    assert isinstance(events[0], ErrorEvent)
    assert events[0].code is ErrorCode.NO_DATA


async def test_usage_is_metered(session, seeded):
    meter = UsageMeter()
    model = ScriptedModel(
        [turn(("list_opportunities", {}), tokens=(100, 20)), final(tokens=(150, 30))]
    )

    await run(session, model, meter)

    usage = meter.counts[(Provider.LLM_TEXT, AGENT_OPERATION)]
    assert (usage.calls, usage.units, usage.output_units) == (2, 250, 50)


@pytest.fixture
def overrides(session):
    @asynccontextmanager
    async def test_session():
        yield session

    app.dependency_overrides[get_session_factory] = lambda: test_session
    app.dependency_overrides[get_rate_limiter] = lambda: RateLimiter(
        per_ip_per_hour=20, global_per_day=300
    )
    try:
        yield app.dependency_overrides
    finally:
        app.dependency_overrides.clear()


async def ask(question: str = "¿Qué acelera?") -> httpx.Response:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.post("/api/v1/agent", json={"question": question})


async def test_route_streams_events(seeded, overrides):
    model = ScriptedModel([turn(("list_opportunities", {})), final(cited=["opp_001"])])
    overrides[get_agent_model] = lambda: model

    response = await ask()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    body = response.text
    positions = [body.index(f"event: {name}") for name in ("step", "answer", "done")]
    assert positions == sorted(positions)


async def test_route_rejects_long_question(overrides):
    overrides[get_agent_model] = lambda: ScriptedModel([])

    response = await ask("x" * 301)

    assert response.status_code == 422


async def test_route_without_llm_is_503(overrides):
    overrides[get_agent_model] = lambda: None

    response = await ask()

    assert response.status_code == 503


async def test_route_rate_limited_is_429(seeded, overrides):
    limiter = RateLimiter(per_ip_per_hour=1, global_per_day=300)
    overrides[get_rate_limiter] = lambda: limiter
    overrides[get_agent_model] = lambda: ScriptedModel([final(), final()])

    first, second = await ask(), await ask()

    assert first.status_code == 200
    assert second.status_code == 429
    assert "demasiadas preguntas" in second.json()["detail"]
