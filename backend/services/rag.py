
import json
import logging
import os
from dataclasses import dataclass, field
from typing import AsyncGenerator

from dotenv import load_dotenv
from groq import AsyncGroq, Groq

from core.config import settings
from models.schemas import SourceChunk
from services.chroma_client import query_chunks
from services.embedder import embed_text

load_dotenv()
logger = logging.getLogger(__name__)


# ── Constants ────────────────────────────────────────────────────────

TOP_K: int = 5
# Maximum characters of context to include in the prompt.
# ~3500 chars ≈ 875 tokens — safely inside Llama 3.1's 128K window
# while keeping the prompt focused. Increasing this adds noise; decreasing
# it risks losing relevant context. Tune per domain if needed.
MAX_CONTEXT_CHARS: int = 3500

# Returned verbatim by the LLM when the answer is not in the document.
# Using a fixed phrase allows the frontend to detect and style it differently.
# The system prompt explicitly instructs the model to use this exact string.
NOT_FOUND_PHRASE: str = (
    "I couldn't find information about that in this document."
)


# ── Result dataclass ─────────────────────────────────────────────────

@dataclass
class RagResult:
    """
    Structured output from get_answer().
    All fields are typed so callers don't parse raw dicts.
    """
    answer: str
    sources: list[SourceChunk]
    doc_id: str
    model: str
    chunks_retrieved: int
    context_chars: int
    is_not_found: bool = field(init=False)

    def __post_init__(self) -> None:
        self.is_not_found = self.answer.strip() == NOT_FOUND_PHRASE


# ── Groq clients ─────────────────────────────────────────────────────

# sync_client: used by get_answer() in test scripts.
# async_client: used by stream_answer() in the HTTP streaming endpoint.
# Both share the same key and model — two client objects, one API.
_sync_client  = Groq(api_key=settings.groq_api_key)
_async_client = AsyncGroq(api_key=settings.groq_api_key)


# ── Context assembly ─────────────────────────────────────────────────

def _build_context(chunks: list[dict]) -> tuple[str, list[SourceChunk]]:
    """
    Convert retrieved chunks into a context string and a source list.

    Each chunk is formatted as:
        [Page N]: {text}

    The [Page N] label is critical — the system prompt instructs the LLM
    to cite these labels. Without them, the LLM invents page numbers.

    Truncates at MAX_CONTEXT_CHARS to stay within token budget.
    Chunks are already sorted by relevance score (highest first) by
    chroma_client.query_chunks(), so truncation drops the least relevant.

    Returns:
        context: formatted string injected into the system prompt.
        sources: list of SourceChunk for the API response.
    """
    parts: list[str]          = []
    sources: list[SourceChunk] = []
    total_chars: int           = 0

    for chunk in chunks:
        entry = f"[Page {chunk['page']}]: {chunk['text']}"

        if total_chars + len(entry) > MAX_CONTEXT_CHARS:
            logger.debug(
                "Context budget reached at chunk %d. Truncating.", len(parts)
            )
            break

        parts.append(entry)
        sources.append(
            SourceChunk(
                page=chunk["page"],
                excerpt=chunk["text"][:200].strip(),
                score=round(chunk.get("score", 0.0), 4),
            )
        )
        total_chars += len(entry)

    context = "\n\n".join(parts)
    return context, sources


# ── Prompt engineering ───────────────────────────────────────────────

def _build_system_prompt(context: str) -> str:
    """
    System prompt designed for three goals:
        1. Groundedness — answer only from the provided context.
        2. Citability  — always reference [Page N] labels.
        3. Honesty     — use the exact NOT_FOUND_PHRASE when the answer
                         is not present, so the frontend can detect it.

    Each rule in the prompt exists for a documented reason (see comments).
    This is the kind of detail that distinguishes engineers who understand
    LLM behaviour from those who just call the API.
    """
    return f"""You are a precise document assistant. Your only knowledge source is the context extracted from the user's uploaded PDF, provided below.

STRICT RULES — follow all of them exactly:

1. GROUNDEDNESS: Answer solely from the provided CONTEXT. Do not use any knowledge from your training data. If the context does not contain enough information to answer, say exactly: "{NOT_FOUND_PHRASE}"

2. CITATIONS: Every factual claim must be followed by a page citation in parentheses, e.g. (Page 3) or (Pages 2, 5). Only cite page numbers that appear in the CONTEXT below.

3. NEVER FABRICATE: If a detail is absent from the CONTEXT, do not infer, estimate, or fill in from general knowledge. Use the not-found phrase instead.

4. FORMAT: Be concise and direct. Use bullet points when listing multiple items. Avoid padding or filler sentences.

5. PAGE ACCURACY: Never cite a page number that does not appear in the CONTEXT labels below. The labels are authoritative.

CONTEXT FROM DOCUMENT:
{context}"""


# ── Synchronous answer (tests + non-streaming fallback) ───────────────

def get_answer(doc_id: str, question: str) -> RagResult:
    """
    Full synchronous RAG pipeline. Blocks until the LLM responds.

    Use this in:
        - Test scripts (test_day4.py)
        - Non-streaming API clients that don't support SSE

    The HTTP streaming endpoint (Day 5) uses stream_answer() instead.

    Args:
        doc_id:   Document identifier from POST /upload/ response.
        question: Natural language question about the document.

    Returns:
        RagResult with answer, sources, and pipeline metadata.

    Raises:
        ValueError: If doc_id or question is empty.
        groq.APIError: If the Groq API call fails (logged + re-raised).
    """
    if not doc_id or not doc_id.strip():
        raise ValueError("doc_id must not be empty.")
    if not question or not question.strip():
        raise ValueError("question must not be empty.")

    question = question.strip()
    logger.info("RAG query: doc_id=%s question='%s'", doc_id, question[:80])

    # ── Step 1: embed question ───────────────────────────────────────
    query_vector = embed_text(question, is_query=True)

    # ── Step 2: retrieve relevant chunks ────────────────────────────
    chunks = query_chunks(query_vector, doc_id, top_k=TOP_K)
    logger.info("Retrieved %d chunks for doc_id=%s", len(chunks), doc_id)

    if not chunks:
        logger.warning("No chunks found for doc_id=%s. Returning not-found.", doc_id)
        return RagResult(
            answer=NOT_FOUND_PHRASE,
            sources=[],
            doc_id=doc_id,
            model=settings.groq_model,
            chunks_retrieved=0,
            context_chars=0,
        )

    # ── Step 3: assemble context + sources ──────────────────────────
    context, sources = _build_context(chunks)
    logger.debug("Context assembled: %d chars, %d sources", len(context), len(sources))

    # ── Step 4: build messages ───────────────────────────────────────
    messages = [
        {"role": "system", "content": _build_system_prompt(context)},
        {"role": "user",   "content": question},
    ]

    # ── Step 5: call Groq ────────────────────────────────────────────
    try:
        response = _sync_client.chat.completions.create(
            model=settings.groq_model,
            messages=messages,
            temperature=0.1,    # low temperature = more factual, less creative
            max_tokens=700,
            stream=False,
        )
    except Exception as exc:
        logger.exception("Groq API error for doc_id=%s: %s", doc_id, exc)
        raise

    answer = response.choices[0].message.content.strip()
    logger.info(
        "Answer generated: doc_id=%s tokens=%d",
        doc_id,
        response.usage.completion_tokens if response.usage else 0,
    )

    return RagResult(
        answer=answer,
        sources=sources,
        doc_id=doc_id,
        model=settings.groq_model,
        chunks_retrieved=len(chunks),
        context_chars=len(context),
    )


# ── Async streaming generator (Day 5 SSE endpoint) ───────────────────

async def stream_answer(
    doc_id: str,
    question: str,
) -> AsyncGenerator[str, None]:
    """
    Async generator that yields Server-Sent Event (SSE) formatted strings.

    SSE wire format (each yield):
        "data: {token}\\n\\n"        — individual LLM token
        "data: [SOURCES]{json}\\n\\n" — structured sources after stream ends
        "data: [DONE]\\n\\n"          — stream terminator

    Day 5's StreamingResponse wraps this generator directly:
        return StreamingResponse(stream_answer(doc_id, q), media_type="text/event-stream")

    The frontend:
        1. Reads tokens and appends them to the chat bubble.
        2. Detects [SOURCES] and parses the JSON to render citation cards.
        3. Detects [DONE] and marks the response as complete.

    Args:
        doc_id:   Document identifier.
        question: Natural language question.

    Yields:
        SSE-formatted strings.
    """
    question = (question or "").strip()
    if not doc_id or not question:
        yield f"data: {NOT_FOUND_PHRASE}\n\n"
        yield "data: [DONE]\n\n"
        return

    logger.info("Stream RAG: doc_id=%s question='%s'", doc_id, question[:80])

    # Steps 1–3 identical to get_answer() ────────────────────────────
    query_vector = embed_text(question, is_query=True)
    chunks       = query_chunks(query_vector, doc_id, top_k=TOP_K)

    if not chunks:
        logger.warning("No chunks for stream: doc_id=%s", doc_id)
        yield f"data: {NOT_FOUND_PHRASE}\n\n"
        yield "data: [DONE]\n\n"
        return

    context, sources = _build_context(chunks)
    messages = [
        {"role": "system", "content": _build_system_prompt(context)},
        {"role": "user",   "content": question},
    ]

    # Stream from Groq ────────────────────────────────────────────────
    try:
        stream = await _async_client.chat.completions.create(
            model=settings.groq_model,
            messages=messages,
            temperature=0.1,
            max_tokens=700,
            stream=True,
        )

        async for chunk in stream:
            token = chunk.choices[0].delta.content
            if token:
                # Escape newlines inside token so SSE line format stays valid.
                # SSE treats bare \n as a field separator — must be escaped.
                safe_token = token.replace("\n", "\\n")
                yield f"data: {safe_token}\n\n"

    except Exception as exc:
        logger.exception("Groq stream error for doc_id=%s: %s", doc_id, exc)
        yield f"data: Error generating response: {exc}\n\n"
        yield "data: [DONE]\n\n"
        return

    # Emit sources as structured JSON after the answer stream ends.
    # The frontend parses this to render page-citation cards.
    sources_payload = json.dumps(
        [s.model_dump() for s in sources],
        ensure_ascii=False,
    )
    yield f"data: [SOURCES]{sources_payload}\n\n"
    yield "data: [DONE]\n\n"
    logger.info("Stream complete: doc_id=%s sources=%d", doc_id, len(sources))