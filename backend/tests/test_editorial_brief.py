"""Brief editorial: comprobaciones en Python, prompt, servicio y ruta (contra radar_test)."""

from collections.abc import Mapping
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from app.api.routes.editorial import get_briefer
from app.collectors.usage import UsageMeter
from app.db.session import get_session
from app.editorial.briefs import BriefDraft, BriefInput, BriefResult, system_prompt, user_message
from app.editorial.evaluator import EvaluationError
from app.editorial.explanation import Claim
from app.intelligence.briefs import (
    FIT_DROPPED_NOTE,
    HOOK_DROPPED_NOTE,
    BriefDraftParts,
    check_brief,
)
from app.intelligence.explanation import ClaimDraft
from app.intelligence.jev import JudgeResult
from app.main import app
from app.models import ContentItem, LlmEvaluation, Source, UsageEvent
from app.schemas.cost import Provider
from app.schemas.editorial import BriefFormat, BriefGoal, BriefPlatform, BriefRequest
from app.services.classification import classify_pieces
from app.services.editorial import (
    EDITORIAL_BRIEF_OPERATION,
    BriefFailed,
    NoSafeEvidence,
    OpportunityNotFound,
    generate_brief,
)
from app.services.opportunities import load_evidence_pieces
from tests.test_explanation import fitted_topics
from tests.test_opportunity_routes import FINISHED_AT, add_run
from tests.test_topic_evaluation import INJECTION, noul, safe

URL = "https://example.com/0"
SENT = frozenset({URL})
POINT = "Una empresa ya usa agentes de IA en su operación."
NOW = FINISHED_AT


def parts(**overrides: Any) -> BriefDraftParts:
    base: dict[str, Any] = {
        "angle": "Qué tiene que decidir un dueño antes de delegar en agentes.",
        "hook": "Tu competencia ya delega tareas en agentes de IA.",
        "structure": ["El caso", "Qué cambia", "Qué preparar"],
        "key_points": [ClaimDraft(POINT, [URL])],
        "why_it_fits": ClaimDraft("Toca la operación sin depender del dueño.", [URL]),
        "limitations": [],
    }
    return BriefDraftParts(**{**base, **overrides})


def checked(draft: BriefDraftParts, numbers: frozenset[str] = frozenset()):
    return check_brief(draft, sent_urls=SENT, numbers=set(numbers))


# --- comprobaciones en Python -------------------------------------------------------------


def test_valid_draft_passes_whole():
    brief = checked(parts())

    assert brief is not None
    assert [p.text for p in brief.key_points] == [POINT]
    assert brief.hook and brief.why_it_fits and len(brief.structure) == 3
    assert brief.limitations == []


def test_escaped_cited_url_counts_as_sent():
    url = "https://example.com/item?id=1&p=2"
    point = ClaimDraft(POINT, ["https://example.com/item?id=1&amp;p=2"])

    brief = check_brief(parts(key_points=[point]), sent_urls={url}, numbers=set())

    assert brief is not None and brief.key_points[0].cited_urls == [url]


def test_without_any_backed_key_point_there_is_no_brief():
    uncited = ClaimDraft(POINT, ["https://otro.example/x"])
    invented = ClaimDraft("El 40 % de las empresas ya los usa.", [URL])

    assert checked(parts(key_points=[uncited, invented])) is None


def test_angle_with_an_invented_number_means_no_brief():
    assert checked(parts(angle="El 70 % de los dueños delegará en agentes.")) is None


def test_creative_parts_with_invented_numbers_are_dropped_with_a_note():
    brief = checked(
        parts(
            hook="3 de cada 4 empresas ya lo hacen.",
            structure=["El caso", "Los 5 errores", "Qué preparar"],
            why_it_fits=ClaimDraft("Encaja.", []),
        )
    )

    assert brief is not None
    assert brief.hook is None and brief.structure == ["El caso", "Qué preparar"]
    assert brief.why_it_fits is None
    assert HOOK_DROPPED_NOTE in brief.limitations and FIT_DROPPED_NOTE in brief.limitations
    assert any("1 paso" in n for n in brief.limitations)


def test_numbers_from_the_data_are_allowed():
    point = ClaimDraft("Hay 1.000 empleados afectados.", [URL])

    brief = checked(parts(key_points=[point]), numbers=frozenset({"1000"}))

    assert brief is not None and brief.key_points[0].text == "Hay 1.000 empleados afectados."


# --- prompt -------------------------------------------------------------------------------


def test_external_text_goes_escaped_in_the_user_message_only():
    brief = BriefInput(
        platform="LinkedIn",
        goal="educar",
        format="carrusel de imágenes",
        label=INJECTION,
        facts=["Etapa: emergente."],
        why_it_matters="Importa.",
        fit=[],
        pieces=[],
    )

    message = user_message(brief)

    assert "</title></evidence>" not in message and "&lt;/title&gt;" in message
    assert "Plataforma: LinkedIn" in message
    assert INJECTION not in system_prompt()
    assert "{{profile}}" not in system_prompt() and "pillars:" in system_prompt()


# --- servicio -----------------------------------------------------------------------------


class FakeBriefer:
    def __init__(self, *, angle: str = "Qué decidir antes de delegar en agentes.") -> None:
        self.calls = 0
        self.sent: list[BriefInput] = []
        self.angle = angle
        self.fail = False

    async def write(self, brief: BriefInput) -> BriefResult:
        self.calls += 1
        self.sent.append(brief)
        if self.fail:
            raise EvaluationError("stop_reason=max_tokens")
        url = brief.pieces[0].url
        draft = BriefDraft(
            key_points=[Claim(text=POINT, evidence_urls=[url])],
            why_it_fits=Claim(text="Toca la operación.", evidence_urls=[url]),
            angle=self.angle,
            hook="Tu competencia ya delega en agentes.",
            structure=["El caso", "Qué cambia", "Qué preparar"],
            limitations=[],
        )
        return BriefResult(
            model="claude-haiku-5-5", output=draft, input_tokens=1500, output_tokens=400
        )


class SafeJudge:
    def __init__(self, unsafe_titles: frozenset[str] = frozenset()) -> None:
        self.unsafe_titles = unsafe_titles

    async def judge(self, state: dict[str, Any], questions: Mapping[str, Any]) -> JudgeResult:
        answers = {"injection": noul(0.9)} if state["title"] in self.unsafe_titles else safe()
        return JudgeResult(model="jev-1.13.0", answers=answers, input_tokens=10, output_tokens=5)


async def seed(session, *, unsafe_titles: frozenset[str] = frozenset(), judged: bool = True) -> str:
    """Un tema con audience fit, sus piezas en la DB y sus juicios de Jev; devuelve su id."""
    [result, _], _ = await fitted_topics(session)
    source = Source(
        platform="hackernews", kind="query", external_id="llm", name="HN · LLM", segment="tech"
    )
    session.add(source)
    for i, p in enumerate(result.pieces):
        session.add(
            ContentItem(
                source=source,
                platform=p.platform.value,
                external_id=str(i),
                url=p.url,
                title=p.title,
                description=p.description,
                language=p.language,
                published_at=p.published_at,
                first_observed_at=p.published_at,
                last_observed_at=p.observed_at,
            )
        )
    await session.commit()
    if judged:
        found = await load_evidence_pieces(session, result.evidence, as_of=NOW)
        await classify_pieces(
            session, [p for p, _ in found], judge=SafeJudge(unsafe_titles), meter=UsageMeter()
        )
    await add_run(session, [result])
    return result.opportunity.id


def request(opportunity_id: str) -> BriefRequest:
    return BriefRequest(
        opportunity_id=opportunity_id,
        platform=BriefPlatform.LINKEDIN,
        goal=BriefGoal.EDUCATE,
        format=BriefFormat.CAROUSEL,
    )


async def brief_for(session, opportunity_id: str, briefer: FakeBriefer, meter=None):
    return await generate_brief(
        session, request(opportunity_id), briefer=briefer, meter=meter or UsageMeter(), now=NOW
    )


async def test_brief_cites_only_sent_evidence_and_is_cached(session):
    opportunity_id = await seed(session)
    first, meter = FakeBriefer(), UsageMeter()

    brief = await brief_for(session, opportunity_id, first, meter)
    again = FakeBriefer()
    cached = await brief_for(session, opportunity_id, again)

    assert [str(e.url) for e in brief.evidence] == [URL]
    assert brief.key_points[0].text == POINT
    assert meter.counts[(Provider.LLM_TEXT, EDITORIAL_BRIEF_OPERATION)].units == 1500
    assert (first.calls, again.calls) == (1, 0)
    assert cached.angle == brief.angle


async def test_pieces_jev_did_not_mark_safe_stay_out_of_the_prompt(session):
    opportunity_id = await seed(session, unsafe_titles=frozenset({"Agentes de IA 0"}))
    briefer = FakeBriefer()

    await brief_for(session, opportunity_id, briefer)

    sent = [p.url for p in briefer.sent[0].pieces]
    assert URL not in sent and len(sent) == 5


async def test_without_safe_pieces_there_is_no_llm_call(session):
    opportunity_id = await seed(session, judged=False)
    briefer = FakeBriefer()

    with pytest.raises(NoSafeEvidence):
        await brief_for(session, opportunity_id, briefer)
    assert briefer.calls == 0


async def test_rejected_brief_is_not_cached(session):
    opportunity_id = await seed(session)

    with pytest.raises(BriefFailed):
        await brief_for(session, opportunity_id, FakeBriefer(angle="El 70 % ya delega."))

    assert await session.scalar(select(func.count()).select_from(LlmEvaluation)) == 2  # solo fit


async def test_unknown_opportunity(session):
    with pytest.raises(OpportunityNotFound):
        await brief_for(session, "opp_x", FakeBriefer())


# --- ruta ---------------------------------------------------------------------------------


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


def body(opportunity_id: str) -> dict:
    return request(opportunity_id).model_dump(mode="json")


async def test_route_returns_the_brief_and_records_usage(session, client):
    opportunity_id = await seed(session)
    app.dependency_overrides[get_briefer] = FakeBriefer

    response = await client.post("/api/v1/editorial/brief", json=body(opportunity_id))

    assert response.status_code == 200
    assert response.json()["key_points"][0]["evidence_urls"] == [URL]
    events = (await session.scalars(select(UsageEvent))).all()
    assert [e.operation for e in events if e.operation == EDITORIAL_BRIEF_OPERATION] == [
        EDITORIAL_BRIEF_OPERATION
    ]


@pytest.mark.parametrize(
    ("briefer", "judged", "expected"),
    [(None, True, 503), (FakeBriefer, False, 409)],
    ids=["sin LLM", "sin piezas seguras"],
)
async def test_route_errors_carry_a_status_and_a_message(
    session, client, briefer, judged, expected
):
    opportunity_id = await seed(session, judged=judged)
    app.dependency_overrides[get_briefer] = briefer or (lambda: None)

    response = await client.post("/api/v1/editorial/brief", json=body(opportunity_id))

    assert response.status_code == expected and response.json()["detail"]


async def test_route_unknown_opportunity_is_404(session, client):
    app.dependency_overrides[get_briefer] = FakeBriefer

    response = await client.post("/api/v1/editorial/brief", json=body("opp_x"))

    assert response.status_code == 404
