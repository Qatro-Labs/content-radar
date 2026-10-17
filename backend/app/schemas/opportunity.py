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
# Forma de `id` (`opp_<content_item.id>`, app/intelligence/opportunities.py): la validan el agente
# y el MCP antes de buscar.
OPPORTUNITY_ID_PATTERN = r"^opp_[A-Za-z0-9_]{1,64}$"


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


class Collection(StrEnum):
    AUTOMATIC = "automatic"
    MANUAL = "manual"


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
    collection: Collection = Field(
        default=Collection.AUTOMATIC, description="Sensor automático o curación manual"
    )
    replica_of: HttpUrl | None = Field(
        default=None,
        description="URL de la pieza original si esta republica la misma nota; "
        "None = original o sin republicaciones",
    )
    replica_count: int = Field(
        default=0,
        ge=0,
        description="En la pieza original: medios distintos del suyo que republican la misma "
        "nota en este tema",
    )


class TopicEvidence(Evidence):
    """Elemento de GET /evidence: la evidencia de todas las oportunidades servidas."""

    opportunity_id: str = Field(description="Oportunidad a la que pertenece la pieza")


class ScoreComponentName(StrEnum):
    MOMENTUM = "momentum"
    AUDIENCE_FIT = "audience_fit"
    CROSS_SOURCE = "cross_source"
    FRESHNESS = "freshness"
    ACTIONABILITY = "actionability"


class ScorePenaltyName(StrEnum):
    SINGLE_SOURCE = "single_source"
    SMALL_SAMPLE = "small_sample"


class ScoreComponent(BaseModel):
    name: ScoreComponentName
    value: Score = Field(description="0–100; freshness = 100 − saturation")
    weight: float = Field(ge=0, le=1)


class ScorePenalty(BaseModel):
    name: ScorePenaltyName
    points: float = Field(ge=0)


class ScoreBreakdown(BaseModel):
    """Desglose del Opportunity Score, calculado en Python (CLAUDE.md §7)."""

    components: list[ScoreComponent] = Field(description="Siempre los 5, en orden fijo")
    penalties: list[ScorePenalty] = Field(description="Solo las aplicadas")
    total: Score = Field(description="== Opportunity.opportunity_score")


class FitCriterion(StrEnum):
    BUSINESS_IMPACT = "business_impact"  # impacto en decisiones empresariales
    ORG_APPLICATION = "org_application"  # aplicación real en organizaciones
    EXEC_READABILITY = "exec_readability"  # comprensible para directivos no técnicos
    LATAM_RELEVANCE = "latam_relevance"  # relevancia LATAM
    PILLAR_FIT = "pillar_fit"  # encaje con pilares 30X
    ACTIONABLE_CONTENT = "actionable_content"  # convertible en contenido accionable


class AudienceFitCriterion(BaseModel):
    criterion: FitCriterion
    # Antes que `level` a propósito: es el orden en que el LLM los genera, para que razone
    # antes de puntuar (CLAUDE.md §7).
    justification: str = Field(description="Por qué ese nivel, citando la evidencia")
    evidence_urls: list[HttpUrl] = Field(
        description="Evidencias del tema que cita la justificación"
    )
    level: int = Field(ge=0, le=5, description="Nivel de la rúbrica 0–5 (LLM)")


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
    # Los niveles los pone el LLM (rúbrica de §7) y Python los combina. None = todavía sin
    # evaluar; nunca un valor inventado.
    audience_fit_score: Score | None = None
    audience_fit_criteria: list[AudienceFitCriterion] | None = Field(
        default=None, description="None = sin evaluar"
    )
    cross_source_score: Score
    saturation_score: Score
    actionability_score: Score | None = None
    opportunity_score: Score | None = Field(default=None, description="None sin audience fit")
    score_breakdown: ScoreBreakdown | None = Field(
        default=None, description="None si opportunity_score es None"
    )
    confidence: Confidence
    source_count: int = Field(
        ge=0, description="Fuentes independientes, sin contar republicaciones de la misma nota"
    )
    evidence_strength: float = Field(
        ge=0, le=100, description="Normalizado por fuente; no suma views entre plataformas"
    )
    latam_gap: bool | None = Field(description="None = sin datos suficientes para decidir")
    recommendation: Recommendation
    recommendation_reason: str | None = Field(
        default=None,
        description="Regla de §7 que se cumplió, en texto; None en ejecuciones anteriores",
    )
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
