import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.document import Document
    from app.models.conversation import Conversation


class Notebook(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "notebooks"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default="")
    category: Mapped[str] = mapped_column(String(100), nullable=False, default="General")
    is_starred: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="notebooks")
    documents: Mapped[List["Document"]] = relationship(
        "Document",
        back_populates="notebook",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    conversations: Mapped[List["Conversation"]] = relationship(
        "Conversation",
        back_populates="notebook",
        cascade="all, delete-orphan",
    )

