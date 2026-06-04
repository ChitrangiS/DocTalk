
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────
    app_name: str = "DocTalk API"
    app_version: str = "0.3.0"
    debug: bool = False

    # ── Upload constraints ────────────────────────────────────
    max_upload_size_mb: int = 20
    allowed_content_types: list[str] = ["application/pdf"]

    # ── Embedding ─────────────────────────────────────────────
    embedding_model: str = "BAAI/bge-small-en-v1.5"

    # ── ChromaDB ──────────────────────────────────────────────
    chroma_persist_dir: str = "./chroma_db"
    chroma_collection_name: str = "doctalk_chunks"

    # ── Groq (Day 4) ──────────────────────────────────────────
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-70b-versatile"

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the cached Settings singleton.
    lru_cache ensures .env is parsed once at startup, not on every call.
    """
    return Settings()


# Module-level singleton — import this directly in routers and services.
settings = get_settings()