import logging
import os
import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.models.document import Document
from app.rag.embeddings.gemini_embeddings import gemini_embeddings
from app.rag.ingestion.document_loader import DocumentLoader
from app.rag.ingestion.text_splitter import DocumentSplitter
from app.rag.retrieval.qdrant_store import qdrant_store
from app.services.storage_service import StorageService

logger = logging.getLogger("app.rag.ingestion_pipeline")


class IngestionPipeline:
    """
    Production end-to-end document ingestion pipeline.
    Manages document extraction, cleaning, chunking, embedding generation,
    vector storage in Qdrant, count verification, and lifecycle state transitions.
    """

    def __init__(self):
        self.splitter = DocumentSplitter()
        self.embeddings = gemini_embeddings
        self.store = qdrant_store

    async def _update_status(
        self,
        db: AsyncSession,
        doc_id: uuid.UUID,
        status: str,
        error: Optional[str] = None,
        page_count: Optional[int] = None,
        total_chunks: Optional[int] = None,
    ) -> None:
        stmt = select(Document).where(Document.id == doc_id)
        res = await db.execute(stmt)
        doc = res.scalar_one_or_none()
        if doc:
            doc.processing_status = status
            if error is not None:
                doc.processing_error = error
            if page_count is not None:
                doc.page_count = page_count
            if total_chunks is not None:
                doc.total_chunks = total_chunks
            await db.commit()

    async def process_document(self, document_id: uuid.UUID) -> None:
        """
        Background task to process and index an uploaded document.
        """
        async with async_session_factory() as db:
            # 1. Fetch document record
            stmt = select(Document).where(Document.id == document_id)
            res = await db.execute(stmt)
            doc = res.scalar_one_or_none()

            if not doc:
                logger.error(f"Document {document_id} not found in database for ingestion")
                return

            try:
                # Stage: EXTRACTING
                await self._update_status(db, doc.id, "EXTRACTING")
                logger.info(f"Extracting document {doc.id} ({doc.filename}) from {doc.storage_path}")
                local_path, is_temp = StorageService.resolve_to_local_path(doc.storage_path)
                try:
                    pages, total_pages = DocumentLoader.load(local_path)
                finally:
                    if is_temp and os.path.exists(local_path):
                        os.unlink(local_path)

                if not pages or total_pages == 0:
                    raise ValueError("Document contains no readable text or empty pages")

                # Stage: CHUNKING
                await self._update_status(db, doc.id, "CHUNKING", page_count=total_pages)
                logger.info(f"Chunking document {doc.id} ({total_pages} pages)")
                chunks = self.splitter.split_pages(
                    pages=pages,
                    document_id=doc.id,
                    notebook_id=doc.notebook_id,
                    user_id=doc.owner_id,
                    filename=doc.filename,
                )

                if not chunks:
                    raise ValueError("Chunking produced 0 chunks")

                # Stage: EMBEDDING
                await self._update_status(db, doc.id, "EMBEDDING", total_chunks=len(chunks))
                logger.info(f"Generating embeddings for {len(chunks)} chunks of document {doc.id}")
                chunk_texts = [c.chunk_text for c in chunks]
                embeddings = await self.embeddings.aembed_documents(chunk_texts)

                # Stage: INDEXING
                await self._update_status(db, doc.id, "INDEXING")
                logger.info(f"Inserting {len(chunks)} vectors into Qdrant for document {doc.id}")
                inserted_count = await self.store.upsert_chunks(chunks, embeddings)

                # Verify stored chunk count in Qdrant
                verified_count = await self.store.count_document_chunks(doc.id)
                logger.info(f"Verified {verified_count}/{len(chunks)} chunks in Qdrant for document {doc.id}")

                if verified_count == 0 and len(chunks) > 0:
                    raise RuntimeError("Vector database verification failed: 0 points stored")

                # Stage: INDEXED
                await self._update_status(
                    db,
                    doc.id,
                    "INDEXED",
                    error=None,
                    page_count=total_pages,
                    total_chunks=verified_count or len(chunks),
                )
                logger.info(f"Document {doc.id} successfully indexed!")

            except Exception as e:
                err_str = str(e)
                logger.error(f"Ingestion failed for document {doc.id}: {err_str}", exc_info=True)
                await self._update_status(db, doc.id, "FAILED", error=err_str)


ingestion_pipeline = IngestionPipeline()

