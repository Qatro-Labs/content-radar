"""Lo que comparten las tools del agente (`tools.py` y `search.py`) y el bucle que las ejecuta."""

from collections.abc import Sequence
from dataclasses import dataclass, field

from pydantic import AwareDatetime, BaseModel, ConfigDict, HttpUrl

from app.agent.sanitize import wrap_data
from app.schemas.agent import CitedOpportunity, Navigation, RadarPatch, StepKind
from app.schemas.opportunity import Opportunity
from app.schemas.signal import Platform

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
    navigate: Navigation | None = None


class ToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvidenceRow(BaseModel):
    url: HttpUrl
    title: str
    source: str
    platform: Platform
    published_at: AwareDatetime
    is_outlier: bool | None
    outlier_ratio: float | None


def as_data(payload: BaseModel | Sequence[BaseModel]) -> str:
    if isinstance(payload, BaseModel):
        return wrap_data(payload.model_dump(mode="json"))
    return wrap_data([p.model_dump(mode="json") for p in payload])


def tool_error(kind: StepKind, label: str, message: str) -> ToolOutcome:
    return ToolOutcome(kind, label, message, is_error=True)
