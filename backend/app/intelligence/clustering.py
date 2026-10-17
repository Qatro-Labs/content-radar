"""Agrupa piezas en temas por similitud coseno (aglomerativo, sin número fijo de clusters)."""

import numpy as np
from sklearn.cluster import AgglomerativeClustering

# Ajustado una vez sobre los datos reales del 17/10: con 0.6 aparecen clusters genéricos
# ("todo lo de agentes"); con 0.5 los temas son historias concretas y cruzan ES/EN.
DISTANCE_THRESHOLD = 0.5
MIN_CLUSTER_SIZE = 5


def cluster(embeddings: np.ndarray, threshold: float = DISTANCE_THRESHOLD) -> list[list[int]]:
    """Índices de cada cluster con al menos MIN_CLUSTER_SIZE piezas, de mayor a menor."""
    if len(embeddings) < MIN_CLUSTER_SIZE:
        return []
    labels = AgglomerativeClustering(
        n_clusters=None,  # pyright: ignore[reportArgumentType] (sklearn acepta None)
        metric="cosine",
        linkage="average",
        distance_threshold=threshold,
    ).fit_predict(embeddings)
    groups: dict[int, list[int]] = {}
    for i, label in enumerate(labels):
        groups.setdefault(int(label), []).append(i)
    return sorted((g for g in groups.values() if len(g) >= MIN_CLUSTER_SIZE), key=len, reverse=True)


def representative(embeddings: np.ndarray, members: list[int]) -> int:
    """La pieza más cercana al centroide del cluster."""
    vectors = embeddings[members]
    centroid = vectors.mean(axis=0)
    return members[int(np.argmax(vectors @ centroid))]
