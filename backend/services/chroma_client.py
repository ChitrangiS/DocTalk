
import logging
import os
from typing import Optional

import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────

_PERSIST_DIR: str      = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
_COLLECTION_NAME: str  = os.getenv("CHROMA_COLLECTION_NAME", "doctalk_chunks")


# ── Client and collection singleton ──────────────────────────────────

_client: Optional[chromadb.PersistentClient] = None
_collection: Optional[chromadb.Collection]   = None


def _get_collection() -> chromadb.Collection:
    """
    Return (and lazily initialize) the ChromaDB collection singleton.
    Thread-safe for reads; not intended for concurrent writes in this scope.
    """
    global _client, _collection
    if _collection is None:
        logger.info(
            "Initializing ChromaDB. Persist dir: %s  Collection: %s",
            os.path.abspath(_PERSIST_DIR),
            _COLLECTION_NAME,
        )
        _client = chromadb.PersistentClient(
            path=_PERSIST_DIR,
            settings=Settings(anonymized_telemetry=False),
        )
        _collection = _client.get_or_create_collection(
            name=_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "ChromaDB ready. Existing vectors: %d", _collection.count()
        )
    return _collection


# Eagerly initialize on import (matches embedder.py pattern).
try:
    _get_collection()
except Exception as exc:
    logger.error("Failed to initialize ChromaDB: %s", exc)
    raise


# ── Public API ───────────────────────────────────────────────────────


def upsert_chunks(chunks: list[dict]) -> int:
    """
    Persist embedded chunks to ChromaDB using upsert semantics.

    Each chunk must contain:
        chunk_id  (str)        — unique identifier, used as the vector ID
        doc_id    (str)        — parent document identifier (used for filtering)
        page      (int)        — source page number
        text      (str)        — raw chunk text
        embedding (list[float])— L2-normalized vector from embedder.py

    Returns:
        Number of vectors upserted.

    Raises:
        KeyError:   If a required field is missing from any chunk.
        ValueError: If chunks is empty.
    """
    if not chunks:
        raise ValueError("upsert_chunks received an empty list.")

    required = {"chunk_id", "doc_id", "page", "text", "embedding"}
    for i, chunk in enumerate(chunks):
        missing = required - chunk.keys()
        if missing:
            raise KeyError(
                f"Chunk at index {i} is missing required fields: {missing}"
            )

    ids: list[str]        = [c["chunk_id"]  for c in chunks]
    embeddings: list      = [c["embedding"] for c in chunks]
    documents: list[str]  = [c["text"]      for c in chunks]
    metadatas: list[dict] = [
        {"doc_id": c["doc_id"], "page": int(c["page"])}
        for c in chunks
    ]

    collection = _get_collection()
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )

    count = len(ids)
    logger.info("Upserted %d vectors. Total in collection: %d", count, collection.count())
    return count


def query_chunks(
    query_embedding: list[float],
    doc_id: str,
    *,
    top_k: int = 5,
) -> list[dict]:
    """
    Return the top_k most semantically similar chunks within a document.

    Args:
        query_embedding: Normalized vector produced by embed_text(..., is_query=True).
        doc_id:          Scope the search to this document only.
        top_k:           Maximum number of results to return.

    Returns:
        List of dicts sorted by score descending. Each dict contains:
            chunk_id (str), text (str), page (int), score (float 0–1).
        Returns empty list if no vectors exist for the given doc_id.
    """
    collection = _get_collection()

    if collection.count() == 0:
        logger.warning("query_chunks called on an empty collection.")
        return []

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
        where={"doc_id": {"$eq": doc_id}},
        include=["documents", "metadatas", "distances"],
    )

    ids       = results.get("ids",       [[]])[0]
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    return [
        {
            "chunk_id": ids[i],
            "text":     documents[i],
            "page":     metadatas[i]["page"],
            "score":    round(1.0 - distances[i], 4),
        }
        for i in range(len(ids))
    ]


def delete_doc_chunks(doc_id: str) -> None:
    """
    Delete all vectors associated with the given doc_id.
    Used when a document is re-uploaded or removed.
    """
    collection = _get_collection()
    collection.delete(where={"doc_id": {"$eq": doc_id}})
    logger.info("Deleted all vectors for doc_id: %s", doc_id)


def get_collection_stats() -> dict:
    """
    Return operational stats. Exposed via the health check endpoint in Day 3.
    """
    collection = _get_collection()
    return {
        "collection_name": _COLLECTION_NAME,
        "total_vectors":   collection.count(),
        "persist_dir":     os.path.abspath(_PERSIST_DIR),
    }