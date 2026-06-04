
import logging
import logging.config
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from routers import chat, upload
# ── Logging ───────────────────────────────────────────────────────────

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
    },
    "root": {"level": "DEBUG" if settings.debug else "INFO", "handlers": ["console"]},
}

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Startup and shutdown logic in one place.
    Code before `yield` runs on startup; code after runs on shutdown.
    FastAPI's lifespan replaces the deprecated on_event decorators.
    """
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)

    # Warm up services — model loading and ChromaDB init happen at
    # module import time in embedder.py and chroma_client.py.
    # Log confirms they completed successfully before accepting requests.
    from services.chroma_client import get_collection_stats
    stats = get_collection_stats()
    logger.info(
        "ChromaDB ready. Collection: %s | Vectors: %d",
        stats["collection_name"],
        stats["total_vectors"],
    )

    yield  # ← server is live and serving requests here

    logger.info("Shutting down %s.", settings.app_name)


# ── App factory ───────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "RAG-powered PDF question-answering API. "
            "Upload a PDF, then ask natural language questions about it."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── CORS ─────────────────────────────────────────────────────────
    # Allow the Next.js dev server during development.
    # Tighten to your production domain before deploying.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ──────────────────────────────────────────────────────
    app.include_router(upload.router)
    app.include_router(chat.router)  
    # ── Global health check ──────────────────────────────────────────
    @app.get("/health", tags=["Health"], summary="Application health check")
    async def health_check() -> dict:
        from services.chroma_client import get_collection_stats
        return {
            "status": "ok",
            "version": settings.app_version,
            "vector_store": get_collection_stats(),
        }

    return app


# ── Entry point ───────────────────────────────────────────────────────

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="debug" if settings.debug else "info",
    )