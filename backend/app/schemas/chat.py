import uuid
from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, Field


class CitationResponse(BaseModel):
    id: str
    documentId: str
    documentName: str
    pageNumber: int
    excerpt: str
    relevanceScore: float = 0.0


def parse_uuid_safe(val: Any) -> Optional[uuid.UUID]:
    if not val:
        return None
    if isinstance(val, uuid.UUID):
        return val
    try:
        return uuid.UUID(str(val))
    except (ValueError, TypeError):
        return uuid.uuid5(uuid.NAMESPACE_DNS, str(val))


class ChatRequest(BaseModel):
    message: Optional[str] = None
    content: Optional[str] = None  # Frontend alias
    conversation_id: Optional[Any] = None
    conversationId: Optional[Any] = None  # Frontend alias
    document_ids: Optional[List[Any]] = None
    documentIds: Optional[List[Any]] = None  # Frontend alias
    selectedDocumentIds: Optional[List[Any]] = None  # Frontend alias

    def get_message(self) -> str:
        msg = self.content or self.message
        if not msg or not msg.strip():
            raise ValueError("Message content cannot be empty")
        return msg.strip()

    def get_conversation_id(self) -> Optional[uuid.UUID]:
        raw = self.conversationId or self.conversation_id
        return parse_uuid_safe(raw)

    def get_document_ids(self) -> Optional[List[uuid.UUID]]:
        raw = self.selectedDocumentIds or self.documentIds or self.document_ids
        if not raw:
            return None
        res = []
        for item in raw:
            parsed = parse_uuid_safe(item)
            if parsed:
                res.append(parsed)
        return res


class ChatResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str = "assistant"
    content: str
    citations: List[CitationResponse] = []
    token_usage: int = 0
    latency_ms: int = 0
    created_at: datetime
    timestamp: Optional[str] = None

    def model_post_init(self, __context: Any) -> None:
        if self.timestamp is None:
            self.timestamp = self.created_at.isoformat()


class ConversationResponse(BaseModel):
    id: uuid.UUID
    notebook_id: uuid.UUID
    title: str
    created_at: datetime
    messages: List[ChatResponse] = []
