
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

_DEFAULT_MODEL: str = "BAAI/bge-small-en-v1.5"


def _is_valid_model_id(model_id: str) -> bool:
    """
    Return True if *model_id* looks like a valid HuggingFace repo ID.

    HuggingFace repo IDs are either:
      - A bare model name:          ``model-name_v2``
      - An org-scoped name:         ``organisation/model-name_v2``

    Each segment may only contain alphanumeric characters, hyphens (-),
    underscores (_), and dots (.).  Characters such as %, [, ], @, !, ?
    and whitespace are explicitly rejected.
    """
    import re

    if not model_id or not isinstance(model_id, str):
        return False

    # Allow an optional single slash separating org from model name.
    # Each segment: one or more alphanumeric / hyphen / underscore / dot chars.
    _SEGMENT = r"[A-Za-z0-9._-]+"
    pattern = re.compile(rf"^{_SEGMENT}(/{_SEGMENT})?$")
    return bool(pattern.fullmatch(model_id.strip()))


def _resolve_model_name() -> str:
    """
    Read ``EMBEDDING_MODEL`` from the environment, validate it, and return
    the model name to use.  Falls back to *_DEFAULT_MODEL* when the value
    is absent or contains characters that would cause an HFValidationError.
    """
    raw = os.getenv("EMBEDDING_MODEL", "")
    if raw:
        logger.info("EMBEDDING_MODEL env var raw value: %r", raw)
        if _is_valid_model_id(raw):
            logger.info("Using embedding model from environment: %s", raw)
            return raw
        logger.warning(
            "EMBEDDING_MODEL value %r contains invalid characters and cannot "
            "be used as a HuggingFace repo ID. "
            "Falling back to default model: %s",
            raw,
            _DEFAULT_MODEL,
        )
    else:
        logger.info(
            "EMBEDDING_MODEL env var not set. Using default model: %s",
            _DEFAULT_MODEL,
        )
    return _DEFAULT_MODEL


_MODEL_NAME: str = _resolve_model_name()
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
    logger.error(
        "Failed to load embedding model '%s' at startup: %s. "
        "The service will start, but embedding calls will fail until the "
        "model is available.",
        _MODEL_NAME,
        exc,
    )
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


