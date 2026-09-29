"""
Document API routes — upload, list, status, delete.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.schemas import (
    DocumentListResponse,
    DocumentResponse,
    DocumentUploadResponse,
)
from app.services.document_service import DocumentService, DuplicateDocumentError
from app.services.notebook_service import NotebookService

router = APIRouter(tags=["Documents"])


@router.post(
    "/notebooks/{notebook_id}/documents",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a document to a notebook",
)
async def upload_document(
    notebook_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> DocumentUploadResponse:
    # Verify notebook exists
    notebook_svc = NotebookService(db)
    notebook = await notebook_svc.get_notebook(notebook_id)
    if notebook is None:
        raise HTTPException(status_code=404, detail="Notebook not found")

    doc_svc = DocumentService(db)
    try:
        doc = await doc_svc.upload_document(notebook_id=notebook_id, file=file)
    except DuplicateDocumentError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    return DocumentUploadResponse(
        document_id=doc.id,
        status=doc.status,
        message="Document uploaded. Processing has started.",
    )


@router.get(
    "/notebooks/{notebook_id}/documents",
    response_model=DocumentListResponse,
    summary="List documents in a notebook",
)
async def list_documents(
    notebook_id: UUID,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> DocumentListResponse:
    notebook_svc = NotebookService(db)
    notebook = await notebook_svc.get_notebook(notebook_id)
    if notebook is None:
        raise HTTPException(status_code=404, detail="Notebook not found")

    doc_svc = DocumentService(db)
    docs, total = await doc_svc.list_documents(notebook_id, limit=limit, offset=offset)
    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(d) for d in docs],
        total=total,
    )


@router.get(
    "/documents/{document_id}",
    response_model=DocumentResponse,
    summary="Get document status",
)
async def get_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    doc_svc = DocumentService(db)
    doc = await doc_svc.get_document(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse.model_validate(doc)


@router.get(
    "/documents/{document_id}/pages/{page_number}",
    summary="Get document page text and metadata for citation viewer",
)
async def get_document_page(
    document_id: UUID,
    page_number: int,
    db: AsyncSession = Depends(get_db),
):
    doc_svc = DocumentService(db)
    return await doc_svc.get_document_page(document_id, page_number)


@router.delete(
    "/notebooks/{notebook_id}/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document and all its chunks/embeddings",
)
async def delete_document(
    notebook_id: UUID,
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    doc_svc = DocumentService(db)
    deleted = await doc_svc.delete_document(document_id, notebook_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")


@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document by ID",
)
async def delete_document_direct(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    doc_svc = DocumentService(db)
    deleted = await doc_svc.delete_document(document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")

