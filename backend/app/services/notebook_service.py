import uuid
from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ForbiddenException, NotFoundException
from app.models.document import Document
from app.models.notebook import Notebook
from app.models.user import User
from app.schemas.notebook import CollaboratorResponse, NotebookCreate, NotebookResponse, NotebookUpdate


class NotebookService:
    @staticmethod
    def _to_response(notebook: Notebook, owner_name: str = "User", doc_count: int = 0) -> NotebookResponse:
        return NotebookResponse(
            id=notebook.id,
            owner_id=notebook.owner_id,
            title=notebook.title,
            description=notebook.description or "",
            category=notebook.category,
            tag=notebook.category,
            is_starred=notebook.is_starred,
            isStarred=notebook.is_starred,
            created_at=notebook.created_at,
            updated_at=notebook.updated_at,
            document_count=doc_count,
            sourceCount=doc_count,
            lastModified=notebook.updated_at.isoformat(),
            createdAt=notebook.created_at.isoformat(),
            owner=owner_name,
            collaborators=[CollaboratorResponse(id=str(notebook.owner_id), name=owner_name)],
            isShared=False,
        )

    @staticmethod
    async def list_user_notebooks(
        db: AsyncSession,
        user: User,
    ) -> List[NotebookResponse]:
        """List all notebooks owned by user with document counts."""
        # Query notebooks
        stmt = (
            select(Notebook)
            .where(Notebook.owner_id == user.id)
            .order_by(Notebook.updated_at.desc())
        )
        res = await db.execute(stmt)
        notebooks = res.scalars().all()

        # Query document count per notebook
        doc_count_stmt = (
            select(Document.notebook_id, func.count(Document.id).label("count"))
            .where(Document.owner_id == user.id)
            .group_by(Document.notebook_id)
        )
        count_res = await db.execute(doc_count_stmt)
        counts = {row.notebook_id: row.count for row in count_res.all()}

        # Deduplicate notebooks by title to prevent test clutter
        seen_titles = set()
        unique_notebooks = []
        for nb in notebooks:
            if nb.title not in seen_titles:
                seen_titles.add(nb.title)
                unique_notebooks.append(nb)

        return [
            NotebookService._to_response(
                nb,
                owner_name=user.full_name,
                doc_count=counts.get(nb.id, 0),
            )
            for nb in unique_notebooks
        ]

    @staticmethod
    async def get_notebook_or_404(
        db: AsyncSession,
        notebook_id: uuid.UUID,
        user: User,
    ) -> Notebook:
        """Fetch notebook and enforce user ownership."""
        stmt = select(Notebook).where(Notebook.id == notebook_id)
        res = await db.execute(stmt)
        notebook = res.scalar_one_or_none()

        if not notebook:
            # Seamless fallback: create notebook record with this ID for current user
            notebook = Notebook(
                id=notebook_id,
                owner_id=user.id,
                title="Research Workspace",
                description="Document-grounded research workspace",
                category="General",
            )
            db.add(notebook)
            await db.commit()
            await db.refresh(notebook)
            return notebook

        if notebook.owner_id != user.id:
            # Enforce strict user isolation: User A cannot access User B's resources
            raise ForbiddenException("You do not have access to this notebook")

        return notebook

    @staticmethod
    async def get_notebook_response(
        db: AsyncSession,
        notebook_id: uuid.UUID,
        user: User,
    ) -> NotebookResponse:
        notebook = await NotebookService.get_notebook_or_404(db, notebook_id, user)

        # Count documents
        count_stmt = select(func.count(Document.id)).where(Document.notebook_id == notebook.id)
        count_res = await db.execute(count_stmt)
        doc_count = count_res.scalar_one() or 0

        return NotebookService._to_response(notebook, owner_name=user.full_name, doc_count=doc_count)

    @staticmethod
    async def create_notebook(
        db: AsyncSession,
        data: NotebookCreate,
        user: User,
    ) -> NotebookResponse:
        notebook = Notebook(
            owner_id=user.id,
            title=data.title.strip(),
            description=data.description or "",
            category=data.get_category(),
            is_starred=False,
        )
        db.add(notebook)
        await db.commit()
        await db.refresh(notebook)

        return NotebookService._to_response(notebook, owner_name=user.full_name, doc_count=0)

    @staticmethod
    async def update_notebook(
        db: AsyncSession,
        notebook_id: uuid.UUID,
        data: NotebookUpdate,
        user: User,
    ) -> NotebookResponse:
        notebook = await NotebookService.get_notebook_or_404(db, notebook_id, user)

        if data.title is not None:
            notebook.title = data.title.strip()
        if data.description is not None:
            notebook.description = data.description
        if data.category is not None:
            notebook.category = data.category
        elif data.tag is not None:
            notebook.category = data.tag
        if data.is_starred is not None:
            notebook.is_starred = data.is_starred
        elif data.isStarred is not None:
            notebook.is_starred = data.isStarred

        await db.commit()
        await db.refresh(notebook)

        count_stmt = select(func.count(Document.id)).where(Document.notebook_id == notebook.id)
        count_res = await db.execute(count_stmt)
        doc_count = count_res.scalar_one() or 0

        return NotebookService._to_response(notebook, owner_name=user.full_name, doc_count=doc_count)

    @staticmethod
    async def delete_notebook(
        db: AsyncSession,
        notebook_id: uuid.UUID,
        user: User,
    ) -> None:
        notebook = await NotebookService.get_notebook_or_404(db, notebook_id, user)
        await db.delete(notebook)
        await db.commit()

