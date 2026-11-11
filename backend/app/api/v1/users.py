from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.conversation import Conversation
from app.models.document import Document
from app.models.message import Message
from app.models.notebook import Notebook
from app.models.user import User
from app.schemas.user import UserResponse
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


@router.get("/me/stats")
async def get_user_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve user statistics for the dashboard."""
    # Total notebooks
    nb_stmt = select(func.count(Notebook.id)).where(Notebook.owner_id == current_user.id)
    nb_res = await db.execute(nb_stmt)
    total_notebooks = nb_res.scalar_one() or 0

    # Total documents
    doc_stmt = select(func.count(Document.id)).where(Document.owner_id == current_user.id)
    doc_res = await db.execute(doc_stmt)
    total_documents = doc_res.scalar_one() or 0

    # Total storage used
    storage_stmt = select(func.sum(Document.file_size)).where(Document.owner_id == current_user.id)
    storage_res = await db.execute(storage_stmt)
    total_storage_bytes = storage_res.scalar_one() or 0

    # Total questions asked (user messages)
    msg_stmt = (
        select(func.count(Message.id))
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(Conversation.user_id == current_user.id, Message.role == "user")
    )
    msg_res = await db.execute(msg_stmt)
    total_questions = msg_res.scalar_one() or 0

    return {
        "total_notebooks": total_notebooks,
        "total_documents": total_documents,
        "questions_asked": total_questions,
        "storage_used_bytes": total_storage_bytes,
        "storage_used_mb": round(total_storage_bytes / (1024 * 1024), 2),
    }

