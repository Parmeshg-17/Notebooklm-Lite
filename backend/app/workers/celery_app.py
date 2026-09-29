"""
Celery application configuration.
Uses Redis as broker and result backend.
"""

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "notebooklm_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,  # Important: process one task at a time per worker
    task_routes={
        "app.workers.tasks.ingest_document_task": {"queue": "ingestion"},
    },
    task_soft_time_limit=600,   # 10 minutes soft limit
    task_time_limit=660,        # 11 minutes hard limit
)
