"""Validación cruzada y saturación, siempre dentro de las fuentes monitoreadas.

Una fuente independiente es un medio o canal, no una fila de `sources`: las 7 queries de HN son
una sola fuente (Hacker News), y lo mismo las búsquedas de TikTok. Así una búsqueda amplia no
infla el conteo.
"""

from collections.abc import Sequence

SEARCH_PLATFORMS = {"hackernews", "tiktok"}
POINTS_PER_EXTRA_SOURCE = 20
POINTS_PER_EXTRA_PLATFORM = 15


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


def saturation_scores(recent_counts: Sequence[int]) -> list[float]:
    """Percentil (0–100) del volumen reciente de cada tema frente al resto de temas."""
    n = len(recent_counts)
    if n == 0:
        return []
    if n == 1:
        return [50.0]
    return [
        round(100 * sum(other < c for other in recent_counts) / (n - 1), 1) for c in recent_counts
    ]
