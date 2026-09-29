"""
Notebook service — business logic for notebook operations.
"""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.notebook_repo import NotebookRepository
from app.models.models import Notebook
from app.schemas.schemas import NotebookCreate

logger = get_logger(__name__)


class NotebookService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = NotebookRepository(db)

    async def create_notebook(self, payload: NotebookCreate, owner_id: UUID | None = None) -> Notebook:
        notebook = await self._repo.create(title=payload.title, owner_id=owner_id)
        logger.info("Notebook created", notebook_id=str(notebook.id), title=notebook.title)
        return notebook

    async def get_notebook(self, notebook_id: UUID) -> Notebook | None:
        return await self._repo.get_by_id(notebook_id)

    async def list_notebooks(self, limit: int = 100, offset: int = 0) -> tuple[list[Notebook], int]:
        return await self._repo.list_all(limit=limit, offset=offset)

    async def delete_notebook(self, notebook_id: UUID) -> bool:
        notebook = await self._repo.get_by_id(notebook_id)
        if notebook is None:
            return False
        await self._repo.delete(notebook)
        logger.info("Notebook deleted", notebook_id=str(notebook_id))
        return True
