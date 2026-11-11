import time
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.metrics import metrics_collector
from app.db.session import get_db
from app.rag.generation.gemini_generator import gemini_generator
from app.rag.retrieval.qdrant_store import qdrant_store

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Detailed readiness and liveness health check verifying:
    - Application status
    - SQLite/PostgreSQL connectivity
    - Qdrant Vector DB collection and connectivity
    - Google Gemini API client configuration
    """
    # 1. Database check
    db_status = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    # 2. Qdrant check
    qdrant_ok = await qdrant_store.health_check()
    qdrant_status = "ok" if qdrant_ok else "unreachable"

    # 3. Gemini / LLM client check
    has_gemini = bool(settings.effective_gemini_api_key)
    llm_status = "ok" if has_gemini else "missing_api_key"

    all_healthy = (db_status == "ok") and (qdrant_ok or settings.QDRANT_URL == ":memory:") and has_gemini

    return {
        "status": "healthy" if all_healthy else "degraded",
        "app_name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "checks": {
            "database": db_status,
            "qdrant": qdrant_status,
            "llm": llm_status,
        },
        "database": db_status,
        "timestamp": time.time(),
    }


@router.get("/metrics")
async def get_metrics(request: Request):
    """
    Exposes application performance and telemetry metrics.
    Supports both Prometheus format (Accept: text/plain) and JSON.
    """
    accept = request.headers.get("accept", "")
    if "text/plain" in accept:
        return Response(
            content=metrics_collector.to_prometheus(),
            media_type="text/plain",
        )
    return metrics_collector.get_summary()
