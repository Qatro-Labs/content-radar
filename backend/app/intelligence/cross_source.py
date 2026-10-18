"""Validación cruzada y saturación, siempre dentro de las fuentes monitoreadas.

Una fuente independiente es un medio o canal, no una fila de `sources`: las 7 queries de HN son
una sola fuente (Hacker News), y lo mismo las búsquedas de TikTok. Así una búsqueda amplia no
infla el conteo.
"""

from collections.abc import Sequence

from app.schemas.signal import Platform

SEARCH_PLATFORMS = {Platform.HACKERNEWS, Platform.TIKTOK}
POINTS_PER_EXTRA_SOURCE = 20
POINTS_PER_EXTRA_PLATFORM = 15
# Saturación absoluta: cuota del tema en las notas originales del corpus de las dos ventanas
# (6 días). 100 = el 2 % de todas las notas, así que `saturated` (≥ 75) pide ≥ 1,5 %. Calibrado
# con los runs 33–37, donde la mayor cuota fue del 1,7–1,9 %. Con un percentil entre temas, un
# 25 % quedaba siempre ≥ 75, hubiera saturación o no.
SATURATION_FULL_SHARE = 0.02


def outlet_key(platform: str, source_name: str) -> str:
    """Clave de independencia: HN y TikTok (fuentes por búsqueda) cuentan como un único medio;
    el resto, por fuente."""
    return platform if platform in SEARCH_PLATFORMS else f"{platform}:{source_name}"


def cross_source_score(outlets: set[str], platforms: set[str]) -> float:
    """0 con una fuente; sube por cada fuente y plataforma adicional, hasta 100."""
    if not outlets:
        return 0.0
    score = POINTS_PER_EXTRA_SOURCE * (len(outlets) - 1) + POINTS_PER_EXTRA_PLATFORM * (
        len(platforms) - 1
    )
    return float(min(100, score))


def saturation_score(topic_stories: int, corpus_stories: int) -> float:
    """0–100 según la cuota del tema en el corpus; 0 con el corpus vacío."""
    if corpus_stories <= 0:
        return 0.0
    share = topic_stories / corpus_stories
    return round(100 * min(1.0, share / SATURATION_FULL_SHARE), 1)


def percentile_scores(counts: Sequence[int]) -> list[float]:
    """Percentil (0–100) de cada conteo frente a los demás temas."""
    n = len(counts)
    if n == 0:
        return []
    if n == 1:
        return [50.0]
    return [round(100 * sum(other < c for other in counts) / (n - 1), 1) for c in counts]
