"""Pydantic schemas for request/response validation."""

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# ─── Notebooks ───────────────────────────────────────────────────────────────

class NotebookCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)


class NotebookResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    owner_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


class NotebookListResponse(BaseModel):
    notebooks: list[NotebookResponse]
    total: int


# ─── Documents ───────────────────────────────────────────────────────────────

DocumentStatus = Literal["uploaded", "parsing", "indexed", "failed"]


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    notebook_id: UUID
    filename: str
    status: DocumentStatus
    page_count: Optional[int] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    error_msg: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DocumentUploadResponse(BaseModel):
    document_id: UUID
    status: DocumentStatus
    message: str


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int


# ─── Chunks ──────────────────────────────────────────────────────────────────

class ChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    chunk_index: int
    page_start: int
    page_end: int
    text: str
    created_at: datetime


# ─── Conversations ────────────────────────────────────────────────────────────

class ConversationCreate(BaseModel):
    title: Optional[str] = None


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    notebook_id: UUID
    title: Optional[str] = None
    created_at: datetime


# ─── Messages & Ask ───────────────────────────────────────────────────────────

class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    conversation_id: Optional[UUID] = None


class CitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    marker: int
    quote: str
    page: int
    chunk_id: UUID
    document_id: Optional[UUID] = None
    filename: Optional[str] = None


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    role: str
    content: str
    not_found: bool = False
    citations: list[CitationResponse] = []
    created_at: datetime


# ─── Page Viewer ─────────────────────────────────────────────────────────────

class PageResponse(BaseModel):
    document_id: UUID
    page_number: int
    text: str
    total_pages: int


# ─── Health ──────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str = "0.1.0"


class ReadyResponse(BaseModel):
    status: str
    checks: dict[str, bool]
