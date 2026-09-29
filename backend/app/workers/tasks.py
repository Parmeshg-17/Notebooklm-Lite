"""
Celery tasks — background document ingestion pipeline.
M1 stub: updates status. Full pipeline in M2.
"""

import logging
from uuid import UUID

from celery import Task

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


class BaseIngestionTask(Task):
    """Base task that holds a synchronous DB session."""
    abstract = True


@celery_app.task(
    bind=True,
    base=BaseIngestionTask,
    name="app.workers.tasks.ingest_document_task",
    max_retries=3,
    default_retry_delay=30,
)
def ingest_document_task(self, document_id: str) -> dict:
    """
    Document ingestion pipeline.
    M1: stubs out to update status only.
    M2+: full parse → chunk → embed pipeline.
    """
    from app.core.config import get_settings
    from app.core.logging import get_logger
    from app.ingestion.pipeline import run_ingestion

    task_logger = get_logger("ingestion_task")
    task_logger.info("Ingestion started", document_id=document_id, task_id=self.request.id)

    try:
        result = run_ingestion(document_id=document_id)
        task_logger.info("Ingestion complete", document_id=document_id, result=result)
        return result

    except Exception as exc:
        task_logger.error(
            "Ingestion failed",
            document_id=document_id,
            error=str(exc),
            exc_info=True,
        )
        # Mark document as failed in DB
        _mark_document_failed(document_id, str(exc))
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 30)


def _mark_document_failed(document_id: str, error_msg: str) -> None:
    """Synchronous DB update — uses sync engine."""
    try:
        from sqlalchemy import create_engine, update
        from sqlalchemy.orm import Session

        from app.core.config import get_settings
        from app.models.models import Document

        settings = get_settings()
        engine = create_engine(settings.database_url_sync)

        with Session(engine) as session:
            session.execute(
                update(Document)
                .where(Document.id == document_id)
                .values(status="failed", error_msg=error_msg[:2000])
            )
            session.commit()
    except Exception as db_exc:
        logger.error("Could not mark document failed", error=str(db_exc))
