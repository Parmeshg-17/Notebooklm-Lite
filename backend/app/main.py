import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.exceptions import AppException
from app.db.session import init_db
from app.middleware.request_id import RequestIdMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.rate_limit import RateLimiterMiddleware

# Set up logging
setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Ensure upload directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    # Initialize DB (creates tables if not using Alembic or running in SQLite dev mode)
    await init_db()
    yield
    # Shutdown logic (if any)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS Middleware
origins = list(settings.CORS_ORIGINS) if settings.CORS_ORIGINS else []
for dev_origin in [
    "http://localhost:5173", "http://localhost:5174", "http://localhost:5175",
    "http://127.0.0.1:5173", "http://127.0.0.1:5174", "http://127.0.0.1:5175",
    "http://localhost:3000", "http://127.0.0.1:3000"
]:
    if dev_origin not in origins:
        origins.append(dev_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:[0-9]+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request ID & Logging Middleware
app.add_middleware(RequestIdMiddleware)

# Security Headers & Rate Limiting Middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimiterMiddleware)

# Custom Exception Handlers
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    # In production, never leak internal tracebacks or secrets to clients
    import logging
    logger = logging.getLogger("app.main")
    logger.exception(f"Unhandled internal server error: {exc}")
    if settings.DEBUG:
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal Server Error: {str(exc)}"},
        )
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please contact support."},
    )

# Static files for uploaded PDFs/documents
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/static/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# API Routers
from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.notebooks import router as notebooks_router
from app.api.v1.documents import router as documents_router
from app.api.v1.chat import router as chat_router
from app.api.v1.users import router as users_router
from app.api.v1.search import router as search_router

# Mount v1 routes
app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(notebooks_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(search_router, prefix="/api/v1")

# Also mount on /api for seamless frontend client compatibility
app.include_router(health_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(notebooks_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(search_router, prefix="/api")

# Root health check
app.include_router(health_router)
