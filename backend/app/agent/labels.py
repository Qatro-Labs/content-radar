"""Etiquetas de los pasos del agente (plan data-radar-agent, D8).

Las escribe Python, nunca el modelo: son texto de la UI. Los nombres de tema salen de la
oportunidad leída de la DB, no de los argumentos del modelo. Etiquetas fijas de DESIGN.md §9.
"""

from app.agent.sanitize import TITLE_MAX_CHARS, strip_invisible, truncate
from app.schemas.agent import RadarSort
from app.schemas.opportunity import Confidence, Lifecycle

LIFECYCLE_LABELS = {
    Lifecycle.EMERGING: "Emergente",
    Lifecycle.ACCELERATING: "Acelerando",
    Lifecycle.PEAKING: "En pico",
    Lifecycle.SATURATED: "Saturado",
    Lifecycle.UNKNOWN: "Sin etapa",
}
CONFIDENCE_LABELS = {
    Confidence.HIGH: "confianza alta",
    Confidence.MEDIUM: "confianza media",
    Confidence.LOW: "confianza baja",
}
SORT_LABELS: dict[RadarSort, str] = {
    "acceleration": "Ordenando por aceleración",
    "opportunity": "Ordenando por oportunidad",
}
GAP_LABEL = "Pulsando «Hueco en LATAM»"
TOPIC_FILTER_LABEL = "tema"
RESET_LABEL = "Restableciendo la vista"
# Sin un filtro que nombrar (p. ej. solo quita el hueco en LATAM).
FILTERS_FALLBACK_LABEL = "Cambiando los filtros"

LIST_LABEL = "Leyendo las oportunidades"
# Antes de leer la DB todavía no hay tema que nombrar; también es la etiqueta si el paso falla.
OPPORTUNITY_PENDING_LABEL = "Revisando una oportunidad"
EVIDENCE_PENDING_LABEL = "Revisando la evidencia"
TIMELINE_PENDING_LABEL = "Revisando la evolución"
HIGHLIGHT_PENDING_LABEL = "Resaltando oportunidades"
SELECT_PENDING_LABEL = "Abriendo una oportunidad"
UNKNOWN_TOOL_LABEL = "Intentando un paso que no existe"


def list_label(lifecycle: list[Lifecycle] | None) -> str:
    if lifecycle and len(lifecycle) == 1:
        return f"{LIST_LABEL} en «{LIFECYCLE_LABELS[lifecycle[0]]}»"
    return LIST_LABEL


def _quoted(topic: str) -> str:
    return f"«{truncate(strip_invisible(topic), TITLE_MAX_CHARS)}»"


def opportunity_label(topic: str) -> str:
    return f"Revisando {_quoted(topic)}"


def evidence_label(topic: str) -> str:
    return f"Revisando la evidencia de {_quoted(topic)}"


def timeline_label(topic: str) -> str:
    return f"Revisando la evolución de {_quoted(topic)}"


def select_label(topic: str) -> str:
    return f"Abriendo {_quoted(topic)}"


def highlight_label(count: int) -> str:
    return "Resaltando 1 oportunidad" if count == 1 else f"Resaltando {count} oportunidades"


def filters_label(
    *,
    lifecycle: list[Lifecycle] | None,
    confidence: Confidence | None,
    filters_topic: bool,
    gap: bool | None,
    sort: RadarSort | None,
) -> str:
    if gap:
        return GAP_LABEL
    filters = [LIFECYCLE_LABELS[stage] for stage in lifecycle or []]
    if confidence:
        filters.append(CONFIDENCE_LABELS[confidence])
    if filters_topic:
        filters.append(TOPIC_FILTER_LABEL)
    phrases = [f"Filtrando por {', '.join(filters)}"] if filters else []
    if sort:
        phrases.append(SORT_LABELS[sort])
    return " · ".join(phrases) or FILTERS_FALLBACK_LABEL
