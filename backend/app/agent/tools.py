"""Tools del agente del Radar (plan data-radar-agent, "Tools que ve el modelo").

Las de datos solo leen la ejecución servida a través de `app.services.opportunities`; las de
vista devuelven un parche de la URL del Radar. Ninguna escribe.
"""

import json
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field

from anthropic.types import ToolParam
from pydantic import AwareDatetime, BaseModel, Field, HttpUrl, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import labels
from app.schemas.agent import CitedOpportunity, RadarPatch, RadarSort, StepKind
from app.schemas.opportunity import (
    AudienceMix,
    Confidence,
    GrowthStatus,
    Lifecycle,
    Opportunity,
    Recommendation,
)
from app.schemas.signal import Platform
from app.services import opportunities

MAX_LISTED = 10
MAX_EVIDENCE = 5
MAX_HIGHLIGHTED = 5
FINAL_ANSWER = "final_answer"
OK_CONTENT = "ok"
NO_DATA_MESSAGE = "Todavía no hay oportunidades calculadas."


@dataclass
class Seen:
    """Lo que devolvieron las tools de datos en esta pregunta: lo único que se puede citar."""

    opportunities: dict[str, CitedOpportunity] = field(default_factory=dict)
    evidence_urls: set[str] = field(default_factory=set)

    def add(self, o: Opportunity) -> None:
        self.opportunities[o.id] = CitedOpportunity(
            id=o.id, topic=o.topic, lifecycle=o.lifecycle, opportunity_score=o.opportunity_score
        )


@dataclass(frozen=True)
class ToolOutcome:
    kind: StepKind
    label: str
    content: str
    is_error: bool = False
    patch: RadarPatch | None = None


class ListInput(BaseModel):
    lifecycle: list[Lifecycle] | None = None
    confidence: Confidence | None = None
    topic: str | None = Field(default=None, description="Subcadena del tema")
    latam_gap_only: bool = False
    sort: RadarSort = "opportunity"
    limit: int = Field(default=MAX_LISTED, ge=1, le=MAX_LISTED)


class IdInput(BaseModel):
    id: str


class EvidenceInput(IdInput):
    limit: int = Field(default=MAX_EVIDENCE, ge=1, le=MAX_EVIDENCE)


class FiltersInput(BaseModel):
    lifecycle: list[Lifecycle] | None = None
    confidence: Confidence | None = None
    topic: str | None = None
    gap: bool | None = Field(default=None, description="true = solo «Hueco en LATAM»")
    sort: RadarSort | None = None


class HighlightInput(BaseModel):
    ids: list[str] = Field(min_length=1, max_length=MAX_HIGHLIGHTED)


class NoInput(BaseModel):
    pass


class FinalAnswerInput(BaseModel):
    text: str = Field(description="Respuesta en español, 120 palabras como máximo")
    cited_ids: list[str] = Field(description="Ids de las oportunidades en las que se apoya")
    unknowns: list[str] = Field(description="Qué no sabemos: al menos un elemento")


class OpportunityRow(BaseModel):
    id: str
    topic: str
    lifecycle: Lifecycle
    opportunity_score: float | None
    acceleration: float
    audience_fit_score: float | None
    latam_gap: bool | None
    recommendation: Recommendation
    confidence: Confidence
    source_count: int


class OpportunityDetail(BaseModel):
    id: str
    topic: str
    description: str
    lifecycle: Lifecycle
    lifecycle_reason: str
    growth_status: GrowthStatus
    velocity: float
    acceleration: float
    opportunity_score: float | None
    audience_fit_score: float | None
    audience_mix: AudienceMix
    latam_gap: bool | None
    recommendation: Recommendation
    recommendation_reason: str | None
    why_it_matters: str
    limitations: list[str]
    confidence: Confidence


class EvidenceRow(BaseModel):
    url: HttpUrl
    title: str
    source: str
    platform: Platform
    published_at: AwareDatetime
    is_outlier: bool | None
    outlier_ratio: float | None


def _as_data(payload: BaseModel | Sequence[BaseModel]) -> str:
    if isinstance(payload, BaseModel):
        dumped = payload.model_dump(mode="json")
    else:
        dumped = [p.model_dump(mode="json") for p in payload]
    # Un título de Internet con "</datos>" no puede cerrar el bloque (CLAUDE.md §2, regla 6); el
    # escape unicode de "<" sigue siendo JSON válido.
    text = json.dumps(dumped, ensure_ascii=False).replace("<", "\\u003c")
    return f"<datos>{text}</datos>"


def _error(kind: StepKind, label: str, message: str) -> ToolOutcome:
    return ToolOutcome(kind, label, message, is_error=True)


def _unknown_id(opportunity_id: str) -> str:
    return f"No existe la oportunidad {opportunity_id} en la ejecución servida."


def _sort_key(sort: RadarSort) -> Callable[[Opportunity], tuple[bool, float]]:
    def key(o: Opportunity) -> tuple[bool, float]:
        value = o.opportunity_score if sort == "opportunity" else o.acceleration
        # Descendente y con los None al final.
        return (value is None, -(value or 0))

    return key


async def _list(args: ListInput, session: AsyncSession, seen: Seen) -> ToolOutcome:
    label = labels.list_label(args.lifecycle)
    listed = await opportunities.list_opportunities(
        session, confidence=args.confidence, topic=args.topic
    )
    if listed is None:
        return _error(StepKind.DATA, label, NO_DATA_MESSAGE)
    items = [o for o in listed.items if not args.lifecycle or o.lifecycle in args.lifecycle]
    if args.latam_gap_only:
        items = [o for o in items if o.latam_gap is True]
    items = sorted(items, key=_sort_key(args.sort))[: args.limit]
    for o in items:
        seen.add(o)
    rows = [OpportunityRow.model_validate(o, from_attributes=True) for o in items]
    return ToolOutcome(StepKind.DATA, label, _as_data(rows))


async def _get_opportunity(args: IdInput, session: AsyncSession, seen: Seen) -> ToolOutcome:
    o = await opportunities.get_opportunity(session, args.id)
    if o is None:
        return _error(StepKind.DATA, labels.OPPORTUNITY_PENDING_LABEL, _unknown_id(args.id))
    seen.add(o)
    detail = OpportunityDetail.model_validate(o, from_attributes=True)
    return ToolOutcome(StepKind.DATA, labels.opportunity_label(o.topic), _as_data(detail))


async def _get_evidence(args: EvidenceInput, session: AsyncSession, seen: Seen) -> ToolOutcome:
    o = await opportunities.get_opportunity(session, args.id)
    evidence = await opportunities.get_evidence(session, args.id)
    if o is None or evidence is None:
        return _error(StepKind.DATA, labels.EVIDENCE_PENDING_LABEL, _unknown_id(args.id))
    seen.add(o)
    # Primero los outliers: son los que explican "por qué funcionó".
    ranked = sorted(evidence, key=lambda e: e.is_outlier is not True)[: args.limit]
    seen.evidence_urls.update(str(e.url) for e in ranked)
    rows = [EvidenceRow.model_validate(e, from_attributes=True) for e in ranked]
    return ToolOutcome(StepKind.DATA, labels.evidence_label(o.topic), _as_data(rows))


async def _get_timeline(args: IdInput, session: AsyncSession, seen: Seen) -> ToolOutcome:
    o = await opportunities.get_opportunity(session, args.id)
    timeline = await opportunities.get_timeline(session, args.id)
    if o is None or timeline is None:
        return _error(StepKind.DATA, labels.TIMELINE_PENDING_LABEL, _unknown_id(args.id))
    seen.add(o)
    return ToolOutcome(StepKind.DATA, labels.timeline_label(o.topic), _as_data(timeline))


async def _set_filters(args: FiltersInput, session: AsyncSession, seen: Seen) -> ToolOutcome:
    label = labels.filters_label(
        lifecycle=args.lifecycle,
        confidence=args.confidence,
        filters_topic=bool(args.topic),
        gap=args.gap,
        sort=args.sort,
    )
    patch = RadarPatch.model_validate(args.model_dump(exclude_unset=True))
    return ToolOutcome(StepKind.VIEW, label, OK_CONTENT, patch=patch)


async def _highlight(args: HighlightInput, session: AsyncSession, seen: Seen) -> ToolOutcome:
    failed_label = labels.HIGHLIGHT_PENDING_LABEL
    listed = await opportunities.list_opportunities(session)
    if listed is None:
        return _error(StepKind.VIEW, failed_label, NO_DATA_MESSAGE)
    served = {o.id for o in listed.items}
    missing = [i for i in args.ids if i not in served]
    if missing:
        return _error(StepKind.VIEW, failed_label, _unknown_id(", ".join(missing)))
    label = labels.highlight_label(len(args.ids))
    return ToolOutcome(StepKind.VIEW, label, OK_CONTENT, patch=RadarPatch(highlight=args.ids))


async def _select(args: IdInput, session: AsyncSession, seen: Seen) -> ToolOutcome:
    o = await opportunities.get_opportunity(session, args.id)
    if o is None:
        return _error(StepKind.VIEW, labels.SELECT_PENDING_LABEL, _unknown_id(args.id))
    patch = RadarPatch(selected=o.id)
    return ToolOutcome(StepKind.VIEW, labels.select_label(o.topic), OK_CONTENT, patch=patch)


async def _reset(args: NoInput, session: AsyncSession, seen: Seen) -> ToolOutcome:
    # Los mismos valores por defecto que `parseRadarQuery` con una URL vacía; los None explícitos
    # viajan porque el parche se serializa con exclude_unset.
    patch = RadarPatch(
        lifecycle=[],
        confidence=None,
        topic=None,
        gap=False,
        sort="opportunity",
        selected=None,
        highlight=[],
    )
    return ToolOutcome(StepKind.VIEW, labels.RESET_LABEL, OK_CONTENT, patch=patch)


@dataclass(frozen=True)
class Tool[T: BaseModel]:
    kind: StepKind
    description: str
    input_model: type[T]
    pending_label: str
    run: Callable[[T, AsyncSession, Seen], Awaitable[ToolOutcome]]

    async def execute(
        self, raw_input: dict[str, object], session: AsyncSession, seen: Seen
    ) -> ToolOutcome:
        try:
            args = self.input_model.model_validate(raw_input)
        except ValidationError as e:
            fields = ", ".join(".".join(map(str, err["loc"])) for err in e.errors())
            return _error(self.kind, self.pending_label, f"Argumentos no válidos: {fields}.")
        return await self.run(args, session, seen)


TOOLS: dict[str, Tool] = {
    "list_opportunities": Tool(
        StepKind.DATA,
        "Lista las oportunidades editoriales de la ejecución servida, con sus scores. Filtra por "
        "etapa, confianza, tema o hueco en LATAM y ordena por oportunidad o aceleración.",
        ListInput,
        labels.LIST_LABEL,
        _list,
    ),
    "get_opportunity": Tool(
        StepKind.DATA,
        "Detalle de una oportunidad: etapa y su regla, crecimiento, scores, audiencia, "
        "recomendación, por qué importa y limitaciones.",
        IdInput,
        labels.OPPORTUNITY_PENDING_LABEL,
        _get_opportunity,
    ),
    "get_evidence": Tool(
        StepKind.DATA,
        "Piezas públicas que respaldan una oportunidad (URL, título, fuente), outliers primero.",
        EvidenceInput,
        labels.EVIDENCE_PENDING_LABEL,
        _get_evidence,
    ),
    "get_timeline": Tool(
        StepKind.DATA,
        "Piezas publicadas por día de una oportunidad, en la ventana actual y la anterior.",
        IdInput,
        labels.TIMELINE_PENDING_LABEL,
        _get_timeline,
    ),
    "set_filters": Tool(
        StepKind.VIEW,
        "Cambia los filtros del Radar que ve el usuario. Solo cambian los campos que envíes; "
        "null quita ese filtro. gap=true activa «Hueco en LATAM».",
        FiltersInput,
        labels.FILTERS_FALLBACK_LABEL,
        _set_filters,
    ),
    "highlight": Tool(
        StepKind.VIEW,
        "Resalta en el Radar de 1 a 5 oportunidades por id.",
        HighlightInput,
        labels.HIGHLIGHT_PENDING_LABEL,
        _highlight,
    ),
    "select_opportunity": Tool(
        StepKind.VIEW,
        "Abre el detalle de una oportunidad en el Radar.",
        IdInput,
        labels.SELECT_PENDING_LABEL,
        _select,
    ),
    "reset_view": Tool(
        StepKind.VIEW,
        "Quita filtros, resaltados y selección del Radar.",
        NoInput,
        labels.RESET_LABEL,
        _reset,
    ),
}

FINAL_ANSWER_DESCRIPTION = (
    "Respuesta final al usuario. Llámala siempre para terminar, con las oportunidades citadas "
    "y al menos un elemento en unknowns."
)

TOOL_SCHEMAS: list[ToolParam] = [
    *(
        ToolParam(
            name=name,
            description=tool.description,
            input_schema=tool.input_model.model_json_schema(),
        )
        for name, tool in TOOLS.items()
    ),
    ToolParam(
        name=FINAL_ANSWER,
        description=FINAL_ANSWER_DESCRIPTION,
        input_schema=FinalAnswerInput.model_json_schema(),
    ),
]


async def execute_tool(
    name: str, raw_input: dict[str, object], session: AsyncSession, seen: Seen
) -> ToolOutcome:
    tool = TOOLS.get(name)
    if tool is None:
        return _error(StepKind.DATA, labels.UNKNOWN_TOOL_LABEL, f"No existe la tool {name}.")
    return await tool.execute(raw_input, session, seen)
