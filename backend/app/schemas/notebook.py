import uuid
from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class NotebookBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default="", max_length=2000)
    category: Optional[str] = Field(default="General", max_length=100)


class NotebookCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default="", max_length=2000)
    category: Optional[str] = Field(default="General", max_length=100)
    tag: Optional[str] = None  # Frontend alias for category

    def get_category(self) -> str:
        return self.tag or self.category or "General"


class NotebookUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = None
    tag: Optional[str] = None
    is_starred: Optional[bool] = None
    isStarred: Optional[bool] = None  # Frontend camelCase alias


class CollaboratorResponse(BaseModel):
    id: str
    name: str
    avatar: Optional[str] = None


class NotebookResponse(NotebookBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    is_starred: bool
    created_at: datetime
    updated_at: datetime
    document_count: int = 0

    # Frontend compatibility fields
    tag: Optional[str] = None
    sourceCount: int = 0
    lastModified: Optional[str] = None
    createdAt: Optional[str] = None
    isStarred: bool = False
    isShared: bool = False
    owner: str = "Owner"
    collaborators: List[CollaboratorResponse] = []

    model_config = ConfigDict(from_attributes=True)

    def model_post_init(self, __context: Any) -> None:
        if self.tag is None:
            self.tag = self.category
        self.sourceCount = self.document_count
        self.isStarred = self.is_starred
        if self.lastModified is None:
            self.lastModified = self.updated_at.isoformat()
        if self.createdAt is None:
            self.createdAt = self.created_at.isoformat()

