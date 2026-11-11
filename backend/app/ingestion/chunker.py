import uuid
from typing import Any, Dict, List
from app.ingestion.text_cleaner import TextCleaner


class DocumentChunk:
    def __init__(
        self,
        chunk_id: str,
        document_id: uuid.UUID,
        notebook_id: uuid.UUID,
        owner_id: uuid.UUID,
        page_number: int,
        chunk_index: int,
        text: str,
        filename: str = "",
    ):
        self.chunk_id = chunk_id
        self.document_id = document_id
        self.notebook_id = notebook_id
        self.owner_id = owner_id
        self.filename = filename
        self.page_number = page_number
        self.chunk_index = chunk_index
        self.text = text

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "document_id": str(self.document_id),
            "notebook_id": str(self.notebook_id),
            "owner_id": str(self.owner_id),
            "filename": self.filename,
            "page_number": self.page_number,
            "chunk_index": self.chunk_index,
            "text": self.text,
        }


class Chunker:
    def __init__(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 120,
        min_chunk_length: int = 40,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_length = min_chunk_length

    def chunk_document(
        self,
        pages: List[Dict[str, int | str]],
        document_id: uuid.UUID,
        notebook_id: uuid.UUID,
        owner_id: uuid.UUID,
        filename: str = "",
    ) -> List[DocumentChunk]:
        """
        Split document pages into overlapping chunks preserving page numbers.
        """
        chunks: List[DocumentChunk] = []
        global_chunk_idx = 0

        for page in pages:
            page_num = int(page["page_number"])
            raw_text = str(page.get("text", ""))
            cleaned_text = TextCleaner.clean(raw_text)

            if not cleaned_text:
                continue

            # If page text fits in one chunk, create single chunk
            if len(cleaned_text) <= self.chunk_size:
                if len(cleaned_text) >= self.min_chunk_length:
                    chunk_id = f"{document_id}_{page_num}_{global_chunk_idx}"
                    chunks.append(
                        DocumentChunk(
                            chunk_id=chunk_id,
                            document_id=document_id,
                            notebook_id=notebook_id,
                            owner_id=owner_id,
                            filename=filename,
                            page_number=page_num,
                            chunk_index=global_chunk_idx,
                            text=cleaned_text,
                        )
                    )
                    global_chunk_idx += 1
                continue

            # Overlapping window chunking
            start = 0
            while start < len(cleaned_text):
                end = start + self.chunk_size
                chunk_slice = cleaned_text[start:end]

                # Try to break on paragraph or sentence boundary if feasible
                if end < len(cleaned_text):
                    last_break = max(
                        chunk_slice.rfind("\n\n"),
                        chunk_slice.rfind(". "),
                        chunk_slice.rfind("? "),
                        chunk_slice.rfind("! "),
                    )
                    if last_break > self.chunk_size // 2:
                        chunk_slice = chunk_slice[: last_break + 1]
                        end = start + len(chunk_slice)

                chunk_text = chunk_slice.strip()
                if len(chunk_text) >= self.min_chunk_length:
                    chunk_id = f"{document_id}_{page_num}_{global_chunk_idx}"
                    chunks.append(
                        DocumentChunk(
                            chunk_id=chunk_id,
                            document_id=document_id,
                            notebook_id=notebook_id,
                            owner_id=owner_id,
                            filename=filename,
                            page_number=page_num,
                            chunk_index=global_chunk_idx,
                            text=chunk_text,
                        )
                    )
                    global_chunk_idx += 1

                if end >= len(cleaned_text) or (start + len(chunk_slice) >= len(cleaned_text)):
                    break

                step = len(chunk_slice) - self.chunk_overlap
                if step <= 0:
                    step = len(chunk_slice)
                start += step

        return chunks

