import os
import uuid
from typing import List, Union
from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile, status
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.db.session import get_db
from app.models.document import Document
from app.models.user import User
from app.schemas.document import (
    DocumentResponse,
    DocumentStatusResponse,
    PresignedUploadRequest,
    PresignedUploadResponse,
)
from app.services.auth_service import get_current_user
from app.services.document_service import DocumentService
from app.services.storage_service import StorageService

router = APIRouter(tags=["documents"])


def parse_uuid(id_val: Union[str, uuid.UUID]) -> uuid.UUID:
    if isinstance(id_val, uuid.UUID):
        return id_val
    try:
        return uuid.UUID(str(id_val))
    except (ValueError, TypeError):
        return uuid.uuid5(uuid.NAMESPACE_DNS, str(id_val))


@router.post(
    "/notebooks/{notebook_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    notebook_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a document to a notebook and start background ingestion."""
    nb_uuid = parse_uuid(notebook_id)
    return await DocumentService.create_and_upload(
        db=db,
        notebook_id=nb_uuid,
        file=file,
        user=current_user,
        background_tasks=background_tasks,
    )


@router.get(
    "/notebooks/{notebook_id}/documents",
    response_model=List[DocumentResponse],
)
async def list_documents(
    notebook_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all documents belonging to a notebook."""
    nb_uuid = parse_uuid(notebook_id)
    return await DocumentService.list_notebook_documents(
        db=db,
        notebook_id=nb_uuid,
        user=current_user,
    )


@router.get(
    "/documents/{document_id}",
    response_model=DocumentResponse,
)
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get document metadata and details."""
    doc_uuid = parse_uuid(document_id)
    doc = await DocumentService.get_document_or_404(db, doc_uuid, current_user)
    return DocumentResponse.model_validate(doc)


@router.post(
    "/notebooks/{notebook_id}/documents/presigned-upload",
    response_model=PresignedUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_presigned_upload(
    notebook_id: str,
    req: PresignedUploadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a presigned S3 PUT URL for direct-to-S3 document uploads."""
    nb_uuid = parse_uuid(notebook_id)
    return await DocumentService.create_presigned_upload(
        db=db,
        notebook_id=nb_uuid,
        req=req,
        user=current_user,
    )


@router.post(
    "/documents/{document_id}/confirm-upload",
    response_model=DocumentResponse,
)
async def confirm_upload(
    document_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Confirm completion of client S3 upload and schedule background ingestion."""
    doc_uuid = parse_uuid(document_id)
    return await DocumentService.confirm_presigned_upload(
        db=db,
        document_id=doc_uuid,
        user=current_user,
        background_tasks=background_tasks,
    )


@router.get("/documents/{document_id}/file")
async def get_document_file(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Serve document file for browser inline viewing in PDF viewer.
    Enforces tenant access control and issues presigned S3 redirect if hosted in AWS.
    """
    doc_uuid = parse_uuid(document_id)
    doc = await DocumentService.get_document_or_404(db, doc_uuid, current_user)

    # 1. If stored in S3, redirect securely to short-lived presigned download URL
    if doc.storage_path.startswith("s3://"):
        presigned_url = StorageService.generate_presigned_download_url(
            doc.storage_path, filename=doc.filename, expires_in=900
        )
        if presigned_url:
            return RedirectResponse(url=presigned_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    # 2. Local storage fallback
    if not os.path.exists(doc.storage_path):
        raise NotFoundException("Physical file not found on disk")
    return FileResponse(
        path=doc.storage_path,
        media_type=doc.file_type or "application/pdf",
        filename=doc.filename,
        content_disposition_type="inline",
    )


@router.get(
    "/documents/{document_id}/status",
    response_model=DocumentStatusResponse,
)
async def get_document_status(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get document processing status and progress."""
    doc_uuid = parse_uuid(document_id)
    return await DocumentService.get_document_status(db, doc_uuid, current_user)


@router.post(
    "/documents/{document_id}/retry",
    response_model=DocumentStatusResponse,
)
async def retry_document_ingestion(
    document_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retry ingestion for a document."""
    doc_uuid = parse_uuid(document_id)
    return await DocumentService.retry_ingestion(db, doc_uuid, current_user, background_tasks)


@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a document, its physical storage file, and indexed vectors."""
    doc_uuid = parse_uuid(document_id)
    await DocumentService.delete_document(db, doc_uuid, current_user)
