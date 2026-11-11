from typing import Any, Dict, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.document import Document
from app.models.notebook import Notebook
from app.models.user import User
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=List[Dict[str, Any]])
async def search_all(
    q: str = Query(..., min_length=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Global search across user's notebooks and documents."""
    term = f"%{q.strip().lower()}%"
    results: List[Dict[str, Any]] = []

    # 1. Search notebooks
    nb_stmt = (
        select(Notebook)
        .where(
            Notebook.owner_id == current_user.id,
            or_(
                Notebook.title.ilike(term),
                Notebook.description.ilike(term),
                Notebook.category.ilike(term),
            ),
        )
        .limit(10)
    )
    nb_res = await db.execute(nb_stmt)
    for nb in nb_res.scalars().all():
        results.append({
            "type": "notebook",
            "notebookId": str(nb.id),
            "title": nb.title,
            "snippet": nb.description or f"Category: {nb.category}",
            "matchedTerms": [q],
            "score": 0.95,
        })

    # 2. Search documents
    doc_stmt = (
        select(Document)
        .where(
            Document.owner_id == current_user.id,
            Document.filename.ilike(term),
        )
        .limit(10)
    )
    doc_res = await db.execute(doc_stmt)
    for doc in doc_res.scalars().all():
        results.append({
            "type": "document",
            "notebookId": str(doc.notebook_id),
            "documentId": str(doc.id),
            "title": doc.filename,
            "snippet": f"{doc.page_count} pages • {doc.file_type}",
            "matchedTerms": [q],
            "score": 0.90,
        })

    return results

