
import logging
import os
from typing import Optional

import numpy as np
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────

# BGE asymmetric retrieval prefix.
# Applied to queries at search time only — NOT to document chunks.
# Documented in the BAAI/bge paper; improves recall ~5% on retrieval tasks.
_BGE_QUERY_PREFIX: str = (
    "Represent this sentence for searching relevant passages: "
)

# Batch size tuned for a CPU-only laptop (8 GB RAM).
# Increase to 64 if running on a machine with a GPU or 16 GB+ RAM.
_BATCH_SIZE: int = 32


# ── Model singleton ──────────────────────────────────────────────────

_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
_model: Optional[SentenceTransformer] = None


def _get_model() -> SentenceTransformer:
    """
    Lazy singleton loader.
    First call downloads the model (~130 MB) if not cached.
    Subsequent calls return the already-loaded instance.
    """
    global _model
    if _model is None:
        logger.info("Loading embedding model: %s", _MODEL_NAME)
        logger.info(
            "First run will download the model (~130 MB) to ~/.cache/huggingface/. "
            "Subsequent startups load from cache in ~1 s."
        )
        _model = SentenceTransformer(_MODEL_NAME)
        logger.info(
            "Embedding model loaded. Dimension: %d",
            _model.get_sentence_embedding_dimension(),
        )
    return _model


# Eagerly initialize on import so FastAPI startup absorbs the latency,
# not the first user request.
try:
    _get_model()
except Exception as exc:
    logger.error("Failed to load embedding model at startup: %s", exc)
    raise


# ── Public API ───────────────────────────────────────────────────────


def get_embedding_dim() -> int:
    """Return the vector dimensionality of the loaded model (384 for bge-small)."""
    return _get_model().get_sentence_embedding_dimension()


def embed_text(text: str, *, is_query: bool = False) -> list[float]:
    """
    Embed a single string into a normalized L2 vector.

    Args:
        text:     Input string. Leading/trailing whitespace is stripped.
        is_query: If True, prepends the BGE asymmetric query prefix.
                  Use True when embedding user questions at search time.
                  Use False (default) when embedding document chunks.

    Returns:
        List of floats with length == get_embedding_dim().

    Raises:
        ValueError: If text is empty after stripping.
    """
    cleaned = text.replace("\n", " ").strip()
    if not cleaned:
        raise ValueError("embed_text received empty or whitespace-only string.")

    if is_query:
        cleaned = _BGE_QUERY_PREFIX + cleaned

    model = _get_model()
    vector: np.ndarray = model.encode(
        cleaned,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return vector.tolist()


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """
    Batch-embed a list of chunk dicts produced by chunker.py.

    Adds an 'embedding' key (list[float]) to each chunk dict in-place.
    Batch encoding is significantly faster than calling embed_text() per chunk.

    Args:
        chunks: Each dict must have at minimum a 'text' key (str).

    Returns:
        The same list with 'embedding' added to every element.

    Raises:
        ValueError: If chunks is empty.
        KeyError:   If any chunk dict is missing the 'text' key.
    """
    if not chunks:
        raise ValueError("embed_chunks received an empty list.")

    texts: list[str] = [
        c["text"].replace("\n", " ").strip() for c in chunks
    ]

    logger.info("Batch embedding %d chunks (model: %s).", len(texts), _MODEL_NAME)

    model = _get_model()
    embeddings: np.ndarray = model.encode(
        texts,
        batch_size=_BATCH_SIZE,
        normalize_embeddings=True,
        show_progress_bar=len(texts) > _BATCH_SIZE,
    )

    for chunk, vector in zip(chunks, embeddings):
        chunk["embedding"] = vector.tolist()

    logger.info("Batch embedding complete. %d vectors produced.", len(chunks))
    return chunks


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """
    Utility helper used only for testing/debugging.

    Since embeddings are normalized, cosine similarity
    is equivalent to the dot product.
    """
    return float(np.dot(vec1, vec2))


