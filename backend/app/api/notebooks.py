"""
Notebook API routes.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.schemas import (
    NotebookCreate,
    NotebookListResponse,
    NotebookResponse,
)
from app.services.notebook_service import NotebookService

router = APIRouter(prefix="/notebooks", tags=["Notebooks"])


@router.post(
    "",
    response_model=NotebookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new notebook",
)
async def create_notebook(
    payload: NotebookCreate,
    db: AsyncSession = Depends(get_db),
) -> NotebookResponse:
    service = NotebookService(db)
    notebook = await service.create_notebook(payload)
    return NotebookResponse.model_validate(notebook)


@router.get(
    "",
    response_model=NotebookListResponse,
    summary="List all notebooks",
)
async def list_notebooks(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> NotebookListResponse:
    service = NotebookService(db)
    notebooks, total = await service.list_notebooks(limit=limit, offset=offset)
    return NotebookListResponse(
        notebooks=[NotebookResponse.model_validate(n) for n in notebooks],
        total=total,
    )


@router.get(
    "/{notebook_id}",
    response_model=NotebookResponse,
    summary="Get a notebook by ID",
)
async def get_notebook(
    notebook_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> NotebookResponse:
    service = NotebookService(db)
    notebook = await service.get_notebook(notebook_id)
    if notebook is None:
        raise HTTPException(status_code=404, detail="Notebook not found")
    return NotebookResponse.model_validate(notebook)


@router.delete(
    "/{notebook_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a notebook and all its documents",
)
async def delete_notebook(
    notebook_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    service = NotebookService(db)
    deleted = await service.delete_notebook(notebook_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Notebook not found")
