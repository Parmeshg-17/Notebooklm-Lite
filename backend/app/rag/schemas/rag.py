import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


def parse_uuid_safe(val: Any) -> Optional[uuid.UUID]:
    if not val:
        return None
    if isinstance(val, uuid.UUID):
        return val
    try:
        return uuid.UUID(str(val))
    except (ValueError, TypeError):
        return uuid.uuid5(uuid.NAMESPACE_DNS, str(val))


class RAGCitation(BaseModel):
    document_id: str = ""
    filename: str = "Document"
    page_number: int = 1
    chunk_id: str = ""
    excerpt: str = ""
    claim: str = ""

    # Frontend aliases
    id: Optional[str] = None
    documentId: Optional[str] = None
    documentName: Optional[str] = None
    pageNumber: Optional[int] = None
    relevanceScore: float = 1.0

    def model_post_init(self, __context: Any) -> None:
        if not self.chunk_id and self.id:
            self.chunk_id = self.id
        elif not self.id and self.chunk_id:
            self.id = self.chunk_id

        if not self.document_id and self.documentId:
            self.document_id = self.documentId
        elif not self.documentId and self.document_id:
            self.documentId = self.document_id

        if not self.filename and self.documentName:
            self.filename = self.documentName
        elif not self.documentName and self.filename:
            self.documentName = self.filename

        if self.pageNumber is None:
            self.pageNumber = self.page_number
        elif self.page_number == 1 and self.pageNumber != 1:
            self.page_number = self.pageNumber


class RetrievalMetadata(BaseModel):
    retrieved_chunks: int = 0
    selected_chunks: int = 0


class PerformanceMetrics(BaseModel):
    retrieval_latency_ms: int = 0
    generation_latency_ms: int = 0
    total_latency_ms: int = 0


class UsageMetrics(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0


class RAGChatRequest(BaseModel):
    question: Optional[str] = None
    message: Optional[str] = None  # Frontend alias
    content: Optional[str] = None  # Frontend alias
    conversation_id: Optional[Any] = None
    conversationId: Optional[Any] = None
    source_ids: Optional[List[Any]] = None
    document_ids: Optional[List[Any]] = None
    documentIds: Optional[List[Any]] = None
    selectedDocumentIds: Optional[List[Any]] = None

    def get_question(self) -> str:
        q = self.question or self.content or self.message
        if not q or not q.strip():
            raise ValueError("Query / question cannot be empty")
        return q.strip()

    def get_conversation_id(self) -> Optional[uuid.UUID]:
        raw = self.conversation_id or self.conversationId
        return parse_uuid_safe(raw)

    def get_source_ids(self) -> Optional[List[uuid.UUID]]:
        raw = self.source_ids or self.selectedDocumentIds or self.document_ids or self.documentIds
        if not raw:
            return None
        res = []
        for item in raw:
            parsed = parse_uuid_safe(item)
            if parsed:
                res.append(parsed)
        return res


class RAGChatResponse(BaseModel):
    id: uuid.UUID
    answer: str
    content: str  # Frontend alias
    conversation_id: uuid.UUID
    citations: List[RAGCitation] = []
    grounded: bool = True
    insufficient_evidence: bool = False
    retrieval_metadata: RetrievalMetadata = Field(default_factory=RetrievalMetadata)
    performance: PerformanceMetrics = Field(default_factory=PerformanceMetrics)
    usage: UsageMetrics = Field(default_factory=UsageMetrics)
    role: str = "assistant"
    created_at: datetime
    timestamp: Optional[str] = None
    token_usage: int = 0
    latency_ms: int = 0
    intent: Optional[str] = None
    tools_used: Optional[List[str]] = None

    def model_post_init(self, __context: Any) -> None:
        if self.timestamp is None:
            self.timestamp = self.created_at.isoformat()
        if not self.content and self.answer:
            self.content = self.answer
        if not self.answer and self.content:
            self.answer = self.content
        if self.token_usage == 0:
            self.token_usage = self.usage.input_tokens + self.usage.output_tokens
