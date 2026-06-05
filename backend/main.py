
import logging
import logging.config
import os
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

# ── Optional: Temporary ChromaDB startup disable for Railway timeout debugging ──
# If Railway times out during startup, set DISABLE_CHROMA_STARTUP_CHECK=1 in Railway env
# This will skip the get_collection_stats() call and let the server start immediately
# Once the app is running, ChromaDB will be initialized on first upload/chat request
DISABLE_CHROMA_STARTUP_CHECK = os.getenv("DISABLE_CHROMA_STARTUP_CHECK", "0") == "1"


# ── Lifespan ──────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Startup and shutdown logic in one place.
    Code before `yield` runs on startup; code after runs on shutdown.
    FastAPI's lifespan replaces the deprecated on_event decorators.
    """
    import time
    startup_start = time.time()
    
    try:
        logger.info("═" * 60)
        logger.info("Starting %s v%s", settings.app_name, settings.app_version)
        logger.info("Startup timestamp: %.3f", startup_start)
        
        # ── GROQ validation ──────────────────────────────────────────
        groq_check_start = time.time()
        logger.info("[1/3] Checking GROQ_API_KEY configuration...")
        key_exists = bool(settings.groq_api_key)
        key_length = len(settings.groq_api_key) if settings.groq_api_key else 0
        logger.info("     GROQ_API_KEY exists: %s | Length: %d chars", key_exists, key_length)
        
        if not settings.groq_api_key or not settings.groq_api_key.strip():
            logger.error(
                "     GROQ_API_KEY environment variable is not set or empty. "
                "Chat functionality will not work. "
                "Set GROQ_API_KEY in .env and restart the application."
            )
            raise ValueError(
                "GROQ_API_KEY is required but not configured. "
                "Please set the GROQ_API_KEY environment variable and restart."
            )
        groq_check_time = time.time() - groq_check_start
        logger.info("     ✓ GROQ validation complete (%.3f sec)", groq_check_time)

        # ── ChromaDB initialization ──────────────────────────────────
        chroma_init_start = time.time()
        
        if DISABLE_CHROMA_STARTUP_CHECK:
            logger.warning(
                "[2/3] ChromaDB startup check DISABLED (DISABLE_CHROMA_STARTUP_CHECK=1). "
                "Will initialize on first request."
            )
            chroma_init_time = time.time() - chroma_init_start
            logger.info("     ⚠ ChromaDB check skipped (%.3f sec)", chroma_init_time)
        else:
            logger.info("[2/3] Initializing ChromaDB...")
            try:
                from services.chroma_client import get_collection_stats
                logger.info("     [2a] Importing get_collection_stats...")
                
                logger.info("     [2b] Calling get_collection_stats()...")
                stats_start = time.time()
                stats = get_collection_stats()
                stats_time = time.time() - stats_start
                logger.info(
                    "     [2c] ✓ get_collection_stats() complete (%.3f sec): Collection=%s, Vectors=%d",
                    stats_time,
                    stats["collection_name"],
                    stats["total_vectors"],
                )
            except Exception as chroma_exc:
                logger.error("     ✗ ChromaDB initialization failed: %s", chroma_exc, exc_info=True)
                raise
            
            chroma_init_time = time.time() - chroma_init_start
            logger.info("     ✓ ChromaDB initialization complete (%.3f sec total)", chroma_init_time)

        # ── Ready to yield ──────────────────────────────────────────
        startup_time = time.time() - startup_start
        logger.info("[3/3] Application startup complete (%.3f sec total)", startup_time)
        logger.info("✓ Server is ready to accept requests")
        logger.info("═" * 60)
        
        yield  # ← server is live and serving requests here

        logger.info("Starting shutdown sequence...")
        logger.info("Shutting down %s.", settings.app_name)

    except Exception as exc:
        startup_time = time.time() - startup_start
        logger.exception(
            "✗ FATAL: Startup failed after %.3f sec. Exception: %s",
            startup_time, exc
        )
        raise


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
        allow_origins=["*"],
        allow_credentials=False,
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