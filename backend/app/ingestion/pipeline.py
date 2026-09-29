"""
Full Document Ingestion Pipeline.
Executes: Parse (page-by-page) -> Chunk (page-preserving) -> Embed -> Store (Postgres + pgvector) -> Index.
"""

from typing import Any, Dict
import uuid

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.ingestion.chunker import PagePreservingChunker
from app.ingestion.parser import DocumentParser
from app.models.models import Chunk, Document, Embedding
from app.rag.embeddings import get_embedding_provider
from app.services.storage import get_storage_service

logger = get_logger(__name__)
settings = get_settings()


def run_ingestion(document_id: str) -> Dict[str, Any]:
    """
    Complete document ingestion pipeline:
    1. Reads document record and marks as 'parsing'
    2. Downloads original file bytes from storage
    3. Parses document page-by-page
    4. Chunks text while strictly preserving page_start and page_end
    5. Computes vector embeddings in batches
    6. Saves chunks and embeddings to database
    7. Updates status to 'indexed'
    """
    engine = create_engine(settings.database_url_sync)
    storage = get_storage_service()
    parser = DocumentParser()
    chunker = PagePreservingChunker()
    embedder = get_embedding_provider()

    with Session(engine) as session:
        doc = session.execute(
            select(Document).where(Document.id == document_id)
        ).scalar_one_or_none()

        if doc is None:
            raise ValueError(f"Document {document_id} not found in database")

        logger.info(
            "Starting ingestion pipeline",
            document_id=document_id,
            filename=doc.filename,
            notebook_id=str(doc.notebook_id),
        )

        try:
            # 1. Update status to 'parsing'
            doc.status = "parsing"
            session.commit()

            # 2. Download from storage
            file_bytes = storage.download_file(doc.storage_key)
            logger.info("Downloaded file from storage", size_bytes=len(file_bytes))

            # 3. Parse page-by-page
            parsed_doc = parser.parse_bytes(file_bytes, doc.filename)
            doc.page_count = parsed_doc.page_count
            session.commit()
            logger.info("Document parsed", pages=parsed_doc.page_count)

            # 4. Chunk with page preservation
            chunks_data = chunker.chunk_pages(parsed_doc.pages)
            logger.info("Generated chunks", count=len(chunks_data))

            if not chunks_data:
                # If document was empty or whitespace only
                doc.status = "indexed"
                session.commit()
                return {"document_id": document_id, "status": "indexed", "chunks": 0}

            # 5. Clean up any previous chunks for this document (if re-ingesting)
            existing_chunks = session.execute(
                select(Chunk).where(Chunk.document_id == doc.id)
            ).scalars().all()
            for ec in existing_chunks:
                session.delete(ec)
            session.flush()

            # 6. Generate embeddings
            chunk_texts = [c.text for c in chunks_data]
            embeddings_list = embedder.embed_texts(chunk_texts)

            # 7. Insert Chunks & Embeddings
            for c_data, emb_vector in zip(chunks_data, embeddings_list):
                chunk_id = uuid.uuid4()
                chunk_obj = Chunk(
                    id=chunk_id,
                    document_id=doc.id,
                    chunk_index=c_data.chunk_index,
                    page_start=c_data.page_start,
                    page_end=c_data.page_end,
                    text=c_data.text,
                )
                session.add(chunk_obj)
                session.flush()  # Flush to ensure chunk_id exists for foreign key

                embedding_obj = Embedding(
                    chunk_id=chunk_id,
                    model=settings.embedding_model,
                    embedding=emb_vector,
                )
                session.add(embedding_obj)

            # 8. Mark as indexed
            doc.status = "indexed"
            doc.error_msg = None
            session.commit()

            logger.info(
                "Ingestion completed successfully",
                document_id=document_id,
                chunks_indexed=len(chunks_data),
            )
            return {
                "document_id": document_id,
                "status": "indexed",
                "chunks": len(chunks_data),
                "pages": doc.page_count,
            }

        except Exception as e:
            logger.error(
                "Document ingestion failed",
                document_id=document_id,
                error=str(e),
                exc_info=True,
            )
            session.rollback()
            try:
                # Update status to failed
                failed_doc = session.execute(
                    select(Document).where(Document.id == document_id)
                ).scalar_one_or_none()
                if failed_doc:
                    failed_doc.status = "failed"
                    failed_doc.error_msg = str(e)
                    session.commit()
            except Exception as inner_e:
                logger.error("Failed to mark document status as failed", error=str(inner_e))

            raise e
