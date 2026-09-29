"""
Document service — handles upload flow and queues ingestion.
"""

import hashlib
import io
import uuid
from uuid import UUID

from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.document_repo import DocumentRepository
from app.models.models import Document
from app.services.storage import get_storage_service

logger = get_logger(__name__)
settings = get_settings()

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "text/plain",
    "text/markdown",
    "text/x-markdown",
    "application/octet-stream",  # sometimes sent for .md files
}

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".markdown"}


class DuplicateDocumentError(Exception):
    """Raised when a document with the same SHA-256 already exists in the notebook."""
    pass


class DocumentService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._repo = DocumentRepository(db)
        self._storage = get_storage_service()

    async def upload_document(
        self,
        notebook_id: UUID,
        file: UploadFile,
    ) -> Document:
        """
        Full upload flow:
        1. Validate file type/size
        2. Compute SHA-256
        3. Check deduplication
        4. Upload to object storage
        5. Create DB record
        6. Queue ingestion job
        """
        # ── Validation ──────────────────────────────────────────────────
        self._validate_file_extension(file.filename or "")

        content = await file.read()
        file_size = len(content)

        max_bytes = settings.max_upload_size_mb * 1024 * 1024
        if file_size > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds maximum size of {settings.max_upload_size_mb} MB",
            )

        if file_size == 0:
            raise HTTPException(status_code=400, detail="File is empty")

        # ── SHA-256 ──────────────────────────────────────────────────────
        sha256 = hashlib.sha256(content).hexdigest()

        # ── Deduplication ────────────────────────────────────────────────
        existing = await self._repo.find_duplicate(notebook_id, sha256)
        if existing is not None:
            raise DuplicateDocumentError(
                f"Document with identical content already exists: {existing.filename}"
            )

        # ── Object storage ───────────────────────────────────────────────
        ext = self._get_extension(file.filename or "")
        storage_key = f"notebooks/{notebook_id}/documents/{uuid.uuid4()}{ext}"
        mime_type = file.content_type or "application/octet-stream"

        self._storage.upload_file(
            io.BytesIO(content),
            storage_key,
            content_type=mime_type,
        )

        # ── DB record ────────────────────────────────────────────────────
        doc = await self._repo.create(
            notebook_id=notebook_id,
            filename=file.filename or "unknown",
            storage_key=storage_key,
            sha256=sha256,
            file_size=file_size,
            mime_type=mime_type,
        )

        logger.info(
            "Document uploaded",
            document_id=str(doc.id),
            notebook_id=str(notebook_id),
            filename=file.filename,
            size=file_size,
        )

        # ── Queue ingestion ──────────────────────────────────────────────
        try:
            from app.workers.tasks import ingest_document_task
            ingest_document_task.delay(str(doc.id))
        except Exception as exc:
            logger.info("Celery queueing bypassed, using background thread", error=str(exc))

        # Direct background thread execution for instant indexing
        import threading
        from app.ingestion.pipeline import run_ingestion
        threading.Thread(target=run_ingestion, args=(str(doc.id),), daemon=True).start()

        return doc

    async def get_document(self, doc_id: UUID) -> Document | None:
        return await self._repo.get_by_id(doc_id)

    async def list_documents(
        self,
        notebook_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Document], int]:
        return await self._repo.list_by_notebook(notebook_id, limit=limit, offset=offset)

    async def delete_document(self, doc_id: UUID, notebook_id: UUID | None = None) -> bool:
        doc = await self._repo.get_by_id(doc_id)
        if doc is None:
            return False
        if notebook_id is not None and doc.notebook_id != notebook_id:
            return False

        # Remove from object storage
        try:
            self._storage.delete_file(doc.storage_key)
        except Exception as exc:
            logger.warning("Could not delete from storage", error=str(exc), key=doc.storage_key)

        await self._repo.delete(doc)
        logger.info("Document deleted", document_id=str(doc_id))
        return True

    async def get_document_page(self, doc_id: UUID, page_number: int) -> dict:
        doc = await self._repo.get_by_id(doc_id)
        if doc is None:
            raise HTTPException(status_code=404, detail="Document not found")

        from sqlalchemy import select
        from app.models.models import Chunk

        # Try fetching from stored chunks first
        stmt = (
            select(Chunk)
            .where(
                Chunk.document_id == doc_id,
                Chunk.page_start <= page_number,
                Chunk.page_end >= page_number,
            )
            .order_by(Chunk.chunk_index)
        )
        res = await self._db.execute(stmt)
        chunks = res.scalars().all()

        text_content = ""
        if chunks:
            text_content = "\n\n".join(c.text for c in chunks)
        else:
            # Fallback to direct parsing from storage
            try:
                from app.ingestion.parser import DocumentParser
                file_bytes = self._storage.download_file(doc.storage_key)
                parser = DocumentParser()
                parsed = parser.parse_bytes(file_bytes, doc.filename)
                for p in parsed.pages:
                    if p.page_number == page_number:
                        text_content = p.text
                        break
            except Exception as e:
                logger.warning("Could not parse page from storage", error=str(e))

        return {
            "document_id": str(doc.id),
            "filename": doc.filename,
            "page_number": page_number,
            "page_count": doc.page_count or 1,
            "text": text_content,
        }

    # ─── Internal helpers ────────────────────────────────────────────────

    @staticmethod
    def _validate_file_extension(filename: str) -> None:
        ext = DocumentService._get_extension(filename).lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
            )

    @staticmethod
    def _get_extension(filename: str) -> str:
        import os
        _, ext = os.path.splitext(filename)
        return ext or ""
