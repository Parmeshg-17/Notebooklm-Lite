import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, List, Optional
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.conversation import Conversation


class Message(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False)  # user, assistant, system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_usage: Mapped[Optional[int]] = mapped_column(Integer, default=0, nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, default=0, nullable=True)
    citations: Mapped[Optional[List[Any]]] = mapped_column(JSON, default=list, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")

