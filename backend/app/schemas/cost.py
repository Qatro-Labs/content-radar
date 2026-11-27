"""Contrato del coste de operación (CLAUDE.md §4): lo consumen `GET /costs`, el panel de coste
del dashboard y la tool MCP `get_operating_cost`. El coste medido y la proyección van separados.
"""

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class Provider(StrEnum):
    """APIs externas con consumo medido. Cada valor es una clave de `variable` en pricing.yaml."""

    YOUTUBE = "youtube"
    HACKERNEWS = "hackernews"
    RSS = "rss"
    BRAVE_SEARCH = "brave_search"
    SCRAPECREATORS = "scrapecreators"
    TWITTERAPI = "twitterapi"
    TYPESAFE_JEV = "typesafe_jev"
    LLM_TEXT = "llm_text"


class CostPeriod(StrEnum):
    WEEK = "7d"
    MONTH = "30d"

    @property
    def days(self) -> int:
        return int(self.value.removesuffix("d"))


class ProviderCost(BaseModel):
    provider: Provider
    unit: str = Field(description="Unidad de consumo según pricing.yaml (quota_units, requests…)")
    units: float
    calls: int
    cost_usd: float | None = Field(
        description="Suma del coste con precio conocido. null si ningún evento tenía precio"
    )
    unknown_price_events: int = Field(description="Eventos sin precio: no suman al coste")


class MeasuredCost(BaseModel):
    window_start: datetime
    window_end: datetime
    total_usd: float | None = Field(description="null si no hay consumo registrado en el periodo")
    unknown_price_events: int
    providers: list[ProviderCost]


class MonthlyProjection(BaseModel):
    """Estimación a 30 días: consumo variable escalado desde lo medido + planes fijos."""

    fixed_usd: float
    variable_usd: float | None = Field(description="null si no hay consumo medido que escalar")
    total_usd: float | None
    based_on_days: float | None = Field(
        description="Días de consumo observado que respaldan la proyección"
    )


class OperatingCost(BaseModel):
    period: CostPeriod
    currency: str
    pricing_checked_at: date
    measured_since: datetime | None = Field(
        description="Primer consumo registrado: cuánto historial respalda las cifras"
    )
    measured: MeasuredCost
    projection: dict[str, MonthlyProjection] = Field(
        description="Por perfil de pricing.yaml (demo, production). Es una estimación"
    )
    limitations: list[str]
