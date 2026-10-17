"""Clustering con embeddings sintéticos normalizados. Sin modelo."""

import numpy as np

from app.intelligence.clustering import cluster, cohesion, is_broad

DIMS = 64


def unit(v: np.ndarray) -> np.ndarray:
    return v / np.linalg.norm(v)


def group(center: np.ndarray, size: int, first_dim: int) -> list[np.ndarray]:
    # Cada vector se desvía del centro por una dimensión propia: distancia coseno ≈ 0.005.
    vectors = []
    for k in range(size):
        noise = np.zeros(DIMS)
        noise[first_dim + k] = 0.1
        vectors.append(unit(center + noise))
    return vectors


def axis(i: int) -> np.ndarray:
    v = np.zeros(DIMS)
    v[i] = 1.0
    return v


def test_large_cluster_is_split():
    a = axis(0)
    b = 0.55 * axis(0) + np.sqrt(1 - 0.55**2) * axis(1)  # distancia coseno 0.45 a `a`
    embeddings = np.array(group(a, 15, 2) + group(b, 15, 17))
    assert sorted(len(c) for c in cluster(embeddings)) == [15, 15]


def test_small_cohesive_cluster_is_kept():
    embeddings = np.array(group(axis(0), 10, 2))
    assert [len(c) for c in cluster(embeddings)] == [10]


def test_cohesion_of_identical_vectors_is_one():
    embeddings = np.array([axis(0)] * 6)
    assert cohesion(embeddings, list(range(6))) == 1.0


def test_is_broad():
    orthogonal = np.eye(32)[:30]
    assert is_broad(orthogonal, list(range(30)))
    close = np.array(group(axis(0), 10, 2))
    assert not is_broad(close, list(range(10)))
