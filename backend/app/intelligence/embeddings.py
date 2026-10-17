"""Embeddings multilingües: ES y EN en el mismo espacio (necesario para el LATAM Gap)."""

from collections.abc import Sequence
from functools import lru_cache

import numpy as np

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DESCRIPTION_CHARS = 300


@lru_cache
def _model():
    # Import perezoso: la API y el MCP solo leen oportunidades y no deben cargar torch.
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(MODEL_NAME)


def embedding_text(title: str, description: str | None) -> str:
    return f"{title}. {(description or '')[:DESCRIPTION_CHARS]}".strip()


def embed(texts: Sequence[str]) -> np.ndarray:
    """Vectores normalizados (norma 1): el producto escalar es la similitud coseno."""
    return _model().encode(list(texts), normalize_embeddings=True, batch_size=64)
