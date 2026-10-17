"""Agrupa piezas en temas por similitud coseno (aglomerativo, sin número fijo de clusters)."""

import numpy as np
from sklearn.cluster import AgglomerativeClustering

# Ajustado una vez sobre los datos reales del 17/10: con 0.6 aparecen clusters genéricos
# ("todo lo de agentes"); con 0.5 los temas son historias concretas y cruzan ES/EN.
DISTANCE_THRESHOLD = 0.5
MIN_CLUSTER_SIZE = 5
# Con average linkage a 0.5 aparecen clusters que solo comparten el término de la búsqueda
# ("AI agents" en HN: 36 piezas, similitud media 0.555 el 17/10). Se vuelven a partir una vez.
SPLIT_MIN_SIZE = 25
SPLIT_MIN_COHESION = 0.6
SPLIT_THRESHOLD = 0.4


def _agglomerate(embeddings: np.ndarray, threshold: float) -> list[list[int]]:
    labels = AgglomerativeClustering(
        n_clusters=None,  # pyright: ignore[reportArgumentType] (sklearn acepta None)
        metric="cosine",
        linkage="average",
        distance_threshold=threshold,
    ).fit_predict(embeddings)
    groups: dict[int, list[int]] = {}
    for i, label in enumerate(labels):
        groups.setdefault(int(label), []).append(i)
    return [g for g in groups.values() if len(g) >= MIN_CLUSTER_SIZE]


def cohesion(embeddings: np.ndarray, members: list[int]) -> float:
    """Similitud coseno media entre pares distintos (los embeddings vienen normalizados)."""
    n = len(members)
    if n < 2:
        return 1.0
    vectors = embeddings[members]
    similarities = vectors @ vectors.T
    return float((similarities.sum() - np.trace(similarities)) / (n * (n - 1)))


def is_broad(embeddings: np.ndarray, members: list[int]) -> bool:
    """Grande y poco cohesionado: se intenta partir, y si sigue así es categoría, no historia."""
    return len(members) > SPLIT_MIN_SIZE and cohesion(embeddings, members) < SPLIT_MIN_COHESION


def _split(embeddings: np.ndarray, members: list[int]) -> list[list[int]]:
    subgroups = _agglomerate(embeddings[members], SPLIT_THRESHOLD)
    # Sin ningún subcluster ≥ MIN_CLUSTER_SIZE se conserva el original (D13): el tema no se
    # pierde y `is_broad` lo marca como amplio.
    return [[members[i] for i in sub] for sub in subgroups] or [members]


def cluster(embeddings: np.ndarray, threshold: float = DISTANCE_THRESHOLD) -> list[list[int]]:
    """Índices de cada cluster con al menos MIN_CLUSTER_SIZE piezas, de mayor a menor."""
    if len(embeddings) < MIN_CLUSTER_SIZE:
        return []
    result: list[list[int]] = []
    for members in _agglomerate(embeddings, threshold):
        if is_broad(embeddings, members):
            result.extend(_split(embeddings, members))
        else:
            result.append(members)
    return sorted(result, key=len, reverse=True)


def representative(embeddings: np.ndarray, members: list[int]) -> int:
    """La pieza más cercana al centroide del cluster."""
    vectors = embeddings[members]
    centroid = vectors.mean(axis=0)
    return members[int(np.argmax(vectors @ centroid))]
