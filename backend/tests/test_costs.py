from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx
import pytest
import respx
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.collectors.hackernews import API_URL as HN_URL
from app.collectors.usage import UsageCount, UsageMeter
from app.collectors.youtube import API_BASE, YouTubeClient, YouTubeCollector
from app.core.config import Settings
from app.core.pricing import VariablePrice, get_pricing
from app.db.session import get_session
from app.jobs import collect
from app.main import app
from app.models import PipelineRun, Source, UsageEvent
from app.schemas.cost import CostPeriod, Provider
from app.services import costs
from app.services.costs import operating_cost, record_meter, record_usage

NOW = datetime(2026, 10, 17, 12, 0, tzinfo=UTC)


@pytest.fixture
def unknown_llm_price(monkeypatch):
    pricing = get_pricing()
    variable = {**pricing.variable, Provider.LLM_TEXT: VariablePrice(unit="tokens")}
    patched = pricing.model_copy(update={"variable": variable})
    monkeypatch.setattr(costs, "get_pricing", lambda: patched)


@pytest.fixture
def llm_model(monkeypatch):
    def use(model: str) -> None:
        monkeypatch.setattr(costs, "get_settings", lambda: Settings(llm_model=model))

    return use


# --- precios ------------------------------------------------------------------------------


def test_every_provider_has_a_price_entry():
    pricing = get_pricing()
    assert set(pricing.variable) == set(Provider)
    # A mano: demo = Railway 5; production = Railway 5 + Supabase 25 + Vercel 20.
    assert pricing.fixed_total("demo") == Decimal("5.00")
    assert pricing.fixed_total("production") == Decimal("50.00")


@pytest.mark.parametrize(
    ("provider", "units", "expected"),
    [
        (Provider.BRAVE_SEARCH, 200, Decimal("1.000")),
        (Provider.TYPESAFE_JEV, 1_000_000, Decimal("0.042")),
        (Provider.YOUTUBE, 300, Decimal(0)),
    ],
    ids=["brave", "jev", "youtube-free"],
)
def test_cost_is_units_times_price(provider, units, expected):
    assert get_pricing().variable[provider].cost(Decimal(units)) == expected


def test_unknown_price_costs_null():
    assert VariablePrice(unit="tokens").cost(Decimal(5000)) is None


def test_llm_cost_prices_input_and_output_separately():
    # A mano con claude-haiku-5-5: 0,10 $ por millón de entrada + 0,50 $ por millón de salida.
    price = get_pricing().variable[Provider.LLM_TEXT]
    assert price.cost(Decimal(1_000_000), output_units=Decimal(1_000_000)) == Decimal("0.60")


def test_llm_cost_without_output_tokens_is_null():
    assert get_pricing().variable[Provider.LLM_TEXT].cost(Decimal(1_000_000)) is None


async def test_llm_meter_records_total_tokens_and_split(session, llm_model):
    llm_model("claude-haiku-5-5")
    meter = UsageMeter()
    meter.add(Provider.LLM_TEXT, "evaluate_topic", units=600, output_units=200)
    meter.add(Provider.LLM_TEXT, "evaluate_topic", units=400, output_units=300)

    await record_meter(session, meter)

    event = await session.scalar(select(UsageEvent))
    assert event is not None
    # 1000 de entrada · 0,10 $/M + 500 de salida · 0,50 $/M = 0,0001 + 0,00025.
    assert (event.calls, event.units, event.cost_usd) == (2, 1500, Decimal("0.00035"))
    assert event.details == {"input_tokens": 1000, "output_tokens": 500}


async def test_llm_cost_is_null_when_the_configured_model_is_not_the_priced_one(session, llm_model):
    llm_model("claude-sonnet-5-5")
    meter = UsageMeter()
    meter.add(Provider.LLM_TEXT, "evaluate_topic", units=600, output_units=200)

    await record_meter(session, meter)

    event = await session.scalar(select(UsageEvent))
    assert event is not None and event.cost_usd is None


async def test_record_usage_keeps_unknown_price_as_null(session, unknown_llm_price):
    event = await record_usage(session, Provider.LLM_TEXT, "explain_opportunity", 1200)
    assert event.cost_usd is None
    assert event.unit == "tokens"


# --- conteo en los collectors -------------------------------------------------------------


@respx.mock
async def test_youtube_counts_quota_units_per_call():
    respx.get(f"{API_BASE}/playlistItems").mock(
        return_value=httpx.Response(200, json={"items": [{"contentDetails": {"videoId": "v1"}}]})
    )
    respx.get(f"{API_BASE}/videos").mock(return_value=httpx.Response(200, json={"items": []}))
    respx.get(f"{API_BASE}/channels").mock(return_value=httpx.Response(200, json={"items": []}))
    source = Source(id=1, platform="youtube", name="C", config={"uploads_playlist_id": "UU1"})

    meter = UsageMeter()
    async with httpx.AsyncClient() as http:
        client = YouTubeClient("k", http, meter)
        await YouTubeCollector(client).collect(source, backfill_days=7)
        await client.channel_by_handle("@x")

    assert meter.counts == {
        (Provider.YOUTUBE, "playlistItems.list"): UsageCount(calls=1, units=1),
        (Provider.YOUTUBE, "videos.list"): UsageCount(calls=1, units=1),
        (Provider.YOUTUBE, "channels.list"): UsageCount(calls=1, units=1),
    }


@respx.mock
async def test_collect_job_persists_usage_linked_to_run(engine, session, monkeypatch):
    monkeypatch.setattr(collect, "SessionLocal", async_sessionmaker(engine, expire_on_commit=False))
    respx.get(HN_URL).mock(
        side_effect=[
            httpx.Response(200, json={"nbPages": 2, "hits": []}),
            httpx.Response(200, json={"nbPages": 2, "hits": []}),
        ]
    )
    session.add(
        Source(platform="hackernews", kind="query", external_id="AI", name="HN", segment="tech")
    )
    run_row = PipelineRun(job="collect", status="running")
    session.add(run_row)
    await session.commit()

    await collect.run(7, ["hackernews"], run_row.id)

    event = await session.scalar(select(UsageEvent))
    assert event is not None
    assert (event.provider, event.operation) == ("hackernews", "search_by_date")
    assert (event.calls, event.units, event.cost_usd) == (2, 2, 0)
    assert event.pipeline_run_id == run_row.id


async def test_empty_meter_records_nothing(session):
    assert await record_meter(session, UsageMeter()) == 0


# --- agregación y proyección --------------------------------------------------------------


async def test_no_usage_reports_unavailable_not_zero(session):
    cost = await operating_cost(session, CostPeriod.WEEK, now=NOW)

    assert cost.measured_since is None
    assert cost.measured.total_usd is None
    assert cost.measured.providers == []
    assert cost.projection["demo"].fixed_usd == 5.0
    assert cost.projection["demo"].variable_usd is None
    assert cost.projection["demo"].total_usd is None


async def test_projection_scales_observed_days_and_applies_free_credit(session):
    await record_usage(
        session, Provider.BRAVE_SEARCH, "search", 200, occurred_at=NOW - timedelta(days=2)
    )
    yesterday = NOW - timedelta(days=1)
    await record_usage(
        session, Provider.YOUTUBE, "videos.list", 300, calls=300, occurred_at=yesterday
    )

    cost = await operating_cost(session, CostPeriod.WEEK, now=NOW)

    by_provider = {p.provider: p for p in cost.measured.providers}
    assert by_provider[Provider.BRAVE_SEARCH].cost_usd == 1.0
    assert by_provider[Provider.YOUTUBE].calls == 300
    assert cost.measured.total_usd == 1.0
    # 1 $ en 2 días → 15 $ en 30 días, menos 5 $ de crédito gratis de Brave = 10 $.
    assert cost.projection["demo"].based_on_days == 2.0
    assert cost.projection["demo"].variable_usd == 10.0
    assert cost.projection["demo"].total_usd == 15.0
    assert cost.projection["production"].total_usd == 60.0


async def test_single_recent_event_projects_from_at_least_one_day(session):
    await record_usage(
        session, Provider.BRAVE_SEARCH, "search", 100, occurred_at=NOW - timedelta(hours=1)
    )
    cost = await operating_cost(session, CostPeriod.WEEK, now=NOW)
    # 0,50 $ en 1 h no se proyecta como 360 $/mes: cuenta como 1 día → 15 $ − 5 $ de crédito.
    assert cost.projection["demo"].based_on_days == 1.0
    assert cost.projection["demo"].variable_usd == 10.0


async def test_unknown_price_is_counted_but_not_summed(session, unknown_llm_price):
    await record_usage(session, Provider.LLM_TEXT, "explain", 5000, occurred_at=NOW)
    cost = await operating_cost(session, CostPeriod.WEEK, now=NOW)

    [llm] = cost.measured.providers
    assert (llm.cost_usd, llm.unknown_price_events) == (None, 1)
    assert cost.measured.total_usd is None
    assert cost.projection["demo"].total_usd is None
    assert any("sin precio" in note for note in cost.limitations)

    await record_usage(session, Provider.HACKERNEWS, "search_by_date", 3, occurred_at=NOW)
    cost = await operating_cost(session, CostPeriod.WEEK, now=NOW)
    assert cost.measured.total_usd == 0.0
    assert cost.measured.unknown_price_events == 1


async def test_period_window_excludes_older_events(session):
    old = NOW - timedelta(days=10)
    await record_usage(session, Provider.BRAVE_SEARCH, "search", 100, occurred_at=old)

    week = await operating_cost(session, CostPeriod.WEEK, now=NOW)
    month = await operating_cost(session, CostPeriod.MONTH, now=NOW)

    assert week.measured.providers == []
    assert week.measured_since == old
    assert month.measured.total_usd == 0.5


# --- ruta ---------------------------------------------------------------------------------


async def test_costs_route(session):
    await record_usage(session, Provider.YOUTUBE, "playlistItems.list", 4, calls=4)

    async def override():
        yield session

    app.dependency_overrides[get_session] = override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            body = (await client.get("/api/v1/costs", params={"period": "30d"})).json()
            invalid = await client.get("/api/v1/costs", params={"period": "1y"})
    finally:
        app.dependency_overrides.clear()

    assert invalid.status_code == 422
    assert body["period"] == "30d"
    assert body["currency"] == "USD"
    assert body["measured"]["providers"] == [
        {
            "provider": "youtube",
            "unit": "quota_units",
            "units": 4.0,
            "calls": 4,
            "cost_usd": 0.0,
            "unknown_price_events": 0,
        }
    ]
    assert body["projection"]["demo"]["total_usd"] == 5.0
    assert body["projection"]["production"]["total_usd"] == 50.0
