"""Para quién importa: proporción de la evidencia por segmento y LATAM Opportunity Gap."""

from collections.abc import Sequence

from app.schemas.opportunity import AudienceMix
from app.schemas.signal import Segment

GAP_MIN_BUSINESS = 0.15  # hay conversación de negocio…
GAP_MAX_LATAM = 0.10  # …y casi nada en español/LATAM
COVERED_MIN_LATAM = 0.30  # ya cubierto en la región


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


def latam_gap(mix: AudienceMix | None) -> bool | None:
    """True = negocio presente y LATAM ausente. False = ya cubierto en la región.
    None = no hay señal de negocio suficiente para decidir.
    """
    if mix is None:
        return None
    if mix.latam_es >= COVERED_MIN_LATAM:
        return False
    if mix.business >= GAP_MIN_BUSINESS and mix.latam_es < GAP_MAX_LATAM:
        return True
    return None
