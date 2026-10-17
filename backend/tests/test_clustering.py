"""Clustering con embeddings sintéticos normalizados. Sin modelo."""

import numpy as np

from app.intelligence.clustering import cluster, cohesion, is_broad

DIMS = 128
CENTER_SIMILARITY = 0.52  # distancia 0.48: average linkage los une a 0.5, no a 0.4
NOISE_DIMS = range(64, DIMS)


def axis(i: int) -> np.ndarray:
    v = np.zeros(DIMS)
    v[i] = 1.0
    return v


def unit(v: np.ndarray) -> np.ndarray:
    return v / np.linalg.norm(v)


def center(i: int) -> np.ndarray:
    # c_i = sqrt(0.52)·u + sqrt(0.48)·e_i, con u = eje 0 y e_i = eje i + 1: coseno 0.52 entre pares.
    return np.sqrt(CENTER_SIMILARITY) * axis(0) + np.sqrt(1 - CENTER_SIMILARITY) * axis(i + 1)


def near_copies(c: np.ndarray, size: int, offset: int = 0) -> list[np.ndarray]:
    # Cada copia se desvía por una dimensión de ruido propia: distancia coseno ≈ 0.0099.
    return [unit(c + 0.1 * axis(NOISE_DIMS[offset + k])) for k in range(size)]


def test_large_incoherent_cluster_is_split():
    embeddings = np.array([v for i in range(6) for v in near_copies(center(i), 5, offset=5 * i)])
    assert cohesion(embeddings, list(range(30))) < 0.6
    assert [len(c) for c in cluster(embeddings)] == [5] * 6


def test_large_cohesive_cluster_is_kept():
    embeddings = np.array(near_copies(center(0), 30))
    assert [len(c) for c in cluster(embeddings)] == [30]


def test_small_incoherent_cluster_is_kept():
    embeddings = np.array([center(i) for i in range(8)])
    assert [len(c) for c in cluster(embeddings)] == [8]


def test_unsplittable_cluster_is_kept_and_broad():
    embeddings = np.array([center(i) for i in range(30)])
    clusters = cluster(embeddings)
    assert [len(c) for c in clusters] == [30]
    assert is_broad(embeddings, clusters[0])


def test_cohesion_of_identical_vectors_is_one():
    embeddings = np.array([axis(0)] * 6)
    assert cohesion(embeddings, list(range(6))) == 1.0
