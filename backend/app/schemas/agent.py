"""Contrato de Rad, el agente del Radar: lo consumen `POST /api/v1/agent` y la barra de pregunta
del frontend. La pregunta puede traer el contexto de la conversación; cada evento SSE lleva como
`data` el modelo de su nombre (`step`, `action`…).
"""

from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import BaseModel, Field, model_validator

from app.schemas.opportunity import OPPORTUNITY_ID_PATTERN, Confidence, Lifecycle, Recommendation

MAX_QUESTION_CHARS = 300
# Contexto de la conversación (plan fe-radar-agent, D2): lo justo para "¿y ese?" sin reenviar
# las respuestas del modelo.
MAX_HISTORY = 4
MAX_FOCUS_IDS = 6
MAX_SEARCH_CHARS = 60

OpportunityId = Annotated[str, Field(pattern=OPPORTUNITY_ID_PATTERN)]
QuestionText = Annotated[str, Field(min_length=1, max_length=MAX_QUESTION_CHARS)]

# Los mismos valores que `RANKING_SORTS` en frontend/src/lib/radarQuery.ts.
RadarSort = Literal["opportunity", "acceleration"]


class StepKind(StrEnum):
    DATA = "data"
    VIEW = "view"


class StepStatus(StrEnum):
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class StepEvent(BaseModel):
    id: int = Field(ge=1, description="Orden del paso en esta pregunta, desde 1")
    kind: StepKind = Field(description="data → etiqueta Datos · view → etiqueta Vista")
    label: str = Field(description="Qué hace el paso, escrito por Python, nunca por el modelo")
    status: StepStatus


class RadarPatch(BaseModel):
    """Parche del estado de la URL del Radar (`useRadarQuery`): solo cambian los campos presentes.

    Un campo presente con `null` significa "quitar ese filtro".
    """

    lifecycle: list[Lifecycle] | None = None
    recommendation: Recommendation | None = None
    confidence: Confidence | None = None
    topic: str | None = None
    gap: bool | None = None
    sort: RadarSort | None = None
    selected: str | None = None
    highlight: list[str] | None = None


class AgentScreen(StrEnum):
    RADAR = "radar"
    DOSSIER = "dossier"
    EXPLORE = "explore"


class DossierSection(StrEnum):
    SCORE = "score"
    EVOLUTION = "evolution"
    FIT = "fit"
    EVIDENCE = "evidence"
    LIMITS = "limits"


class AgentViewContext(BaseModel):
    screen: AgentScreen
    opportunity_id: OpportunityId | None = Field(
        default=None, description="Tema seleccionado en el Radar o abierto en el expediente"
    )
    search: str | None = Field(
        default=None, max_length=MAX_SEARCH_CHARS, description="Búsqueda de Explorar (?q=)"
    )
    filters: RadarPatch | None = Field(
        default=None, description="Filtros del Radar que tiene puestos la persona"
    )


class AgentQuestion(BaseModel):
    question: QuestionText
    history: list[QuestionText] = Field(
        default_factory=list,
        max_length=MAX_HISTORY,
        description=(
            "Preguntas anteriores, de la más antigua a la más reciente. Nunca respuestas del modelo"
        ),
    )
    focus_ids: list[OpportunityId] = Field(
        default_factory=list,
        max_length=MAX_FOCUS_IDS,
        description="Oportunidades citadas en la respuesta anterior",
    )
    view: AgentViewContext | None = None


class Navigation(BaseModel):
    screen: AgentScreen
    opportunity_id: str | None = Field(default=None, description="Expediente que se abre")
    section: DossierSection | None = Field(default=None, description="Sección del expediente")
    search: str | None = Field(default=None, description="Búsqueda con la que se abre Explorar")


class ActionEvent(BaseModel):
    """Trae `patch` (estado del Radar) o `navigate`, nunca los dos. Se serializa con
    `exclude_unset=True` para que solo viajen los campos puestos.
    """

    step_id: int
    patch: RadarPatch | None = None
    navigate: Navigation | None = None

    @model_validator(mode="after")
    def _one_change(self) -> Self:
        if (self.patch is None) == (self.navigate is None):
            raise ValueError("Una acción trae `patch` o `navigate`, y solo uno")
        return self


class CitedOpportunity(BaseModel):
    id: str
    topic: str
    lifecycle: Lifecycle
    opportunity_score: float | None = Field(description="None sin audience fit")


class AnswerEvent(BaseModel):
    text: str
    cited: list[CitedOpportunity] = Field(
        description="Solo oportunidades que devolvió alguna tool de datos en esta pregunta"
    )
    unknowns: list[str] = Field(min_length=1, description="Qué no sabemos")


class ErrorCode(StrEnum):
    LLM_UNAVAILABLE = "llm_unavailable"
    NO_DATA = "no_data"
    INTERNAL = "internal"
    TIMEOUT = "timeout"


class ErrorEvent(BaseModel):
    code: ErrorCode
    message: str = Field(description="En español, sin detalles internos")


class DoneEvent(BaseModel):
    steps: int
    data_steps: int
    view_steps: int


type AgentEvent = StepEvent | ActionEvent | AnswerEvent | ErrorEvent | DoneEvent
