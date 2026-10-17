"""Rutas REST de oportunidades contra la DB de tests, sembradas con el fixture del frontend."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings
from app.db.session import get_session
from app.intelligence.lifecycle import Stage
from app.intelligence.opportunities import TopicResult
from app.main import app
from app.models import PipelineRun
from app.schemas.opportunity import Evidence, Lifecycle, Opportunity, OpportunityTimeline
from app.services import opportunities
from app.services.opportunities import ANALYZE_JOB, save_opportunities

FIXTURE = Path(__file__).resolve().parents[2] / "data" / "fixtures" / "opportunities.json"
FINISHED_AT = datetime(2026, 10, 17, 12, tzinfo=UTC)


def fixture_results() -> list[TopicResult]:
    raw = json.loads(FIXTURE.read_text())
    return [
        TopicResult(
            opportunity=Opportunity.model_validate(o),
            evidence=[Evidence.model_validate(e) for e in raw["evidence"][o["id"]]],
            timeline=OpportunityTimeline.model_validate(raw["timeline"][o["id"]]),
            stage=Stage(Lifecycle(o["lifecycle"]), o["lifecycle_reason"]),
            pieces=[],
        )
        for o in raw["opportunities"]["items"]
    ]


async def add_run(session, results, *, status="success", finished_at=FINISHED_AT) -> int:
    run = PipelineRun(job=ANALYZE_JOB, status=status, finished_at=finished_at)
    session.add(run)
    await session.flush()
    await save_opportunities(session, run.id, results)
    await session.commit()
    return run.id


@pytest.fixture
async def client(session):
    async def override():
        yield session

    app.dependency_overrides[get_session] = override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
async def seeded(session):
    await add_run(session, fixture_results())


async def test_list_is_null_before_any_analyze_run(client):
    response = await client.get("/api/v1/opportunities")
    assert response.status_code == 200
    assert response.json() is None


async def test_list_serves_latest_successful_run_in_rank_order(session, client):
    results = fixture_results()
    await add_run(session, results[:1], finished_at=datetime(2026, 10, 16, tzinfo=UTC))
    await add_run(session, results)
    newer_failed = datetime(2026, 10, 18, tzinfo=UTC)
    await add_run(session, results[:2], status="failed", finished_at=newer_failed)

    body = (await client.get("/api/v1/opportunities")).json()

    assert [o["id"] for o in body["items"]] == [r.opportunity.id for r in results]
    assert body["period"] == "7d"
    assert body["generated_at"] == "2026-10-17T12:00:00Z"
    assert body["monitoring_started_at"] == "2026-10-16T00:00:00Z"


@pytest.fixture
def demo_run(monkeypatch):
    def pin(run_id: int | None) -> None:
        settings = Settings(demo_run_id=run_id)
        monkeypatch.setattr(opportunities, "get_settings", lambda: settings)

    return pin


async def test_demo_run_is_served_instead_of_the_latest(session, client, demo_run):
    results = fixture_results()
    demo = await add_run(session, results[:2], finished_at=datetime(2026, 10, 16, tzinfo=UTC))
    await add_run(session, results)
    demo_run(demo)

    body = (await client.get("/api/v1/opportunities")).json()
    detail = await client.get(f"/api/v1/opportunities/{results[2].opportunity.id}")

    assert [o["id"] for o in body["items"]] == [r.opportunity.id for r in results[:2]]
    # El detalle sale de la misma ejecución: lo que no está en la demo no existe.
    assert detail.status_code == 404


async def test_demo_run_that_failed_is_not_served(session, client, demo_run):
    failed = await add_run(session, fixture_results(), status="failed")
    await add_run(session, fixture_results())
    demo_run(failed)

    assert (await client.get("/api/v1/opportunities")).json() is None


def test_empty_demo_run_id_means_unset():
    assert Settings.model_validate({"demo_run_id": ""}).demo_run_id is None


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        ({"lifecycle": "emerging"}, ["opp_002"]),
        ({"confidence": "high"}, ["opp_001", "opp_003"]),
        ({"topic": "AGENTES"}, ["opp_001"]),
        ({"confidence": "high", "lifecycle": "peaking"}, ["opp_003"]),
        ({"lifecycle": "saturated", "confidence": "high"}, []),
    ],
    ids=["lifecycle", "confidence", "topic-case-insensitive", "combined", "no-match"],
)
async def test_list_filters(seeded, client, params, expected):
    body = (await client.get("/api/v1/opportunities", params=params)).json()
    assert [o["id"] for o in body["items"]] == expected


async def test_list_rejects_unknown_filter_values(seeded, client):
    response = await client.get("/api/v1/opportunities", params={"lifecycle": "viral"})
    assert response.status_code == 422


async def test_detail_evidence_and_timeline(seeded, client):
    detail = (await client.get("/api/v1/opportunities/opp_002")).json()
    evidence = (await client.get("/api/v1/opportunities/opp_002/evidence")).json()
    timeline = (await client.get("/api/v1/opportunities/opp_002/timeline")).json()

    assert detail["topic"] == "[MOCK] Modelos pequeños en el dispositivo"
    assert detail["lifecycle"] == "emerging"
    raw = json.loads(FIXTURE.read_text())
    assert [e["url"] for e in evidence] == [e["url"] for e in raw["evidence"]["opp_002"]]
    assert timeline["opportunity_id"] == "opp_002"
    assert len(timeline["points"]) == len(raw["timeline"]["opp_002"]["points"])


@pytest.mark.parametrize(
    "suffix", ["", "/evidence", "/timeline"], ids=["detail", "evidence", "timeline"]
)
async def test_missing_opportunity_is_404(seeded, client, suffix):
    response = await client.get(f"/api/v1/opportunities/opp_999{suffix}")
    assert response.status_code == 404


@pytest.mark.parametrize(
    "path", ["/api/v1/evidence", "/api/v1/timelines"], ids=["evidence", "timelines"]
)
async def test_bulk_reads_are_null_before_any_analyze_run(client, path):
    response = await client.get(path)
    assert response.status_code == 200
    assert response.json() is None


async def test_all_evidence_strongest_outlier_first_and_nulls_last(seeded, client):
    body = (await client.get("/api/v1/evidence")).json()

    # Ratios del fixture; los nulos van al final, de la más reciente a la más antigua.
    assert [(e["opportunity_id"], e["outlier_ratio"]) for e in body] == [
        ("opp_001", 6.1),
        ("opp_001", 3.4),
        ("opp_002", 2.2),
        ("opp_003", 1.8),
        ("opp_004", 0.6),
        ("opp_005", None),  # 17/10 07:00
        ("opp_002", None),  # 15/10 12:00
        ("opp_003", None),  # 15/10 11:00, la republicación MOCK
        ("opp_001", None),  # 15/10 10:00
        ("opp_003", None),  # 15/10 09:00
    ]
    raw = json.loads(FIXTURE.read_text())
    expected = {(opp, e["url"]) for opp, items in raw["evidence"].items() for e in items}
    assert {(e["opportunity_id"], e["url"]) for e in body} == expected


async def test_timelines_follow_rank_order(session, client):
    reversed_rank = fixture_results()[::-1]
    await add_run(session, reversed_rank)

    body = (await client.get("/api/v1/timelines")).json()

    assert [t["opportunity_id"] for t in body] == [
        "opp_005",
        "opp_004",
        "opp_003",
        "opp_002",
        "opp_001",
    ]
    assert all(len(t["points"]) == 6 for t in body)


async def test_bulk_reads_serve_the_demo_run(session, client, demo_run):
    results = fixture_results()
    demo = await add_run(session, results[:2], finished_at=datetime(2026, 10, 16, tzinfo=UTC))
    await add_run(session, results)
    demo_run(demo)

    evidence = (await client.get("/api/v1/evidence")).json()
    timelines = (await client.get("/api/v1/timelines")).json()

    assert {e["opportunity_id"] for e in evidence} == {"opp_001", "opp_002"}
    assert [t["opportunity_id"] for t in timelines] == ["opp_001", "opp_002"]


async def test_list_served_keeps_rank_and_carries_evidence_and_timeline(session):
    expected = fixture_results()
    await add_run(session, fixture_results())

    served = await opportunities.list_served(session)

    assert served is not None
    assert served.generated_at == FINISHED_AT
    assert [s.opportunity.id for s in served.items] == [r.opportunity.id for r in expected]
    assert [s.evidence for s in served.items] == [r.evidence for r in expected]
    assert [s.timeline for s in served.items] == [r.timeline for r in expected]


async def test_list_served_applies_the_same_filters_as_the_list(session):
    await add_run(session, fixture_results())

    served = await opportunities.list_served(session, lifecycle=Lifecycle.ACCELERATING)
    listed = await opportunities.list_opportunities(session, lifecycle=Lifecycle.ACCELERATING)

    assert served is not None and listed is not None
    assert [s.opportunity.id for s in served.items] == ["opp_001"]
    assert [o.id for o in listed.items] == ["opp_001"]


async def test_list_served_is_none_before_any_analyze_run(session):
    assert await opportunities.list_served(session) is None
