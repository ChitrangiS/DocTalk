
import logging
import os
import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from core.config import settings
from models.schemas import DeleteResponse, ErrorDetail, UploadResponse
from services.chroma_client import delete_doc_chunks, get_collection_stats, upsert_chunks
from services.chunker import process_pdf
from services.embedder import embed_chunks

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/upload",
    tags=["Upload"],
)


# ── Helpers ───────────────────────────────────────────────────────────


def _validate_upload(file: UploadFile, content: bytes) -> None:
    """
    Validate file before processing. Raises HTTPException on any violation.
    Called synchronously before any pipeline work begins (fail fast).
    """
    # Extension check
    filename = file.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF files are accepted. Received: "
                   f"'{Path(filename).suffix or 'no extension'}'.",
        )

    # Content-type check (browsers and curl send this)
    ct = file.content_type or ""
    if ct and ct not in settings.allowed_content_types:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported content-type: '{ct}'. Expected 'application/pdf'.",
        )

    # Empty file
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    # Size check
    if len(content) > settings.max_upload_size_bytes:
        size_mb = len(content) / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"File too large: {size_mb:.1f} MB. "
                f"Maximum allowed: {settings.max_upload_size_mb} MB."
            ),
        )

    # PDF magic bytes (%PDF-)
    if not content.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="File does not appear to be a valid PDF "
                   "(missing PDF magic bytes).",
        )


def _write_temp_file(content: bytes) -> str:
    """
    Write upload bytes to a named temporary file and return its path.
    Caller is responsible for deleting the file (use in try/finally).
    """
    tmp = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".pdf",
        prefix="doctalk_upload_",
    )
    tmp.write(content)
    tmp.close()
    return tmp.name


# ── Routes ────────────────────────────────────────────────────────────


@router.post(
    "/",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest a PDF",
    responses={
        201: {"description": "PDF ingested successfully."},
        400: {"model": ErrorDetail, "description": "Empty or invalid file."},
        413: {"model": ErrorDetail, "description": "File exceeds size limit."},
        415: {"model": ErrorDetail, "description": "Not a PDF file."},
        422: {"model": ErrorDetail, "description": "PDF has no extractable text."},
        500: {"model": ErrorDetail, "description": "Internal pipeline error."},
    },
)
async def upload_pdf(
    file: UploadFile = File(
        ...,
        description="PDF file to ingest. Max 20 MB. Must contain extractable text.",
    ),
) -> UploadResponse:
    """
    Ingest a PDF into the RAG pipeline.

    Pipeline: validate → save temp → chunk → embed → upsert → cleanup → respond.

    Returns a `doc_id` that the caller must pass to `POST /chat/` to ask
    questions about this document.
    """
    # Read entire file into memory once — needed for both validation and disk write.
    content = await file.read()
    _validate_upload(file, content)

    temp_path: str | None = None
    doc_id = str(uuid.uuid4()).replace("-", "")[:12]

    try:
        # ── 1. Persist to a temp file (PyMuPDF requires a file path) ────
        temp_path = _write_temp_file(content)
        logger.info(
            "Upload received: filename=%s size=%d bytes doc_id=%s",
            file.filename, len(content), doc_id,
        )

        # ── 2. Chunk ─────────────────────────────────────────────────────
        chunks = process_pdf(temp_path, doc_id)
        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "No text could be extracted from this PDF. "
                    "The file may be image-only or password-protected. "
                    "Please upload a text-based PDF."
                ),
            )

        page_count = max(c["page"] for c in chunks)
        logger.info("Chunked: doc_id=%s pages=%d chunks=%d", doc_id, page_count, len(chunks))

        # ── 3. Embed ──────────────────────────────────────────────────────
        chunks = embed_chunks(chunks)
        logger.info("Embedded: doc_id=%s vectors=%d", doc_id, len(chunks))

        # ── 4. Upsert ─────────────────────────────────────────────────────
        upsert_chunks(chunks)
        logger.info("Upserted: doc_id=%s", doc_id)

        return UploadResponse(
            doc_id=doc_id,
            filename=file.filename or "unknown.pdf",
            page_count=page_count,
            chunk_count=len(chunks),
        )

    except HTTPException:
        # Re-raise HTTP exceptions unchanged — they already have correct status codes.
        raise

    except Exception as exc:
        # Unexpected pipeline failure — log the full traceback, return 500.
        logger.exception("Pipeline error for doc_id=%s: %s", doc_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document processing failed: {exc}",
        ) from exc

    finally:
        # Always delete the temp file — even if the pipeline raised above.
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
            logger.debug("Temp file deleted: %s", temp_path)


@router.get(
    "/health",
    summary="Upload service health check",
    tags=["Health"],
)
async def upload_health() -> dict:
    """Return upload service status and current vector store statistics."""
    stats = get_collection_stats()
    return {"status": "ok", "vector_store": stats}


@router.delete(
    "/{doc_id}",
    response_model=DeleteResponse,
    summary="Delete all vectors for a document",
    responses={
        200: {"description": "Document deleted."},
        404: {"model": ErrorDetail, "description": "doc_id not found."},
    },
)
async def delete_document(doc_id: str) -> DeleteResponse:
    """
    Remove all stored vectors associated with the given doc_id.
    Use this when a document is re-uploaded or must be removed.
    Note: ChromaDB's delete-by-metadata is idempotent — deleting a
    non-existent doc_id does not raise an error.
    """
    logger.info("Delete request: doc_id=%s", doc_id)
    delete_doc_chunks(doc_id)
    return DeleteResponse(doc_id=doc_id)