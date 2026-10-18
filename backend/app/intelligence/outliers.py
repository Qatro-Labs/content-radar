"""Outliers por pieza (estilo 1of10): rendimiento frente a la mediana de su referencia.

- YouTube: views/día desde la publicación vs. los vídeos del mismo canal.
- TikTok: views/día vs. el p90 de los vídeos de la misma búsqueda. Reddit: score vs. el mismo
  subreddit.
- Instagram: views/día vs. los reels del mismo perfil.
- HN: puntos vs. el p90 de las stories de la misma búsqueda y el mismo periodo. Con la mediana
  (~4 puntos) un 22 % de las stories salía como outlier; con el p90, un 3–6 %.
"""

from collections.abc import Sequence
from datetime import datetime, timedelta

import numpy as np

from app.schemas.signal import Platform

OUTLIER_RATIO = 3.0
NOTABLE_RATIO = 2.0
MIN_REFERENCE = 5  # con menos piezas no hay referencia
MEDIAN = 0.5
HN_REFERENCE_QUANTILE = 0.9  # HN tiene cola larga: la mediana no separa nada
# Una búsqueda de TikTok mezcla muchos autores (63 en 72 vídeos), como HN. Medido el 17/10 a las
# 22:04 UTC, n = 72 en 4 búsquedas: con la mediana un 33 % de los vídeos salía ≥3×; con el p75,
# un 17 %; con el p90, un 6 %.
TIKTOK_REFERENCE_QUANTILE = 0.9
REFERENCE_QUANTILE = {
    Platform.HACKERNEWS: HN_REFERENCE_QUANTILE,
    Platform.TIKTOK: TIKTOK_REFERENCE_QUANTILE,
}
# Las piezas recién publicadas aún no han acumulado métricas: dentro de la referencia hunden la
# mediana (o el p90) y disparan los ratios del resto. Solo salen de la referencia; sí se puntúan.
MIN_REFERENCE_AGE = {
    Platform.YOUTUBE: timedelta(days=2),
    Platform.TIKTOK: timedelta(days=2),
    Platform.INSTAGRAM: timedelta(days=2),
    # Un tweet hace casi todas sus views el primer día, y los perfiles más activos publican 20
    # tweets en 3-4 días: con 2 días, la primera recolección se quedaba sin referencia.
    Platform.X: timedelta(days=1),
    Platform.HACKERNEWS: timedelta(hours=6),
    Platform.REDDIT: timedelta(hours=6),
}


def reference_quantile(platform: Platform) -> float:
    return REFERENCE_QUANTILE.get(platform, MEDIAN)


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
