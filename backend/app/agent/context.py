"""Contexto de la conversación con Rad y paso de vista de respaldo (plan fe-radar-agent, D2 y D4).

El contexto lleva lo que la persona ve y lo que preguntó antes, nunca las respuestas del modelo.
Los nombres de tema salen de la ejecución servida y los ids que no están en ella se descartan.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import labels
from app.agent.tools import MAX_HIGHLIGHTED, OK_CONTENT, ToolOutcome
from app.schemas.agent import (
    AgentQuestion,
    AgentScreen,
    AgentViewContext,
    CitedOpportunity,
    DossierSection,
    Navigation,
    RadarPatch,
    StepKind,
)
from app.schemas.opportunity import Opportunity
from app.services import opportunities

# D4: si la persona está en el expediente de un tema citado, el respaldo baja a su encaje.
FALLBACK_SECTION = DossierSection.FIT


def _topic_ref(o: Opportunity) -> dict[str, str]:
    return {"id": o.id, "topic": o.topic, "lifecycle": o.lifecycle.value}


async def build_context(body: AgentQuestion, session: AsyncSession) -> dict[str, object] | None:
    if not (body.history or body.focus_ids or body.view):
        return None
    listed = await opportunities.list_opportunities(session)
    served = {o.id: o for o in listed.items} if listed else {}
    in_focus = [_topic_ref(served[i]) for i in body.focus_ids if i in served]
    view = body.view
    if not (body.history or in_focus or view):
        return None
    opened = served.get(view.opportunity_id) if view and view.opportunity_id else None
    filters = view.filters if view else None
    # Claves en español: las lee el modelo.
    return {
        "preguntas_anteriores": body.history,
        "en_foco": in_focus,
        "pantalla": view.screen.value if view else None,
        "tema_abierto": _topic_ref(opened) if opened else None,
        "busqueda": view.search if view else None,
        "filtros": filters.model_dump(mode="json", exclude_none=True) if filters else None,
    }


def _opened_and_cited(
    cited: list[CitedOpportunity], view: AgentViewContext | None
) -> CitedOpportunity | None:
    if view is None or view.screen is not AgentScreen.DOSSIER:
        return None
    return next((c for c in cited if c.id == view.opportunity_id), None)


def fallback_view(cited: list[CitedOpportunity], view: AgentViewContext | None) -> ToolOutcome:
    opened = _opened_and_cited(cited, view)
    if opened is not None:
        navigate = Navigation(
            screen=AgentScreen.DOSSIER, opportunity_id=opened.id, section=FALLBACK_SECTION
        )
        label = labels.section_label(FALLBACK_SECTION, opened.topic)
        return ToolOutcome(StepKind.VIEW, label, OK_CONTENT, navigate=navigate)
    ids = [c.id for c in cited][:MAX_HIGHLIGHTED]
    patch = RadarPatch(highlight=ids, selected=ids[0])
    return ToolOutcome(StepKind.VIEW, labels.cited_label(len(ids)), OK_CONTENT, patch=patch)
