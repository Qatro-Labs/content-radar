"""Tools del agente del Radar, una a una: datos, filtros, expediente y búsqueda (planes
data-radar-agent y fe-radar-agent).
"""

import pytest

from app.agent.tool_base import Seen
from app.agent.tools import execute_tool
from app.schemas.agent import AgentScreen, DossierSection, Navigation, StepKind

SEEDED_TOPIC = "[MOCK] Agentes de IA en operaciones empresariales"


async def test_list_tool_filters_and_records_seen_ids(session, seeded):
    seen = Seen()

    outcome = await execute_tool("list_opportunities", {"lifecycle": ["emerging"]}, session, seen)

    assert outcome.kind is StepKind.DATA
    assert not outcome.is_error
    assert outcome.content.startswith("<datos>")
    assert '"opp_002"' in outcome.content
    assert '"opp_001"' not in outcome.content
    assert set(seen.opportunities) == {"opp_002"}


async def test_list_tool_filters_by_recommendation_before_the_limit(session, seeded):
    # En producción, 2 de los 4 «publicar ya» quedaban fuera del top 10 y el agente decía que
    # había solo dos: el filtro tiene que ir antes del corte.
    args = {"recommendation": ["find_angle"], "limit": 1}

    outcome = await execute_tool("list_opportunities", args, session, Seen())

    assert not outcome.is_error
    assert '"opp_001"' not in outcome.content  # publish_now, primero por score
    assert '"opp_002"' in outcome.content or '"opp_003"' in outcome.content


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


# Lo que quita `counterPatch` del front antes de poner el contador (frontend/src/lib/radarView.ts).
COUNTER_CLEARS = {"gap": False, "highlight": [], "confidence": None, "topic": None}


@pytest.mark.parametrize(
    ("args", "label", "patch"),
    [
        (
            {"recommendation": "publish_now"},
            "Pulsando «Publicar ya»",
            {**COUNTER_CLEARS, "lifecycle": [], "recommendation": "publish_now"},
        ),
        # Con «Publicar ya» pulsado, el parche sin `recommendation: null` dejaba las dos cosas
        # puestas y ningún contador pulsado: el rótulo mentía.
        (
            {"lifecycle": ["accelerating"]},
            "Pulsando «Acelerando»",
            {**COUNTER_CLEARS, "lifecycle": ["accelerating"], "recommendation": None},
        ),
        (
            {"lifecycle": ["peaking", "saturated"]},
            "Filtrando por En pico, Saturado",
            {"lifecycle": ["peaking", "saturated"]},
        ),
        # Ordenar por oportunidad es el orden por defecto: el contador sigue siendo lo que pulsa.
        (
            {"recommendation": "publish_now", "sort": "opportunity"},
            "Pulsando «Publicar ya»",
            {
                **COUNTER_CLEARS,
                "lifecycle": [],
                "recommendation": "publish_now",
                "sort": "opportunity",
            },
        ),
    ],
    ids=["publish-now-counter", "accelerating-counter", "several-stages", "counter-default-sort"],
)
async def test_set_filters_presses_the_counter_it_names(session, seeded, args, label, patch):
    outcome = await execute_tool("set_filters", args, session, Seen())

    assert outcome.label == label
    assert outcome.patch is not None
    assert outcome.patch.model_dump(mode="json", exclude_unset=True) == patch


async def test_reset_view_patch(session, seeded):
    outcome = await execute_tool("reset_view", {}, session, Seen())

    assert outcome.patch is not None
    # El mismo parche que `resetViewPatch()` en frontend/src/lib/radarQuery.ts (plan
    # fe-radar-agent, D5).
    assert outcome.patch.model_dump(mode="json", exclude_unset=True) == {
        "lifecycle": [],
        "gap": False,
        "highlight": [],
        "recommendation": None,
        "confidence": None,
        "topic": None,
    }


async def test_show_in_dossier_navigates_to_the_section(session, seeded):
    args = {"id": "opp_001", "section": "evidence"}

    outcome = await execute_tool("show_in_dossier", args, session, Seen())

    assert outcome.kind is StepKind.VIEW
    assert not outcome.is_error
    assert outcome.label == f"Mostrando la evidencia de «{SEEDED_TOPIC}»"
    assert outcome.navigate == Navigation(
        screen=AgentScreen.DOSSIER, opportunity_id="opp_001", section=DossierSection.EVIDENCE
    )


async def test_show_in_dossier_rejects_unknown_id(session, seeded):
    outcome = await execute_tool("show_in_dossier", {"id": "opp_nope"}, session, Seen())

    assert outcome.kind is StepKind.VIEW
    assert outcome.is_error
    assert outcome.navigate is None


async def test_search_pieces_ignores_accents_and_case(session, seeded):
    seen = Seen()
    query = "AUTOMATIZO EL CIERRE"

    outcome = await execute_tool("search_pieces", {"query": query}, session, seen)

    assert outcome.kind is StepKind.DATA
    assert not outcome.is_error
    assert outcome.content.startswith("<datos>")
    assert "Cómo un CFO automatizó el cierre mensual" in outcome.content
    assert set(seen.opportunities) == {"opp_001"}
    assert seen.evidence_urls == {"https://example.com/mock/1"}
    assert outcome.label == "Buscando piezas: 1 encontrada"
    # El modelo ve el total, no solo las filas: así su respuesta cuadra con la etiqueta del paso.
    assert '"total": 1' in outcome.content
    assert "cierre" not in outcome.label.lower()


async def test_show_pieces_opens_explore_with_a_clean_search(session, seeded):
    outcome = await execute_tool("show_pieces", {"search": "<b>agentes</b>"}, session, Seen())

    assert outcome.kind is StepKind.VIEW
    assert outcome.navigate is not None
    assert outcome.navigate.model_dump(mode="json", exclude_unset=True) == {
        "screen": "explore",
        "search": "＜b＞agentes＜/b＞",
    }


@pytest.mark.parametrize(
    ("name", "args"),
    [
        ("drop_table", {}),
        ("list_opportunities", {"limit": 3, "sql": "select 1"}),
        ("set_filters", {"topic": "x" * 61}),
        ("select_opportunity", {"id": "../etc/passwd"}),
        ("search_pieces", {"query": "a"}),
        ("show_in_dossier", {"id": "opp_001", "section": "cover"}),
    ],
    ids=[
        "unknown-tool",
        "extra-field",
        "long-topic",
        "bad-id-format",
        "one-char-search",
        "unknown-section",
    ],
)
async def test_invalid_tool_input_is_rejected(session, seeded, name, args):
    outcome = await execute_tool(name, args, session, Seen())

    assert outcome.is_error
    assert outcome.patch is None
    assert outcome.navigate is None
    assert "drop_table" not in outcome.content
    assert "passwd" not in outcome.content
