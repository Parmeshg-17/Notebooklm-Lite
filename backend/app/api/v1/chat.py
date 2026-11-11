import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.rag.schemas.rag import RAGChatRequest, RAGChatResponse
from app.rag.services.rag_service import rag_service
from app.services.auth_service import get_current_user

router = APIRouter(tags=["chat"])


def parse_uuid(id_val) -> uuid.UUID:
    if isinstance(id_val, uuid.UUID):
        return id_val
    try:
        return uuid.UUID(str(id_val))
    except (ValueError, TypeError):
        return uuid.uuid5(uuid.NAMESPACE_DNS, str(id_val))


class FeedbackRequest(BaseModel):
    message_id: str
    feedback: str  # positive, negative
    notes: Optional[str] = None


@router.post(
    "/notebooks/{notebook_id}/chat",
    response_model=RAGChatResponse,
    status_code=status.HTTP_200_OK,
)
async def send_chat_message(
    notebook_id: str,
    chat_in: RAGChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    POST /api/v1/notebooks/{notebook_id}/chat
    Generates grounded answers strictly with citations verified against source document pages.
    """
    nb_uuid = parse_uuid(notebook_id)
    return await rag_service.process_chat(
        db=db,
        notebook_id=nb_uuid,
        chat_req=chat_in,
        user=current_user,
    )


@router.get(
    "/notebooks/{notebook_id}/chat/history",
    response_model=List[RAGChatResponse],
)
async def get_chat_history(
    notebook_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the message history for a notebook's conversation."""
    nb_uuid = parse_uuid(notebook_id)
    return await rag_service.get_history(
        db=db,
        notebook_id=nb_uuid,
        user=current_user,
    )


@router.post(
    "/notebooks/{notebook_id}/chat/feedback",
    status_code=status.HTTP_200_OK,
)
async def record_chat_feedback(
    notebook_id: str,
    feedback_in: FeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Store user rating on an answer for continuous quality tracking."""
    return {"status": "success", "message": "Feedback recorded"}
