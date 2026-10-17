"""Servidor MCP: tools por el cliente en memoria del SDK, contra radar_test.

Cada test entra en `async with Client(...)` en su propio cuerpo: un fixture que hiciera `yield`
dentro falla en el teardown (anyio cierra sus task groups en otra tarea).
"""

import asyncio
import dataclasses
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from mcp import Client
from mcp.types import CallToolResult, TextContent
from sqlalchemy import select

from app.agent.limits import LimitResult, RateLimiter
from app.agent.sanitize import clean_tree
from app.collectors.usage import UsageMeter
from app.mcp.server import McpDeps, build_mcp_server, transport_security
from app.mcp.tools import COVERAGE_NOTE, MCP_BRIEF_LIMITS, NO_DATA
from app.models import UsageEvent
from app.schemas.cost import CostPeriod, Provider
from app.services import costs
from app.services.costs import record_meter
from app.services.opportunities import get_served
from tests.test_editorial_brief import FakeBriefer, seed
from tests.test_opportunity_routes import add_run, fixture_results
from tests.test_search_signals import item, source

LOCAL_HOSTS = ["127.0.0.1:*", "localhost:*", "[::1]:*"]
LOCAL_ORIGINS = ["http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*"]


def deps(
    session, *, briefer: FakeBriefer | None = None, limiter: RateLimiter | None = None
) -> McpDeps:
    @asynccontextmanager
    async def test_session():
        yield session

    return McpDeps(
        session_factory=test_session,
        briefer=briefer or FakeBriefer(),
        brief_limiter=limiter or RateLimiter(per_ip_per_hour=20, global_per_day=100),
        brief_slots=asyncio.Semaphore(2),
    )


def text_of(result: CallToolResult) -> str:
    return " ".join(c.text for c in result.content if isinstance(c, TextContent))


def structured(result: CallToolResult) -> dict[str, Any]:
    assert not result.is_error, text_of(result)
    assert result.structured_content is not None
    return result.structured_content


async def test_trending_keeps_the_served_rank_and_carries_evidence_urls(session):
    results = fixture_results()
    await add_run(session, fixture_results())

    async with Client(build_mcp_server(deps(session))) as c:
        out = structured(await c.call_tool("get_trending_opportunities", {"limit": 3}))

    assert [o["id"] for o in out["items"]] == [r.opportunity.id for r in results[:3]]
    assert out["matched"] == 5
    first = out["items"][0]
    assert first["id"] == "opp_001"
    assert [e["is_outlier"] for e in first["top_evidence"][:2]] == [True, True]
    opp_001_urls = {str(e.url) for e in results[0].evidence}
    assert {e["url"] for e in first["top_evidence"]} <= opp_001_urls


async def test_trending_never_pads(session):
    await add_run(session, fixture_results())

    async with Client(build_mcp_server(deps(session))) as c:
        out = structured(await c.call_tool("get_trending_opportunities", {"limit": 10}))

    assert len(out["items"]) == 5


async def test_trending_filter_without_match_is_an_empty_list(session):
    await add_run(session, fixture_results())

    async with Client(build_mcp_server(deps(session))) as c:
        out = structured(await c.call_tool("get_trending_opportunities", {"topic": "zzz"}))

    assert out["items"] == []
    assert out["matched"] == 0


@pytest.mark.parametrize(
    ("tool", "args"),
    [
        ("get_trending_opportunities", {}),
        ("analyze_opportunity", {"opportunity_id": "opp_001"}),
    ],
    ids=["trending", "analyze"],
)
async def test_without_any_run_tools_say_there_is_no_data(session, tool, args):
    async with Client(build_mcp_server(deps(session))) as c:
        result = await c.call_tool(tool, args)

    assert result.is_error
    assert NO_DATA in text_of(result)


async def test_analyze_matches_the_rest_detail(session):
    await add_run(session, fixture_results())
    served = await get_served(session, "opp_001")
    assert served is not None

    async with Client(build_mcp_server(deps(session))) as c:
        out = structured(await c.call_tool("analyze_opportunity", {"opportunity_id": "opp_001"}))

    # Comparado con lo saneado: los `lifecycle_reason` de la fixture llevan `<` y salen como `＜`.
    assert out["opportunity"] == clean_tree(served.opportunity.model_dump(mode="json"))
    assert out["timeline"] == clean_tree(served.timeline.model_dump(mode="json"))
    # En la fixture la evidencia ya está con los outliers primero: [True, True, None].
    assert out["evidence"] == clean_tree([e.model_dump(mode="json") for e in served.evidence])
    assert out["evidence_total"] == 3


@pytest.mark.parametrize(
    ("opportunity_id", "named"),
    # Un id malformado no llega a la DB: lo rechaza el schema de la tool, que nombra el argumento.
    [("opp_999", "opp_999"), ("DROP TABLE", "opportunity_id")],
    ids=["unknown", "malformed"],
)
async def test_analyze_rejects_unknown_and_malformed_ids(session, opportunity_id, named):
    await add_run(session, fixture_results())

    async with Client(build_mcp_server(deps(session))) as c:
        result = await c.call_tool("analyze_opportunity", {"opportunity_id": opportunity_id})

    assert result.is_error
    assert named in text_of(result)


async def test_external_text_is_sanitized(session):
    results = fixture_results()
    results[0].opportunity = results[0].opportunity.model_copy(update={"topic": "<b>Agentes</b>​"})
    await add_run(session, results)

    async with Client(build_mcp_server(deps(session))) as c:
        out = structured(await c.call_tool("get_trending_opportunities", {"limit": 1}))

    topic = out["items"][0]["topic"]
    assert not {"<", ">", "​"} & set(topic)
    assert "＜" in topic and "＞" in topic


@pytest.mark.parametrize(
    ("public_url", "hosts", "origins"),
    [
        ("", [], []),
        (
            "https://radar.up.railway.app/mcp",
            ["radar.up.railway.app", "radar.up.railway.app:*"],
            ["https://radar.up.railway.app"],
        ),
        ("http://localhost:8000/mcp", ["localhost:8000"], ["http://localhost:8000"]),
    ],
    ids=["unset", "railway", "with-port"],
)
def test_transport_security_follows_the_public_url(public_url, hosts, origins):
    settings = transport_security(public_url)

    assert settings.enable_dns_rebinding_protection
    assert set(settings.allowed_hosts) == {*LOCAL_HOSTS, *hosts}
    assert set(settings.allowed_origins) == {*LOCAL_ORIGINS, *origins}


def test_invalid_public_url_fails_at_startup():
    with pytest.raises(ValueError, match="MCP_PUBLIC_URL"):
        transport_security("radar.example")


async def test_search_through_mcp_returns_urls_and_coverage(session):
    yesterday = datetime.now(UTC) - timedelta(days=1)
    found = item(source(), "Agentes en la empresa", published_at=yesterday)
    session.add(found)
    await session.commit()

    async with Client(build_mcp_server(deps(session))) as c:
        out = structured(await c.call_tool("search_content_signals", {"query": "agentes"}))

    assert [h["url"] for h in out["items"]] == [found.url]
    assert out["coverage"] == COVERAGE_NOTE


async def test_compare_keeps_requested_order_and_null_fit(session):
    await add_run(session, fixture_results())

    async with Client(build_mcp_server(deps(session))) as c:
        result = await c.call_tool(
            "compare_audience_fit", {"opportunity_ids": ["opp_005", "opp_001"]}
        )

    unevaluated, evaluated = structured(result)["items"]
    assert (unevaluated["id"], evaluated["id"]) == ("opp_005", "opp_001")
    assert unevaluated["audience_fit_score"] is None
    assert unevaluated["audience_fit_criteria"] is None
    assert len(evaluated["audience_fit_criteria"]) == 6


async def test_compare_names_unknown_ids(session):
    await add_run(session, fixture_results())

    async with Client(build_mcp_server(deps(session))) as c:
        result = await c.call_tool(
            "compare_audience_fit", {"opportunity_ids": ["opp_001", "opp_999"]}
        )

    assert result.is_error
    assert "opp_999" in text_of(result)


@pytest.mark.parametrize("count", [1, 6], ids=["one", "six"])
async def test_compare_needs_two_to_five_ids(session, count):
    await add_run(session, fixture_results())
    # Todos existen: solo el límite del schema puede rechazarlos (el sexto se repetiría).
    ids = ["opp_001", "opp_002", "opp_003", "opp_004", "opp_005", "opp_001"][:count]

    async with Client(build_mcp_server(deps(session))) as c:
        result = await c.call_tool("compare_audience_fit", {"opportunity_ids": ids})

    assert result.is_error
    assert "opportunity_ids" in text_of(result)


async def test_operating_cost_matches_the_service(session):
    meter = UsageMeter()
    meter.add(Provider.LLM_TEXT, "evaluate_topic", units=600, output_units=200)
    await record_meter(session, meter)

    async with Client(build_mcp_server(deps(session))) as c:
        out = structured(await c.call_tool("get_operating_cost", {}))
    expected = (
        await costs.operating_cost(session, CostPeriod.WEEK, now=datetime.now(UTC))
    ).model_dump(mode="json")

    assert out["period"] == expected["period"] == "7d"
    assert out["measured"]["total_usd"] == expected["measured"]["total_usd"]
    assert out["measured"]["providers"] == expected["measured"]["providers"]


def brief_args(opportunity_id: str) -> dict[str, str]:
    return {
        "opportunity_id": opportunity_id,
        "platform": "linkedin",
        "goal": "educate",
        "format": "carousel",
    }


async def usage_events(session) -> list[UsageEvent]:
    return list((await session.scalars(select(UsageEvent))).all())


async def test_lists_the_six_tools_with_descriptions_and_hints(session):
    async with Client(build_mcp_server(deps(session))) as c:
        tools = (await c.list_tools()).tools

    assert {t.name for t in tools} == {
        "get_trending_opportunities",
        "analyze_opportunity",
        "search_content_signals",
        "compare_audience_fit",
        "get_operating_cost",
        "generate_editorial_brief",
    }
    assert all(t.description and t.output_schema for t in tools)
    read_only = {t.name: bool(t.annotations and t.annotations.read_only_hint) for t in tools}
    assert [name for name, hint in read_only.items() if not hint] == ["generate_editorial_brief"]


async def test_brief_through_mcp_matches_the_service_and_records_usage(session):
    opportunity_id = await seed(session)
    served = await get_served(session, opportunity_id)
    assert served is not None

    async with Client(build_mcp_server(deps(session))) as c:
        out = structured(await c.call_tool("generate_editorial_brief", brief_args(opportunity_id)))

    assert out["opportunity_id"] == opportunity_id
    evidence_urls = {str(e.url) for e in served.evidence}
    cited = {url for point in out["key_points"] for url in point["evidence_urls"]}
    assert cited and cited <= evidence_urls
    assert len(await usage_events(session)) == 1


async def test_rejected_brief_is_an_error_and_its_usage_is_recorded(session):
    opportunity_id = await seed(session)
    server = build_mcp_server(deps(session, briefer=FakeBriefer(angle="El 70 % ya delega.")))

    async with Client(server) as c:
        result = await c.call_tool("generate_editorial_brief", brief_args(opportunity_id))

    assert result.is_error
    assert len(await usage_events(session)) == 1


async def test_brief_without_llm_is_an_error(session):
    opportunity_id = await seed(session)
    server = build_mcp_server(dataclasses.replace(deps(session), briefer=None))

    async with Client(server) as c:
        result = await c.call_tool("generate_editorial_brief", brief_args(opportunity_id))

    assert result.is_error
    assert "falta configurar el LLM" in text_of(result)


async def test_brief_limit_is_an_error_without_calling_the_llm(session):
    opportunity_id = await seed(session)
    briefer = FakeBriefer()
    limiter = RateLimiter(per_ip_per_hour=1, global_per_day=100)
    server = build_mcp_server(deps(session, briefer=briefer, limiter=limiter))

    async with Client(server) as c:
        first = await c.call_tool("generate_editorial_brief", brief_args(opportunity_id))
        second = await c.call_tool("generate_editorial_brief", brief_args(opportunity_id))

    assert not first.is_error, text_of(first)
    assert second.is_error
    assert MCP_BRIEF_LIMITS[LimitResult.IP] in text_of(second)
    assert briefer.calls == 1
