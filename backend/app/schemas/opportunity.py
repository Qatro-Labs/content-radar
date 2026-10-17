"""Contrato `Opportunity`: lo que consumen la API REST, el frontend y el servidor MCP.

Refleja CLAUDE.md §6. Cambiarlo rompe el trabajo de los demás: avisar en el canal antes.
Los scores los calcula Intelligence en Python; `why_it_matters` y `limitations` los redacta el LLM.
"""

from datetime import date
from enum import StrEnum
from typing import Annotated

from pydantic import AwareDatetime, BaseModel, Field, HttpUrl

from app.schemas.signal import Metrics, Platform, Segment

Score = Annotated[float, Field(ge=0, le=100)]


class Lifecycle(StrEnum):
    EMERGING = "emerging"
    ACCELERATING = "accelerating"
    PEAKING = "peaking"
    SATURATED = "saturated"
    UNKNOWN = "unknown"


class GrowthStatus(StrEnum):
    OBSERVED = "observed"  # ≥2 mediciones
    ESTIMATED = "estimated"  # 1 medición vs. referencia
    PRELIMINARY = "preliminary"  # aparece, sin aceleración demostrada


class Confidence(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Recommendation(StrEnum):
    PUBLISH_NOW = "publish_now"
    FIND_ANGLE = "find_angle"
    WAIT_FOR_CASE = "wait_for_case"
    DISCARD = "discard"


class Period(StrEnum):
    H24 = "24h"
    D7 = "7d"
    D30 = "30d"


class AudienceMix(BaseModel):
    """Proporción de la evidencia por segmento (suma 1). Campos explícitos para que el
    tipo TS generado conserve las claves.
    """

    tech: float = Field(ge=0, le=1)
    business: float = Field(ge=0, le=1)
    latam_es: float = Field(ge=0, le=1)


class Rate(BaseModel):
    """Tasa de crecimiento de una pieza entre snapshots."""

    value: float
    unit: str = Field(description="p. ej. 'views/h', 'points/h', 'comments/h'")


class Evidence(BaseModel):
    url: HttpUrl
    source: str = Field(description="Nombre público de la fuente (canal, medio, query)")
    platform: Platform
    segment: Segment
    title: str
    published_at: AwareDatetime
    observed_at: AwareDatetime
    language: str | None = None
    metrics: Metrics = Field(description="Tal cual la fuente; None = no la expone")
    velocity: Rate | None = Field(default=None, description="None sin 2+ snapshots")
    outlier_ratio: float | None = Field(
        default=None, ge=0, description="Rendimiento ajustado por edad / mediana de referencia"
    )
    is_outlier: bool | None = Field(default=None, description="outlier_ratio ≥ 3")


class Opportunity(BaseModel):
    id: str
    topic: str
    description: str
    lifecycle: Lifecycle
    lifecycle_reason: str = Field(description="Regla de §7 que se cumplió, en texto")
    growth_status: GrowthStatus
    velocity: float = Field(ge=0, description="Piezas nuevas/día en la ventana actual")
    acceleration: float = Field(description="Cambio relativo vs. ventana anterior (+0.8 = +80 %)")
    momentum_score: Score
    outlier_count: int = Field(ge=0)
    top_outlier_ratio: float | None = Field(default=None, ge=0)
    audience_mix: AudienceMix
    audience_fit_score: Score
    cross_source_score: Score
    saturation_score: Score
    actionability_score: Score
    opportunity_score: Score
    confidence: Confidence
    source_count: int = Field(ge=0, description="Fuentes independientes")
    evidence_strength: float = Field(
        ge=0, le=100, description="Normalizado por fuente; no suma views entre plataformas"
    )
    latam_gap: bool | None = Field(description="None = sin datos suficientes para decidir")
    recommendation: Recommendation
    why_it_matters: str
    limitations: list[str]
    last_updated: AwareDatetime


class OpportunityList(BaseModel):
    """Respuesta de GET /opportunities."""

    items: list[Opportunity]
    period: Period
    generated_at: AwareDatetime
    monitoring_started_at: AwareDatetime = Field(
        description="Inicio del monitoreo: los periodos anteriores no son históricos"
    )


class TimelineWindow(StrEnum):
    CURRENT = "current"
    PREVIOUS = "previous"


class TimelinePoint(BaseModel):
    date: date
    count: int = Field(ge=0, description="Piezas publicadas ese día (por published_at)")
    window: TimelineWindow


class OpportunityTimeline(BaseModel):
    """Respuesta de GET /opportunities/{id}/timeline."""

    opportunity_id: str
    window_days: int = Field(ge=1)
    points: list[TimelinePoint]
