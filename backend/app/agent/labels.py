"""Etiquetas de los pasos del agente (plan data-radar-agent, D8).

Las escribe Python, nunca el modelo: son texto de la UI. Los nombres de tema salen de la
oportunidad leída de la DB, no de los argumentos del modelo. Etiquetas fijas de DESIGN.md §9.
"""

from dataclasses import dataclass

from app.agent.sanitize import TITLE_MAX_CHARS, strip_invisible, truncate
from app.schemas.agent import DossierSection, RadarSort
from app.schemas.opportunity import Confidence, Lifecycle, Recommendation

LIFECYCLE_LABELS = {
    Lifecycle.EMERGING: "Emergente",
    Lifecycle.ACCELERATING: "Acelerando",
    Lifecycle.PEAKING: "En pico",
    Lifecycle.SATURATED: "Saturado",
    Lifecycle.UNKNOWN: "Sin tendencia clara",
}
RECOMMENDATION_LABELS = {
    Recommendation.PUBLISH_NOW: "Publicar ya",
    Recommendation.FIND_ANGLE: "Buscar ángulo",
    Recommendation.WAIT_FOR_CASE: "Esperar caso",
    Recommendation.DISCARD: "Descartar",
}
type Counter = Lifecycle | Recommendation

# Los contadores de frontend/src/components/radar/RadarHero.vue: un filtro que equivale a uno de
# ellos se nombra como el control que pulsa una persona.
COUNTER_LABELS: dict[Counter, str] = {
    Recommendation.PUBLISH_NOW: RECOMMENDATION_LABELS[Recommendation.PUBLISH_NOW],
    Lifecycle.ACCELERATING: LIFECYCLE_LABELS[Lifecycle.ACCELERATING],
    # En plural, como el contador: cuenta temas.
    Lifecycle.EMERGING: "Emergentes",
    Lifecycle.UNKNOWN: LIFECYCLE_LABELS[Lifecycle.UNKNOWN],
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
SECTION_LABELS = {
    DossierSection.SCORE: "Abriendo el expediente de",
    DossierSection.EVOLUTION: "Mostrando la evolución de",
    DossierSection.FIT: "Mostrando el encaje de",
    DossierSection.EVIDENCE: "Mostrando la evidencia de",
    DossierSection.LIMITS: "Mostrando qué no sabemos de",
}
DEFAULT_SORT: RadarSort = "opportunity"
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
SECTION_PENDING_LABEL = "Abriendo un expediente"
SEARCH_PENDING_LABEL = "Buscando piezas"
EXPLORE_LABEL = "Abriendo Explorar con la búsqueda"
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


def section_label(section: DossierSection, topic: str) -> str:
    return f"{SECTION_LABELS[section]} {_quoted(topic)}"


def search_label(count: int) -> str:
    if count == 0:
        return f"{SEARCH_PENDING_LABEL}: ninguna encontrada"
    found = "1 encontrada" if count == 1 else f"{count} encontradas"
    return f"{SEARCH_PENDING_LABEL}: {found}"


def highlight_label(count: int) -> str:
    return "Resaltando 1 oportunidad" if count == 1 else f"Resaltando {count} oportunidades"


def cited_label(count: int) -> str:
    if count == 1:
        return "Enseñando la oportunidad citada"
    return f"Enseñando las {count} oportunidades citadas"


@dataclass(frozen=True)
class FilterChange:
    lifecycle: list[Lifecycle] | None
    recommendation: Recommendation | None
    confidence: Confidence | None
    filters_topic: bool
    gap: bool | None
    sort: RadarSort | None


def _counter(
    lifecycle: list[Lifecycle] | None, recommendation: Recommendation | None
) -> Counter | None:
    if recommendation and not lifecycle:
        candidate = recommendation
    elif lifecycle and len(lifecycle) == 1 and not recommendation:
        candidate = lifecycle[0]
    else:
        return None
    return candidate if candidate in COUNTER_LABELS else None


# De aquí salen el rótulo y el parche de `set_filters`: «Pulsando «X»» solo si se pulsa X de verdad.
def pressed_counter(change: FilterChange) -> Counter | None:
    # Ordenar por oportunidad es el orden por defecto: no cambia lo que se ve.
    changes_sort = change.sort is not None and change.sort != DEFAULT_SORT
    if change.gap or change.confidence or change.filters_topic or changes_sort:
        return None
    return _counter(change.lifecycle, change.recommendation)


def filters_label(change: FilterChange) -> str:
    if change.gap:
        return GAP_LABEL
    counter = pressed_counter(change)
    if counter is not None:
        return f"Pulsando «{COUNTER_LABELS[counter]}»"
    filters = [LIFECYCLE_LABELS[stage] for stage in change.lifecycle or []]
    if change.recommendation:
        filters.append(RECOMMENDATION_LABELS[change.recommendation])
    if change.confidence:
        filters.append(CONFIDENCE_LABELS[change.confidence])
    if change.filters_topic:
        filters.append(TOPIC_FILTER_LABEL)
    phrases = [f"Filtrando por {', '.join(filters)}"] if filters else []
    if change.sort:
        phrases.append(SORT_LABELS[change.sort])
    return " · ".join(phrases) or FILTERS_FALLBACK_LABEL
