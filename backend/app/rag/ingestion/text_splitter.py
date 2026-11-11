import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings


@dataclass
class DocumentChunk:
    chunk_id: str
    user_id: str
    notebook_id: str
    document_id: str
    filename: str
    page_number: int
    chunk_index: int
    chunk_text: str
    contributing_pages: List[int] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "user_id": self.user_id,
            "owner_id": self.user_id,  # For backward-compatible Qdrant filter
            "notebook_id": self.notebook_id,
            "document_id": self.document_id,
            "filename": self.filename,
            "page_number": self.page_number,
            "chunk_index": self.chunk_index,
            "chunk_text": self.chunk_text,
            "text": self.chunk_text,  # For backward-compatible Qdrant payload
            "contributing_pages": self.contributing_pages or [self.page_number],
        }


class DocumentSplitter:
    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
            keep_separator=True,
        )

    def split_pages(
        self,
        pages: List[Dict[str, Any]],
        document_id: uuid.UUID,
        notebook_id: uuid.UUID,
        user_id: uuid.UUID,
        filename: str = "",
    ) -> List[DocumentChunk]:
        """
        Splits extracted pages into chunks while preserving 1-indexed page boundaries
        and generating deterministic, stable chunk UUIDs.
        """
        chunks: List[DocumentChunk] = []
        global_chunk_idx = 0

        doc_id_str = str(document_id)
        nb_id_str = str(notebook_id)
        u_id_str = str(user_id)

        for page in pages:
            page_num = int(page.get("page_number", 1))
            page_text = page.get("text", "").strip()

            if not page_text:
                continue

            splits = self.splitter.split_text(page_text)

            for split_text in splits:
                clean_chunk_text = split_text.strip()
                if not clean_chunk_text:
                    continue

                # Deterministic UUID5 based on document_id + chunk_index
                chunk_uuid = str(
                    uuid.uuid5(uuid.NAMESPACE_DNS, f"{doc_id_str}-{global_chunk_idx}")
                )

                chunks.append(
                    DocumentChunk(
                        chunk_id=chunk_uuid,
                        user_id=u_id_str,
                        notebook_id=nb_id_str,
                        document_id=doc_id_str,
                        filename=filename,
                        page_number=page_num,
                        chunk_index=global_chunk_idx,
                        chunk_text=clean_chunk_text,
                        contributing_pages=[page_num],
                    )
                )
                global_chunk_idx += 1

        return chunks

