import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.notebook import NotebookCreate, NotebookResponse, NotebookUpdate
from app.services.auth_service import get_current_user
from app.services.notebook_service import NotebookService

router = APIRouter(prefix="/notebooks", tags=["notebooks"])


def parse_uuid(id_val) -> uuid.UUID:
    if isinstance(id_val, uuid.UUID):
        return id_val
    try:
        return uuid.UUID(str(id_val))
    except (ValueError, TypeError):
        return uuid.uuid5(uuid.NAMESPACE_DNS, str(id_val))


@router.post("", response_model=NotebookResponse, status_code=status.HTTP_201_CREATED)
async def create_notebook(
    notebook_in: NotebookCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new notebook for the current user."""
    return await NotebookService.create_notebook(db, notebook_in, current_user)


@router.get("", response_model=List[NotebookResponse])
async def list_notebooks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all notebooks owned by the current user."""
    return await NotebookService.list_user_notebooks(db, current_user)


@router.get("/{notebook_id}", response_model=NotebookResponse)
async def get_notebook(
    notebook_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific notebook by ID (enforcing user ownership)."""
    nb_uuid = parse_uuid(notebook_id)
    return await NotebookService.get_notebook_response(db, nb_uuid, current_user)


@router.patch("/{notebook_id}", response_model=NotebookResponse)
async def update_notebook(
    notebook_id: str,
    notebook_in: NotebookUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a notebook title, description, category, or starred status."""
    nb_uuid = parse_uuid(notebook_id)
    return await NotebookService.update_notebook(db, nb_uuid, notebook_in, current_user)


@router.delete("/{notebook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notebook(
    notebook_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a notebook and all associated documents/conversations."""
    nb_uuid = parse_uuid(notebook_id)
    await NotebookService.delete_notebook(db, nb_uuid, current_user)

