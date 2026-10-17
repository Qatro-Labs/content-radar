"""Contrato de salida de las tools MCP (CLAUDE.md §6): lo consumen asistentes externos.

Cambiarlo rompe a los clientes: avisar en el canal. Reutiliza `Opportunity`, `Evidence`,
`OperatingCost` y `EditorialBrief` sin copiarlos.
"""

from pydantic import AwareDatetime, BaseModel, Field, HttpUrl

from app.schemas.opportunity import (
    AudienceFitCriterion,
    AudienceMix,
    Confidence,
    Evidence,
    GrowthStatus,
    Lifecycle,
    Opportunity,
    OpportunityTimeline,
    Period,
    Recommendation,
)
from app.schemas.signal import Platform, SignalHit


class EvidenceLink(BaseModel):
    url: HttpUrl
    title: str
    source: str
    platform: Platform
    published_at: AwareDatetime
    is_outlier: bool | None = Field(description="outlier_ratio ≥ 3; null = sin referencia")
    outlier_ratio: float | None = Field(description="null = sin referencia con la que comparar")


class TrendingOpportunity(BaseModel):
    """Resumen de una `Opportunity` para el listado; el detalle está en `analyze_opportunity`."""

    id: str
    topic: str
    lifecycle: Lifecycle
    lifecycle_reason: str
    growth_status: GrowthStatus
    velocity: float = Field(description="Piezas nuevas/día en la ventana actual")
    acceleration: float = Field(description="Cambio relativo vs. ventana anterior (+0.8 = +80 %)")
    momentum_score: float
    outlier_count: int
    opportunity_score: float | None = Field(description="null = sin audience fit")
    audience_fit_score: float | None = Field(description="null = sin evaluar")
    saturation_score: float
    cross_source_score: float
    confidence: Confidence
    source_count: int = Field(description="Fuentes independientes")
    latam_gap: bool | None = Field(description="null = sin datos suficientes para decidir")
    recommendation: Recommendation
    recommendation_reason: str | None
    why_it_matters: str
    top_evidence: list[EvidenceLink] = Field(description="Hasta 3, outliers primero")


class TrendingOpportunities(BaseModel):
    period: Period
    generated_at: AwareDatetime
    monitoring_started_at: AwareDatetime = Field(
        description="Inicio del monitoreo: los periodos anteriores no son históricos"
    )
    matched: int = Field(description="Oportunidades que cumplen los filtros, antes de `limit`")
    items: list[TrendingOpportunity] = Field(description="En el orden del ranking del dashboard")
    coverage: str


class OpportunityAnalysis(BaseModel):
    opportunity: Opportunity
    evidence: list[Evidence] = Field(description="Outliers primero; puede no estar completa")
    evidence_total: int = Field(description="Piezas de evidencia que tiene la oportunidad")
    timeline: OpportunityTimeline


class SignalSearch(BaseModel):
    query: str
    days: int
    items: list[SignalHit]
    coverage: str


class FitComparisonItem(BaseModel):
    id: str
    topic: str
    audience_fit_score: float | None = Field(description="null = sin evaluar")
    actionability_score: float | None = Field(description="null = sin evaluar")
    audience_fit_criteria: list[AudienceFitCriterion] | None = Field(
        description="Los 6 criterios de la rúbrica; null = sin evaluar"
    )
    audience_mix: AudienceMix
    latam_gap: bool | None
    opportunity_score: float | None
    recommendation: Recommendation
    recommendation_reason: str | None
    confidence: Confidence


class AudienceFitComparison(BaseModel):
    items: list[FitComparisonItem] = Field(description="En el orden pedido")
