"""Outliers por pieza (estilo 1of10): rendimiento frente a la mediana de su referencia.

- YouTube: views/día desde la publicación vs. los vídeos del mismo canal.
- HN: puntos vs. el p90 de las stories de la misma búsqueda y el mismo periodo. Con la mediana
  (~4 puntos) un 22 % de las stories salía como outlier; con el p90, un 3–6 %.
"""

from collections.abc import Sequence
from datetime import datetime, timedelta

import numpy as np

OUTLIER_RATIO = 3.0
NOTABLE_RATIO = 2.0
MIN_REFERENCE = 5  # con menos piezas no hay referencia
MEDIAN = 0.5
HN_REFERENCE_QUANTILE = 0.9  # HN tiene cola larga: la mediana no separa nada


def age_adjusted(value: int, published_at: datetime, observed_at: datetime) -> float:
    """Métrica por día de vida. Mínimo un día, para que lo recién publicado no se dispare."""
    days = max((observed_at - published_at) / timedelta(days=1), 1.0)
    return value / days


def outlier_ratio(
    value: float, reference: Sequence[float], quantile: float = MEDIAN
) -> float | None:
    """`value / cuantil(reference)`. None sin referencia suficiente o con referencia 0."""
    if len(reference) < MIN_REFERENCE:
        return None
    ref = float(np.quantile(reference, quantile))
    if ref <= 0:
        return None
    return round(value / ref, 2)


def is_outlier(ratio: float | None) -> bool | None:
    return None if ratio is None else ratio >= OUTLIER_RATIO
