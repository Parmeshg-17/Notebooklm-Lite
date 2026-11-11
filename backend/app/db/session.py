"""
Database session and connection management for NotebookLM Lite.
Supports:
- Local development via SQLite (aiosqlite)
- Enterprise production via Amazon RDS PostgreSQL (asyncpg)
- Connection pooling with health pre-pinging, recycling, and pool overflow limits
- Graceful connection disposal during application shutdown
"""

import logging
from collections.abc import AsyncGenerator
from typing import Any, Dict
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.core.config import settings

logger = logging.getLogger("app.db.session")

connect_args: Dict[str, Any] = {}
engine_kwargs: Dict[str, Any] = {
    "echo": False,
    "future": True,
}

if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
else:
    # Production PostgreSQL (RDS) connection pooling parameters
    engine_kwargs.update({
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_timeout": settings.DB_POOL_TIMEOUT,
        "pool_recycle": settings.DB_POOL_RECYCLE,
        "pool_pre_ping": True,  # Discards stale RDS connections automatically
    })

engine = create_async_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    **engine_kwargs,
)

async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)
async_session_factory = async_session_maker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI request dependency for database session."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database schema on application startup."""
    from app.db.base import Base
    import app.models  # noqa: F401

    db_type = "PostgreSQL" if "postgres" in settings.DATABASE_URL else "SQLite"
    logger.info(f"[DATABASE] Initializing {db_type} schema...")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info(f"[DATABASE] {db_type} schema verified and initialized.")


async def close_db() -> None:
    """Graceful database connection pool teardown on application shutdown."""
    logger.info("[DATABASE] Closing database connection pool...")
    await engine.dispose()
    logger.info("[DATABASE] Database connections disposed successfully.")
