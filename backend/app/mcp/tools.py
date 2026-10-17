"""Tools del servidor MCP: leen la ejecución servida a través de `app/services/` y nada más.

Los docstrings de los métodos son la descripción que lee el asistente. Toda salida pasa por el
saneado del agente (regla 6): el texto de las piezas y temas viene de Internet o del LLM.
"""

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Annotated

from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel, Field

from app.agent.sanitize import clean_tree
from app.schemas.cost import CostPeriod, OperatingCost
from app.schemas.mcp import (
    AudienceFitComparison,
    EvidenceLink,
    FitComparisonItem,
    OpportunityAnalysis,
    SignalSearch,
    TrendingOpportunities,
    TrendingOpportunity,
)
from app.schemas.opportunity import (
    OPPORTUNITY_ID_PATTERN,
    Confidence,
    Evidence,
    Lifecycle,
)
from app.schemas.signal import Platform, Segment
from app.services import costs, opportunities, signals
from app.services.opportunities import MONITORING_STARTED_AT, SERVED_PERIOD, ServedOpportunity

if TYPE_CHECKING:
    # Solo para el tipo: `server.py` importa este módulo para registrar las tools.
    from app.mcp.server import McpDeps

MAX_TRENDING = 10
MAX_TOPIC_FILTER_CHARS = 60
EVIDENCE_PER_OPPORTUNITY = 3
MAX_ANALYZED_EVIDENCE = 15
MAX_QUERY_CHARS = 80
DEFAULT_SEARCH_DAYS = 14
MAX_SEARCH_DAYS = 30
DEFAULT_SEARCH_RESULTS = 10
MAX_SEARCH_RESULTS = 20
MIN_COMPARED = 2
MAX_COMPARED = 5

COVERAGE_NOTE = (
    "Ranking sobre las fuentes que monitoreamos (YouTube, Hacker News, medios y RSS). "
    "LinkedIn, Instagram y TikTok no entran."
)
NO_DATA = "Todavía no hay oportunidades calculadas: no hay datos que mostrar."
UNKNOWN_OPPORTUNITY = (
    "No existe la oportunidad {ids} en la ejecución servida. "
    "Usa get_trending_opportunities para ver los ids válidos."
)
EMPTY_QUERY = "La búsqueda necesita al menos una palabra de 2 caracteres o más."

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

    async def search_content_signals(
        self,
        query: Annotated[
            str,
            Field(
                min_length=signals.MIN_SEARCH_TERM_CHARS,
                max_length=MAX_QUERY_CHARS,
                description="Palabras que deben aparecer todas (p. ej. 'agentes ventas')",
            ),
        ],
        platform: Annotated[
            Platform | None, Field(description="Solo piezas de esta plataforma")
        ] = None,
        segment: Annotated[
            Segment | None,
            Field(description="Solo fuentes de este segmento (latam_es = fuentes en español)"),
        ] = None,
        days: Annotated[
            int, Field(ge=1, le=MAX_SEARCH_DAYS, description="Publicadas en los últimos N días")
        ] = DEFAULT_SEARCH_DAYS,
        limit: Annotated[
            int, Field(ge=1, le=MAX_SEARCH_RESULTS, description="Cuántas piezas devolver")
        ] = DEFAULT_SEARCH_RESULTS,
    ) -> SignalSearch:
        """Busca piezas públicas ya recolectadas en las fuentes que monitoreamos (no busca en la
        web ni en LinkedIn). Todas las palabras deben aparecer en el título o la descripción, sin
        distinguir mayúsculas; prueba también la palabra en inglés y en español. Devuelve las más
        recientes primero, con URL, fuente, fechas, métricas públicas del último snapshot (null =
        no disponible) y los ids de las oportunidades del ranking que contienen cada pieza."""
        since = datetime.now(UTC) - timedelta(days=days)
        async with self._deps.session_factory() as session:
            try:
                hits = await signals.search_signals(
                    session,
                    query=query,
                    platform=platform,
                    segment=segment,
                    since=since,
                    limit=limit,
                )
            except ValueError as e:
                raise ToolError(EMPTY_QUERY) from e
        return _sanitized(SignalSearch(query=query, days=days, items=hits, coverage=COVERAGE_NOTE))

    async def compare_audience_fit(
        self,
        opportunity_ids: Annotated[
            list[OpportunityId],
            Field(
                min_length=MIN_COMPARED,
                max_length=MAX_COMPARED,
                description="Ids de las oportunidades a comparar, en el orden en que se quieren",
            ),
        ],
    ) -> AudienceFitComparison:
        """Compara el encaje con la audiencia de 30X de 2 a 5 oportunidades: score 0–100 y los 6
        criterios de la rúbrica (nivel 0–5, justificación y URLs), mezcla de audiencias, LATAM
        Gap, recomendación y confianza. Un score null significa sin evaluar. Es una evaluación
        editorial asistida por IA, no una medición."""
        # Un id repetido se compara una vez, en su primera posición.
        served = await self._served(list(dict.fromkeys(opportunity_ids)))
        return _sanitized(
            AudienceFitComparison(
                items=[
                    FitComparisonItem.model_validate(s.opportunity, from_attributes=True)
                    for s in served
                ]
            )
        )

    async def get_operating_cost(
        self,
        period: Annotated[
            CostPeriod, Field(description="Ventana del coste medido: 7d o 30d")
        ] = CostPeriod.WEEK,
    ) -> OperatingCost:
        """Coste medido de operar el radar (APIs de datos, Jev y LLM) en los últimos 7 o 30 días,
        por proveedor, y la proyección mensual por perfil de despliegue. La proyección es una
        estimación: preséntala siempre separada del coste medido."""
        async with self._deps.session_factory() as session:
            cost = await costs.operating_cost(session, period, now=datetime.now(UTC))
        return _sanitized(cost)
