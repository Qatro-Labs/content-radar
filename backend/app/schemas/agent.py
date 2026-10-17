"""Contrato del agente del Radar: lo consumen `POST /api/v1/agent` y la barra de pregunta del
frontend. Cada modelo es el `data` de un evento SSE con el mismo nombre (`step`, `action`…).
"""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.opportunity import Confidence, Lifecycle

MAX_QUESTION_CHARS = 300

# Los mismos valores que `RANKING_SORTS` en frontend/src/lib/radarQuery.ts.
RadarSort = Literal["opportunity", "acceleration"]


class AgentQuestion(BaseModel):
    question: str = Field(min_length=1, max_length=MAX_QUESTION_CHARS)


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
    confidence: Confidence | None = None
    topic: str | None = None
    gap: bool | None = None
    sort: RadarSort | None = None
    selected: str | None = None
    highlight: list[str] | None = None


class ActionEvent(BaseModel):
    """Se serializa con `exclude_unset=True` para que solo viajen los campos del parche."""

    step_id: int
    patch: RadarPatch


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
