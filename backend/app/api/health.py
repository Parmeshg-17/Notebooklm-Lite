"""
Health and readiness endpoints.
"""

from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.schemas.schemas import HealthResponse, ReadyResponse

router = APIRouter(tags=["Health"])
settings = get_settings()


@router.get("/health", response_model=HealthResponse, summary="Liveness check")
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/ready", response_model=ReadyResponse, summary="Readiness check")
async def ready() -> ReadyResponse:
    checks: dict[str, bool] = {}

    # Check database
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        checks["database"] = False

    # Check Redis
    try:
        import redis as redis_lib
        r = redis_lib.from_url(settings.redis_url, socket_connect_timeout=2)
        r.ping()
        checks["redis"] = True
    except Exception:
        checks["redis"] = False

    # Check Storage (S3 / Local fallback)
    try:
        from app.services.storage import get_storage_service
        storage = get_storage_service()
        checks["storage"] = storage.health_check()
    except Exception:
        checks["storage"] = False

    all_ok = all(checks.values())
    return ReadyResponse(
        status="ready" if all_ok else "degraded",
        checks=checks,
    )
