"""
FastAPI application — main entry point.
"""

import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog.contextvars

from app.api import chat, documents, evals, health, notebooks
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger

settings = get_settings()
configure_logging(settings.log_level)

logger = get_logger(__name__)

app = FastAPI(
    title="NotebookLM Lite API",
    description="Citation-first document question-answering API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─── CORS ────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request ID middleware ────────────────────────────────────────────────────

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ─── Global exception handler ────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception", error=str(exc), path=request.url.path, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# ─── Routers ─────────────────────────────────────────────────────────────────

app.include_router(health.router)
# Include with /api/v1 prefix
app.include_router(notebooks.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(evals.router, prefix="/api/v1")
# Include without prefix for direct root spec endpoints like /notebooks/{id}/ask
app.include_router(notebooks.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(evals.router)


# ─── Startup / Shutdown ───────────────────────────────────────────────────────

@app.on_event("startup")
async def on_startup():
    logger.info("NotebookLM Lite starting", env=settings.app_env)

    # Ensure MinIO bucket exists
    try:
        from app.services.storage import get_storage_service
        storage = get_storage_service()
        storage.ensure_bucket()
    except Exception as e:
        logger.warning("Could not ensure storage bucket", error=str(e))


@app.on_event("shutdown")
async def on_shutdown():
    logger.info("NotebookLM Lite shutting down")
