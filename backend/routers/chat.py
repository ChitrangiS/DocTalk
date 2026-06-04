
import logging

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from core.config import settings
from models.schemas import ChatRequest, ErrorDetail
from services.chroma_client import get_collection_stats
from services.rag import stream_answer

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)

# ── SSE response headers ─────────────────────────────────────────────
#
# Cache-Control: no-cache
#     Prevents CDN / browser caching. Every request must reach the origin.
#     Cached SSE streams would replay stale answers.
#
# X-Accel-Buffering: no
#     Disables response buffering in Nginx and most reverse proxies.
#     Without this, the proxy holds the response until it's complete,
#     destroying the streaming effect for the client.
#
# Connection: keep-alive
#     Instructs the TCP connection to stay open for the duration of the stream.
#     Redundant on HTTP/2 (multiplexed by default) but required for HTTP/1.1.
#
# Content-Type is set via media_type="text/event-stream" on StreamingResponse.
# ─────────────────────────────────────────────────────────────────────

_SSE_HEADERS: dict[str, str] = {
    "Cache-Control":     "no-cache",
    "X-Accel-Buffering": "no",
    "Connection":        "keep-alive",
}


# ── Routes ────────────────────────────────────────────────────────────


@router.post(
    "/",
    summary="Stream an answer to a question about an uploaded PDF",
    response_description=(
        "Server-Sent Event stream. "
        "Tokens arrive as 'data: {token}\\n\\n'. "
        "Ends with 'data: [SOURCES]{json}\\n\\n' then 'data: [DONE]\\n\\n'."
    ),
    responses={
        200: {"description": "SSE stream started successfully."},
        400: {"model": ErrorDetail, "description": "doc_id or question is blank."},
        503: {"model": ErrorDetail, "description": "Vector store is empty — no PDFs uploaded."},
    },
)
async def chat(
    request: ChatRequest,
    _req: Request = None,
) -> StreamingResponse:
    """
    Accept a question about a previously uploaded PDF and stream the answer.

    The caller must supply the `doc_id` returned by `POST /upload/`.
    The response is a Server-Sent Event stream — not JSON.

    Connect from JavaScript:
        const res = await fetch('/chat/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ doc_id: '...', question: '...' }),
        });
        const reader = res.body.getReader();
        // read tokens and [SOURCES] / [DONE] events

    Connect with curl (dev testing):
        curl -N -X POST http://localhost:8000/chat/ \\
             -H "Content-Type: application/json" \\
             -d '{"doc_id":"YOUR_ID","question":"What is this about?"}'
    """
    # Guard: reject if the vector store is empty.
    # This gives a meaningful 503 instead of a stream that immediately
    # returns NOT_FOUND for every question.
    stats = get_collection_stats()
    if stats["total_vectors"] == 0:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "No documents have been ingested yet. "
                "Upload a PDF via POST /upload/ before asking questions."
            ),
        )

    logger.info(
        "Chat request: doc_id=%s question='%s'",
        request.doc_id,
        request.question[:80],
    )

    return StreamingResponse(
        stream_answer(request.doc_id, request.question),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


@router.get(
    "/health",
    summary="Chat service health check",
    tags=["Health"],
)
async def chat_health() -> dict:
    """
    Return chat service operational status.
    Includes vector store stats and the configured LLM model name.
    Used by monitoring, the frontend on startup, and the /docs UI.
    """
    stats = get_collection_stats()
    return {
        "status":        "ready" if stats["total_vectors"] > 0 else "idle",
        "model":         settings.groq_model,
        "vector_store":  stats,
        "note": (
            "Upload a PDF via POST /upload/ to start chatting."
            if stats["total_vectors"] == 0
            else f"{stats['total_vectors']} vectors indexed and ready."
        ),
    }