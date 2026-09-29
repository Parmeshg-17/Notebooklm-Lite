"""
Document repository — data access layer for documents.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Document


class DocumentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(
        self,
        notebook_id: UUID,
        filename: str,
        storage_key: str,
        sha256: str,
        file_size: int | None = None,
        mime_type: str | None = None,
    ) -> Document:
        doc = Document(
            notebook_id=notebook_id,
            filename=filename,
            storage_key=storage_key,
            sha256=sha256,
            file_size=file_size,
            mime_type=mime_type,
            status="uploaded",
        )
        self._db.add(doc)
        await self._db.flush()
        await self._db.refresh(doc)
        return doc

    async def get_by_id(self, doc_id: UUID) -> Document | None:
        result = await self._db.execute(
            select(Document).where(Document.id == doc_id)
        )
        return result.scalar_one_or_none()

    async def list_by_notebook(
        self,
        notebook_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[Document], int]:
        count_q = await self._db.execute(
            select(func.count()).select_from(Document).where(
                Document.notebook_id == notebook_id
            )
        )
        total = count_q.scalar_one()

        result = await self._db.execute(
            select(Document)
            .where(Document.notebook_id == notebook_id)
            .order_by(Document.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all()), total

    async def find_duplicate(self, notebook_id: UUID, sha256: str) -> Document | None:
        result = await self._db.execute(
            select(Document).where(
                Document.notebook_id == notebook_id,
                Document.sha256 == sha256,
            )
        )
        return result.scalar_one_or_none()

    async def update_status(
        self,
        doc: Document,
        status: str,
        error_msg: str | None = None,
        page_count: int | None = None,
    ) -> Document:
        doc.status = status
        if error_msg is not None:
            doc.error_msg = error_msg
        if page_count is not None:
            doc.page_count = page_count
        await self._db.flush()
        await self._db.refresh(doc)
        return doc

    async def delete(self, doc: Document) -> None:
        await self._db.delete(doc)
        await self._db.flush()
