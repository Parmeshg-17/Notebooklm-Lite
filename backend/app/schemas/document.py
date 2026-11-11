import uuid
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


class DocumentBase(BaseModel):
    filename: str
    file_type: str = "pdf"
    file_size: int = 0


class DocumentResponse(BaseModel):
    id: uuid.UUID
    notebook_id: uuid.UUID
    owner_id: uuid.UUID
    filename: str
    file_type: str
    file_size: int
    page_count: int
    total_chunks: int
    processing_status: str  # PENDING, PROCESSING, INDEXED, FAILED
    processing_error: Optional[str] = None
    created_at: datetime

    # Frontend compatibility fields
    notebookId: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None
    size: Optional[int] = None
    pageCount: Optional[int] = None
    tokenCount: Optional[int] = 0
    chunkCount: Optional[int] = None
    status: Optional[str] = None  # uploading, processing, indexed, failed
    progress: int = 100
    uploadedAt: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    def model_post_init(self, __context: Any) -> None:
        if self.notebookId is None:
            self.notebookId = str(self.notebook_id)
        if self.name is None:
            self.name = self.filename
        if self.type is None:
            self.type = "pdf" if "pdf" in self.file_type.lower() else "txt"
        if self.size is None:
            self.size = self.file_size
        if self.pageCount is None:
            self.pageCount = self.page_count
        if self.chunkCount is None:
            self.chunkCount = self.total_chunks
        if not self.tokenCount:
            if self.total_chunks > 0:
                self.tokenCount = self.total_chunks * 200
            elif self.page_count > 0:
                self.tokenCount = self.page_count * 350
            else:
                self.tokenCount = max(100, int(self.file_size / 4))
        if self.uploadedAt is None:
            self.uploadedAt = self.created_at.isoformat()

        # Map processing status to frontend status
        status_lower = self.processing_status.lower()
        if status_lower in ("pending", "processing"):
            self.status = "processing"
            self.progress = 50
        elif status_lower == "indexed":
            self.status = "indexed"
            self.progress = 100
        elif status_lower == "failed":
            self.status = "failed"
            self.progress = 0
        else:
            self.status = status_lower


class DocumentStatusResponse(BaseModel):
    id: uuid.UUID
    status: str
    progress: int
    page_count: int = 0
    total_chunks: int = 0
    error: Optional[str] = None


class PresignedUploadRequest(BaseModel):
    filename: str
    file_type: str = "application/pdf"
    file_size: int = 0


class PresignedUploadResponse(BaseModel):
    upload_url: str
    document_id: uuid.UUID
    storage_path: str
    expires_in_seconds: int

