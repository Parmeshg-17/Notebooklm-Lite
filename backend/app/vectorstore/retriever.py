import logging
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.vectorstore.retrieval_pipeline import (
    RetrievedPassage,
    retrieval_pipeline,
)

logger = logging.getLogger("app.vectorstore.retriever")


class RetrievedChunk:
    def __init__(
        self,
        document_id: str,
        document_name: str,
        page_number: int,
        chunk_id: str,
        excerpt: str,
        score: float,
        text: str = "",
        is_boilerplate: bool = False,
    ):
        self.document_id = document_id
        self.document_name = document_name
        self.page_number = page_number
        self.chunk_id = chunk_id
        self.excerpt = excerpt
        self.score = score
        self.text = text or excerpt
        self.is_boilerplate = is_boilerplate

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.chunk_id,
            "documentId": self.document_id,
            "documentName": self.document_name,
            "pageNumber": self.page_number,
            "excerpt": self.excerpt,
            "relevanceScore": round(float(self.score), 4),
        }


class VectorRetriever:
    @staticmethod
    async def retrieve(
        db: AsyncSession,
        query: str,
        user_id: uuid.UUID,
        notebook_id: uuid.UUID,
        document_ids: Optional[List[uuid.UUID]] = None,
        limit: int = 5,
        score_threshold: Optional[float] = None,
    ) -> List[RetrievedChunk]:
        """
        Executes the 7-stage retrieval pipeline with BM25 lexical fusion, boilerplate penalty,
        and relevance filtering.
        """
        passages, has_sufficient, _, _ = await retrieval_pipeline.execute(
            db=db,
            query=query,
            user_id=user_id,
            notebook_id=notebook_id,
            document_ids=document_ids,
            top_k=limit,
        )

        return [
            RetrievedChunk(
                document_id=p.document_id,
                document_name=p.document_name,
                page_number=p.page_number,
                chunk_id=p.chunk_id,
                excerpt=p.excerpt,
                score=p.rerank_score or p.fused_score or p.raw_dense_score,
                text=p.text,
                is_boilerplate=p.is_boilerplate,
            )
            for p in passages
        ]
