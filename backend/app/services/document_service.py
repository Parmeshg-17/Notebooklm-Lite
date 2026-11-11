import uuid
from typing import List
from fastapi import BackgroundTasks, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, NotFoundException
from app.models.document import Document
from app.models.notebook import Notebook
from app.models.user import User
from app.rag.ingestion.ingestion_pipeline import ingestion_pipeline
from app.rag.retrieval.qdrant_store import qdrant_store
from app.schemas.document import (
    DocumentResponse,
    DocumentStatusResponse,
    PresignedUploadRequest,
    PresignedUploadResponse,
)
from app.services.notebook_service import NotebookService
from app.services.storage_service import StorageService


class DocumentService:
    @staticmethod
    async def create_and_upload(
        db: AsyncSession,
        notebook_id: uuid.UUID,
        file: UploadFile,
        user: User,
        background_tasks: BackgroundTasks,
    ) -> DocumentResponse:
        """Verify notebook ownership, save uploaded file, and schedule ingestion."""
        # 1. Verify notebook exists and belongs to user
        await NotebookService.get_notebook_or_404(db, notebook_id, user)

        # 2. Save file
        filename, storage_path, file_size = await StorageService.save_upload_file(file, user.id)

        # 3. Create document record
        doc = Document(
            notebook_id=notebook_id,
            owner_id=user.id,
            filename=filename,
            storage_path=storage_path,
            file_type=file.content_type or "application/pdf",
            file_size=file_size,
            page_count=0,
            total_chunks=0,
            processing_status="UPLOADED",
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)

        # 4. Schedule background ingestion
        background_tasks.add_task(ingestion_pipeline.process_document, doc.id)

        return DocumentResponse.model_validate(doc)

    @staticmethod
    async def list_notebook_documents(
        db: AsyncSession,
        notebook_id: uuid.UUID,
        user: User,
    ) -> List[DocumentResponse]:
        """List documents in notebook, enforcing ownership."""
        # Verify notebook access (auto-registers if needed)
        await NotebookService.get_notebook_or_404(db, notebook_id, user)

        stmt = (
            select(Document)
            .where(Document.notebook_id == notebook_id, Document.owner_id == user.id)
            .order_by(Document.created_at.desc())
        )
        res = await db.execute(stmt)
        docs = res.scalars().all()
        return [DocumentResponse.model_validate(d) for d in docs]

    @staticmethod
    async def get_document_or_404(
        db: AsyncSession,
        document_id: uuid.UUID,
        user: User,
    ) -> Document:
        """Fetch document and verify ownership."""
        stmt = select(Document).where(Document.id == document_id)
        res = await db.execute(stmt)
        doc = res.scalar_one_or_none()
        if not doc:
            raise NotFoundException("Document not found")
        if doc.owner_id != user.id:
            raise ForbiddenException("You do not have access to this document")
        return doc

    STATUS_PROGRESS_MAP = {
        "UPLOADED": 10,
        "EXTRACTING": 25,
        "CHUNKING": 45,
        "EMBEDDING": 70,
        "INDEXING": 90,
        "INDEXED": 100,
        "FAILED": 0,
        # Backwards compatibility
        "PENDING": 10,
        "PROCESSING": 50,
    }

    @classmethod
    def calculate_status_progress(
        cls,
        status: str,
        error: Optional[str] = None,
    ) -> Tuple[int, bool, Optional[str]]:
        st = (status or "").upper()
        progress = cls.STATUS_PROGRESS_MAP.get(st, 50)
        is_failed = (st == "FAILED")
        return progress, is_failed, error

    @staticmethod
    async def get_document_status(
        db: AsyncSession,
        document_id: uuid.UUID,
        user: User,
    ) -> DocumentStatusResponse:
        doc = await DocumentService.get_document_or_404(db, document_id, user)
        progress, _, _ = DocumentService.calculate_status_progress(
            doc.processing_status, doc.processing_error
        )

        return DocumentStatusResponse(
            id=doc.id,
            status=doc.processing_status.lower(),
            progress=progress,
            page_count=doc.page_count,
            total_chunks=doc.total_chunks,
            error=doc.processing_error,
        )

    @staticmethod
    async def delete_document(
        db: AsyncSession,
        document_id: uuid.UUID,
        user: User,
    ) -> None:
        doc = await DocumentService.get_document_or_404(db, document_id, user)

        # Remove vector chunks
        await qdrant_store.delete_by_document(doc.id)

        # Remove file on disk
        StorageService.delete_file(doc.storage_path)

        # Delete database record
        await db.delete(doc)
        await db.commit()

    @staticmethod
    async def create_presigned_upload(
        db: AsyncSession,
        notebook_id: uuid.UUID,
        req: PresignedUploadRequest,
        user: User,
    ) -> PresignedUploadResponse:
        """Verify notebook access, create pending document record, and generate presigned S3 upload URL."""
        await NotebookService.get_notebook_or_404(db, notebook_id, user)
        upload_data = StorageService.generate_presigned_upload_url(
            user_id=user.id,
            filename=req.filename,
            content_type=req.file_type or "application/pdf",
        )
        doc = Document(
            notebook_id=notebook_id,
            owner_id=user.id,
            filename=upload_data["filename"],
            storage_path=upload_data["storage_path"],
            file_type=req.file_type or "application/pdf",
            file_size=req.file_size or 0,
            page_count=0,
            total_chunks=0,
            processing_status="PENDING_UPLOAD",
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
        return PresignedUploadResponse(
            upload_url=upload_data["upload_url"],
            document_id=doc.id,
            storage_path=upload_data["storage_path"],
            expires_in_seconds=upload_data["expires_in_seconds"],
        )

    @staticmethod
    async def confirm_presigned_upload(
        db: AsyncSession,
        document_id: uuid.UUID,
        user: User,
        background_tasks: BackgroundTasks,
    ) -> DocumentResponse:
        """Confirm direct S3 upload completion and trigger background ingestion."""
        doc = await DocumentService.get_document_or_404(db, document_id, user)
        doc.processing_status = "UPLOADED"
        await db.commit()
        await db.refresh(doc)
        background_tasks.add_task(ingestion_pipeline.process_document, doc.id)
        return DocumentResponse.model_validate(doc)

    @staticmethod
    async def retry_ingestion(
        db: AsyncSession,
        document_id: uuid.UUID,
        user: User,
        background_tasks: BackgroundTasks,
    ) -> DocumentStatusResponse:
        """Reset failed document state and schedule background re-ingestion."""
        doc = await DocumentService.get_document_or_404(db, document_id, user)
        doc.processing_status = "UPLOADED"
        doc.processing_error = None
        await db.commit()
        await db.refresh(doc)

        background_tasks.add_task(ingestion_pipeline.process_document, doc.id)

        progress, _, _ = DocumentService.calculate_status_progress(
            doc.processing_status, doc.processing_error
        )
        return DocumentStatusResponse(
            id=doc.id,
            status=doc.processing_status.lower(),
            progress=progress,
            page_count=doc.page_count,
            total_chunks=doc.total_chunks,
            error=doc.processing_error,
        )

