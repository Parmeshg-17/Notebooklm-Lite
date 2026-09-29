"""
Notebook repository — data access layer for notebooks.
Keeps all SQL out of route handlers.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Notebook


class NotebookRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, title: str, owner_id: UUID | None = None) -> Notebook:
        notebook = Notebook(title=title, owner_id=owner_id)
        self._db.add(notebook)
        await self._db.flush()
        await self._db.refresh(notebook)
        return notebook

    async def get_by_id(self, notebook_id: UUID) -> Notebook | None:
        result = await self._db.execute(
            select(Notebook).where(Notebook.id == notebook_id)
        )
        return result.scalar_one_or_none()

    async def list_all(self, limit: int = 100, offset: int = 0) -> tuple[list[Notebook], int]:
        count_result = await self._db.execute(select(func.count()).select_from(Notebook))
        total = count_result.scalar_one()

        result = await self._db.execute(
            select(Notebook).order_by(Notebook.created_at.desc()).limit(limit).offset(offset)
        )
        notebooks = list(result.scalars().all())
        return notebooks, total

    async def delete(self, notebook: Notebook) -> None:
        await self._db.delete(notebook)
        await self._db.flush()
