from pydantic import BaseModel, Field, field_validator


# ════════════════════════════════════════════════════════════
# SHARED / UTILITY
# ════════════════════════════════════════════════════════════


class HealthResponse(BaseModel):
    status: str = Field(..., examples=["ok"])
    version: str
    vector_store: dict


class ErrorDetail(BaseModel):
    """Structured error body returned on 4xx / 5xx responses."""
    error: str
    detail: str | None = None
    doc_id: str | None = None  # included when the error is doc-scoped


# ════════════════════════════════════════════════════════════
# UPLOAD  (Day 3)
# ════════════════════════════════════════════════════════════


class UploadResponse(BaseModel):
    """
    Returned by POST /upload/ on success.
    The doc_id is the caller's handle for all subsequent /chat/ requests.
    """
    doc_id: str = Field(
        ...,
        description="Unique document identifier. Pass this to POST /chat/.",
        examples=["3f7a1b2c4d5e"],
    )
    filename: str = Field(..., examples=["research_paper.pdf"])
    page_count: int = Field(..., ge=1)
    chunk_count: int = Field(..., ge=1)
    message: str = Field(default="Document ingested successfully.")

    model_config = {"json_schema_extra": {
        "example": {
            "doc_id": "3f7a1b2c4d5e",
            "filename": "research_paper.pdf",
            "page_count": 12,
            "chunk_count": 47,
            "message": "Document ingested successfully.",
        }
    }}


class DeleteResponse(BaseModel):
    doc_id: str
    message: str = Field(default="Document deleted successfully.")


# ════════════════════════════════════════════════════════════
# CHAT  (Day 4 / Day 5 — forward declared)
# ════════════════════════════════════════════════════════════


class ChatRequest(BaseModel):
    """POST /chat/ request body."""
    doc_id: str = Field(
        ...,
        description="doc_id returned by POST /upload/.",
        examples=["3f7a1b2c4d5e"],
    )
    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Natural language question about the uploaded document.",
        examples=["What is the main contribution of this paper?"],
    )

    @field_validator("question")
    @classmethod
    def question_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("question must not be blank.")
        return v.strip()


class SourceChunk(BaseModel):
    """A single retrieved chunk included in the chat response."""
    page: int = Field(..., ge=1)
    excerpt: str = Field(..., description="First 200 characters of the chunk text.")
    score: float = Field(..., ge=0.0, le=1.0)


class ChatResponse(BaseModel):
    """POST /chat/ response (non-streaming fallback — streaming via SSE in Day 5)."""
    answer: str
    sources: list[SourceChunk]
    doc_id: str
    model: str