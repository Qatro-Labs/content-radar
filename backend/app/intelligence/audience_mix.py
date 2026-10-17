"""Para quién importa: proporción de la evidencia por segmento y LATAM Opportunity Gap."""

from collections.abc import Sequence

from app.schemas.opportunity import AudienceMix
from app.schemas.signal import Segment

GAP_MIN_BUSINESS = 0.15  # hay conversación de negocio…
GAP_MAX_LATAM = 0.10  # …y casi nada de fuentes latinoamericanas
COVERED_MIN_LATAM = 0.30  # ya cubierto en la región

# Grupo B del gap (CLAUDE.md §5). España comparte el segmento `latam_es` pero no cuenta: es
# contexto, no el mercado objetivo.
LATAM_REGIONS = frozenset(
    {"latam", "ar", "bo", "br", "cl", "co", "cr", "cu", "do", "ec", "gt", "hn", "mx", "ni",
     "pa", "pe", "pr", "py", "sv", "uy", "ve"}
)  # fmt: skip


def audience_mix(pieces: Sequence[tuple[Segment, float]]) -> AudienceMix | None:
    """`pieces` = (segmento, peso). El peso es el engagement normalizado dentro de su fuente
    (1.0 si no hay métricas). None si no hay piezas.
    """
    totals = dict.fromkeys(Segment, 0.0)
    for segment, weight in pieces:
        totals[segment] += max(weight, 0.0)
    total = sum(totals.values())
    if total == 0:
        return None
    return AudienceMix(
        tech=round(totals[Segment.TECH] / total, 3),
        business=round(totals[Segment.BUSINESS] / total, 3),
        latam_es=round(totals[Segment.LATAM_ES] / total, 3),
    )


def latam_share(pieces: Sequence[tuple[str | None, float]]) -> float | None:
    """`pieces` = (región de la fuente, peso). Proporción del peso que viene de LATAM.
    None si no hay peso.
    """
    total = sum(max(weight, 0.0) for _, weight in pieces)
    if total == 0:
        return None
    latam = sum(max(weight, 0.0) for region, weight in pieces if region in LATAM_REGIONS)
    return round(latam / total, 3)


def latam_gap(mix: AudienceMix | None, latam: float | None) -> bool | None:
    """True = negocio presente y LATAM ausente. False = ya cubierto en la región.
    None = no hay señal de negocio suficiente para decidir.
    """
    if mix is None or latam is None:
        return None
    if latam >= COVERED_MIN_LATAM:
        return False
    if mix.business >= GAP_MIN_BUSINESS and latam < GAP_MAX_LATAM:
        return True
    return None
