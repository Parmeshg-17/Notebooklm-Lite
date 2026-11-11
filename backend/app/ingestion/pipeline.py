import asyncio
import logging
import os
import uuid
from sqlalchemy import select
from app.db.session import async_session_maker
from app.ingestion.chunker import Chunker
from app.ingestion.pdf_parser import PDFParser
from app.models.document import Document
from app.services.storage_service import StorageService
from app.vectorstore.embeddings import embedding_service
from app.vectorstore.qdrant_client import qdrant_service

logger = logging.getLogger("app.ingestion.pipeline")

# Concurrency semaphore to bound simultaneous PDF extractions on ECS Fargate
_INGESTION_SEMAPHORE = asyncio.Semaphore(5)


class IngestionPipeline:
    @staticmethod
    async def process_document(document_id: uuid.UUID) -> None:
        """
        Background worker task to extract, chunk, embed, and index a document.
        Guarantees bounded concurrency and cleans up temporary S3 files.
        """
        async with _INGESTION_SEMAPHORE:
            async with async_session_maker() as db:
                stmt = select(Document).where(Document.id == document_id)
                res = await db.execute(stmt)
                doc = res.scalar_one_or_none()

                if not doc:
                    logger.error(f"Ingestion failed: document {document_id} not found in database")
                    return

                local_path = None
                is_temporary = False

                try:
                    # 1. Update status to EXTRACTING
                    doc.processing_status = "EXTRACTING"
                    await db.commit()
                    await db.refresh(doc)
                    logger.info(f"Extracting document {document_id} ({doc.filename})...")

                    # Resolve storage path (handles local filesystem or S3 download to tempfile)
                    local_path, is_temporary = await asyncio.to_thread(
                        StorageService.resolve_to_local_path, doc.storage_path
                    )

                    # 2. Extract pages from file in worker thread
                    pages, page_count = await asyncio.to_thread(PDFParser.extract_pages, local_path)
                    doc.page_count = page_count

                    # 3. Update status to CHUNKING
                    doc.processing_status = "CHUNKING"
                    await db.commit()
                    await db.refresh(doc)
                    logger.info(f"Chunking document {document_id} ({page_count} pages)...")

                    chunker = Chunker(chunk_size=1000, chunk_overlap=150)
                    chunks = await asyncio.to_thread(
                        chunker.chunk_document,
                        pages=pages,
                        document_id=doc.id,
                        notebook_id=doc.notebook_id,
                        owner_id=doc.owner_id,
                        filename=doc.filename,
                    )
                    doc.total_chunks = len(chunks)

                    if chunks:
                        # 4. Update status to EMBEDDING
                        doc.processing_status = "EMBEDDING"
                        await db.commit()
                        await db.refresh(doc)
                        logger.info(f"Embedding {len(chunks)} chunks for document {document_id}...")

                        chunk_texts = [c.text for c in chunks]
                        embeddings = await embedding_service.get_embeddings(chunk_texts)

                        # 5. Update status to INDEXING
                        doc.processing_status = "INDEXING"
                        await db.commit()
                        await db.refresh(doc)
                        logger.info(f"Indexing vectors for document {document_id}...")

                        chunk_dicts = [c.to_dict() for c in chunks]
                        await qdrant_service.upsert_chunks(chunk_dicts, embeddings)

                        # Verification: Ensure chunks were written into Qdrant before declaring INDEXED
                        stored_count = await qdrant_service.count_document_chunks(doc.id)
                        logger.info(f"Verified stored chunks for {document_id}: {stored_count}/{len(chunks)}")
                        if stored_count < len(chunks):
                            logger.warning(f"Chunk count mismatch for {document_id}: expected {len(chunks)}, found {stored_count}")

                    # 6. Mark as INDEXED
                    doc.processing_status = "INDEXED"
                    doc.processing_error = None
                    await db.commit()
                    logger.info(f"Successfully indexed document {document_id}: {page_count} pages, {len(chunks)} chunks")

                except Exception as e:
                    logger.exception(f"Error processing document {document_id}: {e}")
                    doc.processing_status = "FAILED"
                    doc.processing_error = str(e)
                    await db.commit()

                finally:
                    # Clean up temporary download file if fetched from S3
                    if is_temporary and local_path and os.path.exists(local_path):
                        try:
                            os.remove(local_path)
                            logger.debug(f"[S3] Cleaned up temporary ingestion file: {local_path}")
                        except OSError as clean_err:
                            logger.warning(f"Failed to remove temp file {local_path}: {clean_err}")

