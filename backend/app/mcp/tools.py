"""Tools del servidor MCP: leen la ejecución servida a través de `app/services/` y nada más.

Los docstrings de los métodos son la descripción que lee el asistente. Toda salida pasa por el
saneado del agente (regla 6): el texto de las piezas y temas viene de Internet o del LLM.
"""

from typing import TYPE_CHECKING, Annotated

from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, Field

from app.agent.sanitize import clean_tree
from app.schemas.mcp import (
    EvidenceLink,
    OpportunityAnalysis,
    TrendingOpportunities,
    TrendingOpportunity,
)
from app.schemas.opportunity import (
    OPPORTUNITY_ID_PATTERN,
    Confidence,
    Evidence,
    Lifecycle,
)
from app.services import opportunities
from app.services.opportunities import MONITORING_STARTED_AT, SERVED_PERIOD, ServedOpportunity

if TYPE_CHECKING:
    # Solo para el tipo: `server.py` importa este módulo para registrar las tools.
    from app.mcp.server import McpDeps

MAX_TRENDING = 10
MAX_TOPIC_FILTER_CHARS = 60
EVIDENCE_PER_OPPORTUNITY = 3
MAX_ANALYZED_EVIDENCE = 15

COVERAGE_NOTE = (
    "Ranking sobre las fuentes que monitoreamos (YouTube, Hacker News, medios y RSS). "
    "LinkedIn, Instagram y TikTok no entran."
)
NO_DATA = "Todavía no hay oportunidades calculadas: no hay datos que mostrar."
UNKNOWN_OPPORTUNITY = (
    "No existe la oportunidad {ids} en la ejecución servida. "
    "Usa get_trending_opportunities para ver los ids válidos."
)

OpportunityId = Annotated[
    str,
    Field(
        pattern=OPPORTUNITY_ID_PATTERN,
        description="Id de la oportunidad (opp_…), tal como lo devuelve get_trending_opportunities",
    ),
]


def _sanitized[M: BaseModel](model: M) -> M:
    return type(model).model_validate(clean_tree(model.model_dump(mode="json")))


def _outliers_first(evidence: list[Evidence]) -> list[Evidence]:
    # `sorted` es estable: dentro de cada grupo se conserva el orden guardado.
    return sorted(evidence, key=lambda e: e.is_outlier is not True)


def _trending_item(served: ServedOpportunity) -> TrendingOpportunity:
    links = [
        EvidenceLink.model_validate(e, from_attributes=True)
        for e in _outliers_first(served.evidence)[:EVIDENCE_PER_OPPORTUNITY]
    ]
    # Los campos de `Opportunity` que no están en el resumen se descartan (extra="ignore").
    return TrendingOpportunity.model_validate(
        {**served.opportunity.model_dump(), "top_evidence": links}
    )


class RadarTools:
    def __init__(self, deps: "McpDeps") -> None:
        self._deps = deps

    async def _served(self, ids: list[str]) -> list[ServedOpportunity]:
        async with self._deps.session_factory() as session:
            run = await opportunities.list_served(session)
        if run is None:
            raise ToolError(NO_DATA)
        by_id = {s.opportunity.id: s for s in run.items}
        if missing := [i for i in ids if i not in by_id]:
            raise ToolError(UNKNOWN_OPPORTUNITY.format(ids=", ".join(missing)))
        return [by_id[i] for i in ids]

    async def get_trending_opportunities(
        self,
        limit: Annotated[
            int, Field(ge=1, le=MAX_TRENDING, description="Cuántas oportunidades devolver")
        ] = MAX_TRENDING,
        lifecycle: Annotated[
            Lifecycle | None, Field(description="Solo las de esta etapa del ciclo de vida")
        ] = None,
        confidence: Annotated[
            Confidence | None, Field(description="Solo las de esta confianza en la evidencia")
        ] = None,
        topic: Annotated[
            str | None,
            Field(
                max_length=MAX_TOPIC_FILTER_CHARS,
                description="Texto que debe aparecer en el nombre del tema",
            ),
        ] = None,
    ) -> TrendingOpportunities:
        """Lista las oportunidades editoriales de IA de esta semana (ventanas de 3 + 3 días), en
        el orden del ranking del dashboard. Cada una trae su etapa del ciclo de vida y la regla que
        la asignó, el tipo de crecimiento (observed/estimated/preliminary), la aceleración, scores
        0–100 (null = sin evaluar), la confianza, la recomendación y hasta 3 URLs de evidencia,
        outliers primero. Filtra por etapa, confianza o texto del tema. Si hay menos oportunidades
        que `limit`, devuelve las que hay."""
        async with self._deps.session_factory() as session:
            run = await opportunities.list_served(
                session, lifecycle=lifecycle, confidence=confidence, topic=topic
            )
        if run is None:
            raise ToolError(NO_DATA)
        return _sanitized(
            TrendingOpportunities(
                period=SERVED_PERIOD,
                generated_at=run.generated_at,
                monitoring_started_at=MONITORING_STARTED_AT,
                matched=len(run.items),
                items=[_trending_item(s) for s in run.items[:limit]],
                coverage=COVERAGE_NOTE,
            )
        )

    async def analyze_opportunity(self, opportunity_id: OpportunityId) -> OpportunityAnalysis:
        """Detalle completo de una oportunidad por id (opp_…): por qué importa, limitaciones,
        desglose del score, los 6 criterios de encaje con la audiencia de 30X con su
        justificación, mezcla de audiencias, LATAM Gap, evidencia (outliers primero, con el total)
        y timeline de piezas publicadas por día en la ventana actual y la anterior. Úsala para
        explicar si una tendencia es fiable y por qué."""
        [served] = await self._served([opportunity_id])
        return _sanitized(
            OpportunityAnalysis(
                opportunity=served.opportunity,
                evidence=_outliers_first(served.evidence)[:MAX_ANALYZED_EVIDENCE],
                evidence_total=len(served.evidence),
                timeline=served.timeline,
            )
        )
