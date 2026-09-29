"""
Hybrid Retrieval Engine for NotebookLM Lite.
Implements:
1. Vector Similarity Search via pgvector (HNSW index)
2. Keyword Search via PostgreSQL tsvector / plainto_tsquery (GIN index)
3. Reciprocal Rank Fusion (RRF) to merge rankings
4. Source candidate filtering strictly bound to notebook_id
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.rag.embeddings import get_embedding_provider

logger = get_logger(__name__)
settings = get_settings()


@dataclass
class RetrievedChunk:
    chunk_id: UUID
    document_id: UUID
    filename: str
    page_start: int
    page_end: int
    text: str
    score: float
    source_id: int = 0  # Assigned 1..N when passed to LLM


class HybridRetriever:
    """Combines vector search and full-text keyword search using Reciprocal Rank Fusion (RRF)."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.embedder = get_embedding_provider()
        self.rrf_k = 60  # Standard RRF constant

    async def retrieve(
        self,
        notebook_id: UUID,
        query: str,
        top_k: int = 5,
        vector_candidates: int = 20,
        keyword_candidates: int = 20,
    ) -> List[RetrievedChunk]:
        """
        Executes hybrid retrieval strictly filtered to the given notebook_id:
        1. Runs vector search on pgvector
        2. Runs full-text keyword search on tsvector
        3. Applies Reciprocal Rank Fusion
        4. Returns top_k highest ranked chunks with sequential source_ids (1, 2, ...)
        """
        if not query.strip():
            return []

        # 1. Vector Search
        query_vector = self.embedder.embed_query(query)
        vector_results = await self._vector_search(notebook_id, query_vector, limit=vector_candidates)

        # 2. Keyword Search
        keyword_results = await self._keyword_search(notebook_id, query, limit=keyword_candidates)

        # 3. Reciprocal Rank Fusion (RRF)
        # RRF score = sum( 1 / (k + rank) )
        chunk_map: Dict[UUID, RetrievedChunk] = {}
        rrf_scores: Dict[UUID, float] = {}

        for rank, chunk in enumerate(vector_results, start=1):
            chunk_map[chunk.chunk_id] = chunk
            rrf_scores[chunk.chunk_id] = rrf_scores.get(chunk.chunk_id, 0.0) + (1.0 / (self.rrf_k + rank))

        for rank, chunk in enumerate(keyword_results, start=1):
            if chunk.chunk_id not in chunk_map:
                chunk_map[chunk.chunk_id] = chunk
            rrf_scores[chunk.chunk_id] = rrf_scores.get(chunk.chunk_id, 0.0) + (1.0 / (self.rrf_k + rank))

        # Sort by final RRF score descending
        sorted_chunk_ids = sorted(rrf_scores.keys(), key=lambda cid: rrf_scores[cid], reverse=True)

        final_chunks: List[RetrievedChunk] = []
        for idx, cid in enumerate(sorted_chunk_ids[:top_k], start=1):
            chunk = chunk_map[cid]
            chunk.score = rrf_scores[cid]
            chunk.source_id = idx
            final_chunks.append(chunk)

        logger.info(
            "Retrieved chunks via hybrid search",
            notebook_id=str(notebook_id),
            query=query,
            vector_count=len(vector_results),
            keyword_count=len(keyword_results),
            final_count=len(final_chunks),
        )
        return final_chunks

    async def _vector_search(
        self,
        notebook_id: UUID,
        query_vector: List[float],
        limit: int = 20,
    ) -> List[RetrievedChunk]:
        """Perform cosine distance vector search using pgvector."""
        # Convert vector to Postgres vector literal string
        vec_literal = "[" + ",".join(str(f) for f in query_vector) + "]"

        stmt = text("""
            SELECT 
                c.id AS chunk_id,
                c.document_id,
                d.filename,
                c.page_start,
                c.page_end,
                c.text,
                (1 - (e.embedding <=> CAST(:query_vector AS vector))) AS score
            FROM chunks c
            JOIN embeddings e ON e.chunk_id = c.id
            JOIN documents d ON d.id = c.document_id
            WHERE d.notebook_id = :notebook_id
              AND d.status = 'indexed'
            ORDER BY e.embedding <=> CAST(:query_vector AS vector)
            LIMIT :limit;
        """)

        result = await self.db.execute(
            stmt,
            {
                "notebook_id": str(notebook_id),
                "query_vector": vec_literal,
                "limit": limit,
            },
        )
        rows = result.mappings().all()

        return [
            RetrievedChunk(
                chunk_id=r["chunk_id"],
                document_id=r["document_id"],
                filename=r["filename"],
                page_start=r["page_start"],
                page_end=r["page_end"],
                text=r["text"],
                score=float(r["score"]) if r["score"] is not None else 0.0,
            )
            for r in rows
        ]

    async def _keyword_search(
        self,
        notebook_id: UUID,
        query: str,
        limit: int = 20,
    ) -> List[RetrievedChunk]:
        """Perform full-text keyword search using tsvector and plainto_tsquery."""
        stmt = text("""
            SELECT 
                c.id AS chunk_id,
                c.document_id,
                d.filename,
                c.page_start,
                c.page_end,
                c.text,
                ts_rank_cd(c.tsv, plainto_tsquery('english', :query)) AS score
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE d.notebook_id = :notebook_id
              AND d.status = 'indexed'
              AND c.tsv @@ plainto_tsquery('english', :query)
            ORDER BY score DESC
            LIMIT :limit;
        """)

        result = await self.db.execute(
            stmt,
            {
                "notebook_id": str(notebook_id),
                "query": query,
                "limit": limit,
            },
        )
        rows = result.mappings().all()

        return [
            RetrievedChunk(
                chunk_id=r["chunk_id"],
                document_id=r["document_id"],
                filename=r["filename"],
                page_start=r["page_start"],
                page_end=r["page_end"],
                text=r["text"],
                score=float(r["score"]) if r["score"] is not None else 0.0,
            )
            for r in rows
        ]
