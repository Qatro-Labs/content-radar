"""Outliers por pieza (estilo 1of10): rendimiento frente a la mediana de su referencia.

- YouTube: views/día desde la publicación vs. los vídeos del mismo canal.
- HN: puntos vs. las stories de la misma búsqueda y el mismo periodo.
"""

from collections.abc import Sequence
from datetime import datetime, timedelta
from statistics import median

OUTLIER_RATIO = 3.0
NOTABLE_RATIO = 2.0
MIN_REFERENCE = 5  # con menos piezas la mediana no es una referencia


def age_adjusted(value: int, published_at: datetime, observed_at: datetime) -> float:
    """Métrica por día de vida. Mínimo un día, para que lo recién publicado no se dispare."""
    days = max((observed_at - published_at) / timedelta(days=1), 1.0)
    return value / days


def outlier_ratio(value: float, reference: Sequence[float]) -> float | None:
    """`value / mediana(reference)`. None sin referencia suficiente o con mediana 0."""
    if len(reference) < MIN_REFERENCE:
        return None
    m = median(reference)
    if m <= 0:
        return None
    return round(value / m, 2)


def is_outlier(ratio: float | None) -> bool | None:
    return None if ratio is None else ratio >= OUTLIER_RATIO
