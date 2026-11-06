"""
ResearchMind AI – Embedding Service
======================================
Provides text embeddings using HuggingFace sentence-transformers.

The model is loaded lazily on first use to avoid startup delay
when embeddings are not needed.
"""

from __future__ import annotations

import numpy as np

from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

_model = None  # Lazy singleton


def _get_model():
    """Lazy-load the embedding model on first use."""
    global _model
    if _model is not None:
        return _model

    try:
        from sentence_transformers import SentenceTransformer  # type: ignore[import]
    except ImportError:
        raise ImportError(
            "sentence-transformers not installed. Run: pip install sentence-transformers"
        )

    model_name = settings.hf_embedding_model
    logger.info("loading_embedding_model", model=model_name)

    kwargs = {}
    if settings.hf_token:
        kwargs["token"] = settings.hf_token

    _model = SentenceTransformer(model_name, **kwargs)
    logger.info("embedding_model_loaded", model=model_name)
    return _model


def embed_texts(texts: list[str]) -> np.ndarray:
    """
    Encode a list of texts into embedding vectors.

    Args:
        texts: List of text strings to embed.

    Returns:
        2D numpy array of shape (len(texts), embedding_dim).
    """
    if not texts:
        return np.array([])

    model = _get_model()
    embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return embeddings  # type: ignore[return-value]


def embed_query(query: str) -> np.ndarray:
    """
    Encode a single query string.

    Args:
        query: The query text.

    Returns:
        1D numpy array (embedding vector).
    """
    result = embed_texts([query])
    if len(result) == 0:
        raise ValueError("Empty embedding result for query.")
    return result[0]


def get_embedding_dimension() -> int:
    """Return the dimensionality of the embedding model's output vectors."""
    model = _get_model()
    return model.get_sentence_embedding_dimension()
