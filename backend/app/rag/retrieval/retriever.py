import asyncio
import logging
import re
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.rag.embeddings.gemini_embeddings import gemini_embeddings
from app.rag.retrieval.context_builder import ContextBuilder
from app.rag.retrieval.hybrid_retriever import BM25Ranker, HybridRetriever, STOPWORDS
from app.rag.retrieval.qdrant_store import qdrant_store
from app.rag.retrieval.reranker import PassageReranker

logger = logging.getLogger("app.rag.retriever")


class ModularRetriever:
    """
    Production modular retrieval pipeline:
    Normalization -> Dense Embeddings -> Qdrant Top-10 -> Lexical BM25 -> RRF Fusion ->
    Reranking -> Relevance Threshold Check -> Context Construction.
    """

    def __init__(
        self,
        top_k: Optional[int] = None,
        score_threshold: Optional[float] = None,
    ):
        self.top_k = top_k or settings.RETRIEVAL_TOP_K
        self.score_threshold = score_threshold if score_threshold is not None else settings.RAG_SCORE_THRESHOLD
        self.embeddings = gemini_embeddings
        self.store = qdrant_store

    @staticmethod
    def normalize_query(query: str) -> Tuple[str, List[str]]:
        cleaned = re.sub(r"[^\w\s\-\.\?]", " ", query).strip()
        cleaned = " ".join(cleaned.split())
        raw_tokens = re.findall(r"\b[a-zA-Z0-9_\-\.]{2,}\b", cleaned.lower())
        keywords = [t for t in raw_tokens if t not in STOPWORDS]
        return cleaned, keywords or raw_tokens

    async def retrieve(
        self,
        query: str,
        user_id: uuid.UUID,
        notebook_id: uuid.UUID,
        document_ids: Optional[List[uuid.UUID]] = None,
        top_k: Optional[int] = None,
    ) -> Tuple[List[Dict[str, Any]], bool, str, Dict[str, Any]]:
        """
        Executes modular retrieval steps 1 through 9.
        Returns:
            (selected_chunks, has_sufficient_evidence, context_text, telemetry)
        """
        t0 = time.perf_counter()
        k = top_k or self.top_k

        # Step 1: Normalize query
        cleaned_query, keywords = self.normalize_query(query)

        # Step 2: Query embedding
        t_embed_0 = time.perf_counter()
        query_vec = await self.embeddings.aembed_query(cleaned_query)
        embed_duration_ms = int((time.perf_counter() - t_embed_0) * 1000)

        # Step 3: Dense retrieval (Top 10 candidates from Qdrant)
        t_dense_0 = time.perf_counter()
        dense_candidates = await self.store.similarity_search(
            query_vector=query_vec,
            user_id=user_id,
            notebook_id=notebook_id,
            document_ids=document_ids,
            limit=10,
        )
        dense_duration_ms = int((time.perf_counter() - t_dense_0) * 1000)

        # Step 4: Lexical BM25 retrieval
        t_bm25_0 = time.perf_counter()
        all_chunks = await self.store.fetch_notebook_chunks(
            user_id=user_id,
            notebook_id=notebook_id,
            document_ids=document_ids,
            limit=2500,
        )
        bm25_hits: List[Tuple[Dict[str, Any], float]] = []
        if all_chunks and keywords:
            bm25 = BM25Ranker(all_chunks)
            scores = bm25.score(keywords)
            scored = list(zip(all_chunks, scores))
            scored.sort(key=lambda x: x[1], reverse=True)
            bm25_hits = scored[:10]
        bm25_duration_ms = int((time.perf_counter() - t_bm25_0) * 1000)

        # Step 5: Reciprocal Rank Fusion (RRF)
        fused = HybridRetriever.reciprocal_rank_fusion(dense_candidates, bm25_hits, rrf_k=60)

        # Step 6: Rerank and Boilerplate Penalization
        reranked = PassageReranker.rerank(fused, query, keywords)

        # Step 7: Select best chunks
        candidates_pool = [c for c in reranked if not c.get("is_boilerplate")]
        if not candidates_pool and reranked:
            candidates_pool = reranked

        selected = candidates_pool[:k]

        # Step 8: Build context window
        context_text = ContextBuilder.build_context(selected)

        # Step 9: Relevance and Evidence Sufficiency Checks
        has_sufficient = False
        if selected:
            best_chunk = selected[0]
            best_score = best_chunk.get("rerank_score", 0.0)
            has_keyword_matches = any(len(c.get("matched_keywords", [])) > 0 for c in selected)
            if best_score >= self.score_threshold or has_keyword_matches:
                has_sufficient = True

        total_duration_ms = int((time.perf_counter() - t0) * 1000)

        telemetry = {
            "query": query,
            "normalized_query": cleaned_query,
            "keywords": keywords,
            "dense_count": len(dense_candidates),
            "bm25_count": len(bm25_hits),
            "selected_count": len(selected),
            "has_sufficient_evidence": has_sufficient,
            "latencies": {
                "embedding_ms": embed_duration_ms,
                "dense_retrieval_ms": dense_duration_ms,
                "bm25_retrieval_ms": bm25_duration_ms,
                "total_retrieval_ms": total_duration_ms,
            },
        }

        logger.info(
            f"[RETRIEVAL] query='{query[:40]}' | total={total_duration_ms}ms | "
            f"selected={len(selected)} | sufficient={has_sufficient}"
        )

        return selected, has_sufficient, context_text, telemetry


modular_retriever = ModularRetriever()

