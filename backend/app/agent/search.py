"""Tools de búsqueda de piezas del agente (plan fe-radar-agent, D1): buscan como Explorar y lo abren
con la misma búsqueda.
"""

import unicodedata
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import labels
from app.agent.sanitize import clean_external
from app.agent.tool_base import (
    NO_DATA_MESSAGE,
    OK_CONTENT,
    EvidenceRow,
    Seen,
    ToolInput,
    ToolOutcome,
    as_data,
    tool_error,
)
from app.schemas.agent import MAX_SEARCH_CHARS, AgentScreen, Navigation, StepKind
from app.schemas.opportunity import TopicEvidence
from app.services import opportunities

MAX_SEARCH_ROWS = 8
# Con una sola letra casi todo coincide: la búsqueda no enseñaría nada.
MIN_QUERY_CHARS = 2
# Marcas diacríticas sin espacio propio: lo que NFD separa de su letra ("ó" → "o" + U+0301).
COMBINING_MARK = "Mn"

SearchArg = Annotated[str, Field(max_length=MAX_SEARCH_CHARS), AfterValidator(clean_external)]


class SearchInput(ToolInput):
    query: SearchArg = Field(min_length=MIN_QUERY_CHARS)
    limit: int = Field(default=MAX_SEARCH_ROWS, ge=1, le=MAX_SEARCH_ROWS)


class ShowPiecesInput(ToolInput):
    search: SearchArg = Field(min_length=1)


class SearchRow(EvidenceRow):
    opportunity_id: str
    topic: str


class SearchResult(BaseModel):
    # El total y no solo las filas: la etiqueta del paso dice cuántas hay y la respuesta cuadra.
    total: int
    pieces: list[SearchRow]


def _fold(text: str) -> str:
    # Como `foldForSearch` de frontend/src/lib/exploreView.ts: el agente encuentra lo mismo que
    # la persona en Explorar, con o sin tildes y mayúsculas.
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(c for c in decomposed if unicodedata.category(c) != COMBINING_MARK).casefold()


def _matching_pieces(evidence: list[TopicEvidence], query: str) -> list[TopicEvidence]:
    needle = _fold(query)
    # Una URL puede estar en la evidencia de varios temas: se queda la primera, como en Explorar.
    by_url: dict[str, TopicEvidence] = {}
    for e in evidence:
        if needle in _fold(e.title) or needle in _fold(e.source):
            by_url.setdefault(str(e.url), e)
    return list(by_url.values())


async def search_pieces(args: SearchInput, session: AsyncSession, seen: Seen) -> ToolOutcome:
    evidence = await opportunities.list_all_evidence(session)
    listed = await opportunities.list_opportunities(session)
    if evidence is None or listed is None:
        return tool_error(StepKind.DATA, labels.SEARCH_PENDING_LABEL, NO_DATA_MESSAGE)
    by_id = {o.id: o for o in listed.items}
    # Como Explorar: una pieza de un tema que no está en el listado no tiene tema al que atribuirla.
    attributed = [e for e in evidence if e.opportunity_id in by_id]
    found = _matching_pieces(attributed, args.query)
    shown = found[: args.limit]
    rows = [
        SearchRow.model_validate({**e.model_dump(), "topic": by_id[e.opportunity_id].topic})
        for e in shown
    ]
    for e in shown:
        seen.add(by_id[e.opportunity_id])
        seen.evidence_urls.add(str(e.url))
    result = SearchResult(total=len(found), pieces=rows)
    return ToolOutcome(StepKind.DATA, labels.search_label(len(found)), as_data(result))


async def show_pieces(args: ShowPiecesInput, session: AsyncSession, seen: Seen) -> ToolOutcome:
    navigate = Navigation(screen=AgentScreen.EXPLORE, search=args.search)
    return ToolOutcome(StepKind.VIEW, labels.EXPLORE_LABEL, OK_CONTENT, navigate=navigate)
