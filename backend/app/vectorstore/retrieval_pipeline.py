import asyncio
import logging
import math
import re
import time
import uuid
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.vectorstore.embeddings import embedding_service
from app.vectorstore.qdrant_client import qdrant_service

logger = logging.getLogger("app.rag.retrieval_pipeline")

# Standard English stopwords for lexical filtering & BM25
STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but",
    "by", "can", "could", "did", "do", "does", "doing", "down", "during", "each", "few", "for",
    "from", "further", "had", "has", "have", "having", "he", "her", "here", "hers", "herself",
    "him", "himself", "his", "how", "i", "if", "in", "into", "is", "it", "its", "itself", "just",
    "me", "more", "most", "my", "myself", "no", "nor", "not", "now", "of", "off", "on", "once",
    "only", "or", "other", "our", "ours", "ourselves", "out", "over", "own", "same", "she",
    "should", "so", "some", "such", "than", "that", "the", "their", "theirs", "them", "themselves",
    "then", "there", "these", "they", "this", "those", "through", "to", "too", "under", "until",
    "up", "very", "was", "we", "were", "what", "when", "where", "which", "while", "who", "whom",
    "why", "with", "would", "you", "your", "yours", "yourself", "yourselves"
}

BOILERPLATE_PATTERNS = [
    re.compile(r"all rights reserved", re.IGNORECASE),
    re.compile(r"isbn[:\s]+[0-9\-]+", re.IGNORECASE),
    re.compile(r"cataloging-in-publication", re.IGNORECASE),
    re.compile(r"printed in the united states", re.IGNORECASE),
    re.compile(r"o'reilly media", re.IGNORECASE),
    re.compile(r"errata and updates", re.IGNORECASE),
    re.compile(r"neither the author nor the publisher", re.IGNORECASE),
    re.compile(r"table of contents", re.IGNORECASE),
]


@dataclass
class RetrievedPassage:
    chunk_id: str
    document_id: str
    document_name: str
    page_number: int
    text: str
    raw_dense_score: float = 0.0
    bm25_score: float = 0.0
    fused_score: float = 0.0
    rerank_score: float = 0.0
    is_boilerplate: bool = False
    keyword_matches: List[str] = field(default_factory=list)

    @property
    def excerpt(self) -> str:
        cleaned = " ".join(self.text.split())
        return cleaned[:300] + ("..." if len(cleaned) > 300 else "")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.chunk_id,
            "documentId": self.document_id,
            "documentName": self.document_name,
            "pageNumber": self.page_number,
            "excerpt": self.excerpt,
            "relevanceScore": round(float(self.rerank_score or self.fused_score or self.raw_dense_score), 4),
        }


class BM25Okapi:
    """Fast in-memory BM25 index over retrieved candidate chunks."""
    def __init__(self, corpus: List[Dict[str, Any]], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus_size = len(corpus)
        self.doc_lengths = []
        self.doc_tokens = []
        self.df = Counter()

        for item in corpus:
            tokens = self._tokenize(item.get("text", ""))
            self.doc_tokens.append(tokens)
            self.doc_lengths.append(len(tokens))
            unique_tokens = set(tokens)
            for t in unique_tokens:
                self.df[t] += 1

        self.avg_doc_len = (sum(self.doc_lengths) / self.corpus_size) if self.corpus_size > 0 else 1.0

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        words = re.findall(r"\b[a-zA-Z0-9_\-\.]{2,}\b", text.lower())
        return [w for w in words if w not in STOPWORDS]

    def score(self, query_tokens: List[str]) -> List[float]:
        scores = [0.0] * self.corpus_size
        if self.corpus_size == 0 or not query_tokens:
            return scores

        for q in query_tokens:
            df = self.df.get(q, 0)
            if df == 0:
                continue
            # Lucene / Okapi IDF with floor
            idf = math.log(1.0 + (self.corpus_size - df + 0.5) / (df + 0.5))
            if idf <= 0:
                idf = 0.05

            for idx, d_tokens in enumerate(self.doc_tokens):
                tf = d_tokens.count(q)
                if tf == 0:
                    continue
                d_len = self.doc_lengths[idx]
                numerator = tf * (self.k1 + 1.0)
                denominator = tf + self.k1 * (1.0 - self.b + self.b * (d_len / self.avg_doc_len))
                scores[idx] += idf * (numerator / denominator)

        return scores


class RetrievalPipeline:
    def __init__(self, relevance_threshold: float = 0.20):
        self.relevance_threshold = relevance_threshold

    # =========================================================================
    # STAGE 1: QUERY NORMALIZATION
    # =========================================================================
    @staticmethod
    def normalize_query(query: str) -> Tuple[str, List[str]]:
        """
        Normalize query string and extract salient keyword tokens.
        Returns (cleaned_query, keywords).
        """
        cleaned = re.sub(r"[^\w\s\-\.\?]", " ", query).strip()
        cleaned = " ".join(cleaned.split())

        raw_tokens = re.findall(r"\b[a-zA-Z0-9_\-\.]{2,}\b", cleaned.lower())
        keywords = [t for t in raw_tokens if t not in STOPWORDS]
        if not keywords:
            keywords = raw_tokens

        return cleaned, keywords

    # =========================================================================
    # STAGE 2: DENSE VECTOR RETRIEVAL
    # =========================================================================
    @staticmethod
    async def dense_retrieval(
        query: str,
        user_id: uuid.UUID,
        notebook_id: uuid.UUID,
        document_ids: Optional[List[uuid.UUID]] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        query_vector = await embedding_service.get_query_embedding(query)
        raw_hits = await qdrant_service.search(
            query_vector=query_vector,
            user_id=user_id,
            notebook_id=notebook_id,
            document_ids=document_ids,
            limit=limit,
        )
        return raw_hits

    # =========================================================================
    # STAGE 3: BM25 LEXICAL RETRIEVAL
    # =========================================================================
    @staticmethod
    async def bm25_retrieval(
        query_keywords: List[str],
        user_id: uuid.UUID,
        notebook_id: uuid.UUID,
        document_ids: Optional[List[uuid.UUID]] = None,
        limit: int = 20,
    ) -> List[Tuple[Dict[str, Any], float]]:
        """Compute lexical BM25 ranking over all notebook chunks."""
        all_chunks = await qdrant_service.fetch_notebook_chunks(
            user_id=user_id,
            notebook_id=notebook_id,
            document_ids=document_ids,
            limit=2500,
        )
        if not all_chunks:
            return []

        bm25 = BM25Okapi(all_chunks)
        scores = bm25.score(query_keywords)

        scored_chunks = list(zip(all_chunks, scores))
        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        return scored_chunks[:limit]

    # =========================================================================
    # STAGE 4: HYBRID RECIPROCAL RANK FUSION (RRF)
    # =========================================================================
    @staticmethod
    def reciprocal_rank_fusion(
        dense_hits: List[Dict[str, Any]],
        bm25_hits: List[Tuple[Dict[str, Any], float]],
        rrf_k: int = 60,
    ) -> List[Dict[str, Any]]:
        """
        Merge dense and lexical rankings using Reciprocal Rank Fusion.
        RRF_score(d) = sum(1.0 / (rrf_k + rank))
        """
        fused_scores: Dict[str, float] = {}
        chunk_data: Dict[str, Dict[str, Any]] = {}
        dense_score_map: Dict[str, float] = {}
        bm25_score_map: Dict[str, float] = {}

        # 1. Dense ranks
        for rank, hit in enumerate(dense_hits, start=1):
            c_id = hit.get("chunk_id")
            if not c_id:
                continue
            chunk_data[c_id] = hit
            dense_score_map[c_id] = float(hit.get("score", 0.0))
            fused_scores[c_id] = fused_scores.get(c_id, 0.0) + (1.0 / (rrf_k + rank))

        # 2. BM25 ranks
        for rank, (chunk, bm25_sc) in enumerate(bm25_hits, start=1):
            c_id = chunk.get("chunk_id")
            if not c_id:
                continue
            if c_id not in chunk_data:
                chunk_data[c_id] = chunk
            bm25_score_map[c_id] = float(bm25_sc)
            fused_scores[c_id] = fused_scores.get(c_id, 0.0) + (1.0 / (rrf_k + rank))

        # Sort by fused score
        ranked_ids = sorted(fused_scores.keys(), key=lambda cid: fused_scores[cid], reverse=True)

        results = []
        for cid in ranked_ids:
            item = dict(chunk_data[cid])
            item["fused_score"] = fused_scores[cid]
            item["raw_dense_score"] = dense_score_map.get(cid, 0.0)
            item["bm25_score"] = bm25_score_map.get(cid, 0.0)
            results.append(item)

        return results

    # =========================================================================
    # STAGE 5: RERANKING & BOILERPLATE PENALTY
    # =========================================================================
    @staticmethod
    def rerank_and_penalize(
        fused_hits: List[Dict[str, Any]],
        query: str,
        query_keywords: List[str],
        doc_names: Dict[str, str],
    ) -> List[RetrievedPassage]:
        """
        Rerank hits with:
        1. Boilerplate / front-matter penalty (e.g. copyright notices, ISBN disclaimers).
        2. Exact keyword matching boost.
        3. Calibrated relevance score.
        """
        passages: List[RetrievedPassage] = []
        query_lower = query.lower()
        is_metadata_query = any(k in query_lower for k in ["copyright", "isbn", "publisher", "author", "edition", "published"])

        for hit in fused_hits:
            c_id = hit.get("chunk_id", str(uuid.uuid4()))
            d_id = hit.get("document_id", "")
            d_name = doc_names.get(d_id) or hit.get("filename") or "Document"
            page_num = int(hit.get("page_number", 1))
            text = hit.get("text", "")
            raw_dense = hit.get("raw_dense_score", 0.0)
            bm25_sc = hit.get("bm25_score", 0.0)
            fused = hit.get("fused_score", 0.0)

            # Detect boilerplate front matter
            is_bp = False
            if page_num <= 8 and not is_metadata_query:
                for pattern in BOILERPLATE_PATTERNS:
                    if pattern.search(text):
                        is_bp = True
                        break

            # Find matching keywords
            text_lower = text.lower()
            matched_kws = [kw for kw in query_keywords if kw in text_lower]
            keyword_ratio = (len(matched_kws) / len(query_keywords)) if query_keywords else 0.0

            # Calibrate final rerank score:
            # Base = scaled fused score + dense score weight + keyword overlap weight
            score = (fused * 25.0) + (raw_dense * 0.30) + (keyword_ratio * 0.45)

            # Heavy boilerplate discount
            if is_bp:
                score *= 0.15

            passages.append(
                RetrievedPassage(
                    chunk_id=c_id,
                    document_id=d_id,
                    document_name=d_name,
                    page_number=page_num,
                    text=text,
                    raw_dense_score=raw_dense,
                    bm25_score=bm25_sc,
                    fused_score=fused,
                    rerank_score=score,
                    is_boilerplate=is_bp,
                    keyword_matches=matched_kws,
                )
            )

        # Sort descending by rerank score
        passages.sort(key=lambda p: p.rerank_score, reverse=True)
        return passages

    # =========================================================================
    # STAGE 6: CONTEXT RELEVANCE FILTERING
    # =========================================================================
    def filter_relevance(
        self,
        passages: List[RetrievedPassage],
        query_keywords: List[str],
        top_k: int = 5,
    ) -> Tuple[List[RetrievedPassage], bool]:
        """
        Evaluate if retrieved passages contain sufficient relevant evidence.
        Returns: (filtered_passages, has_sufficient_context)
        """
        if not passages:
            return [], False

        # Take top candidates
        top_candidates = passages[:top_k]

        # Check best score and evidence quality
        best_candidate = top_candidates[0]

        # Does the candidate satisfy relevance threshold or keyword match?
        has_keyword_evidence = any(len(p.keyword_matches) > 0 for p in top_candidates)
        passes_threshold = best_candidate.rerank_score >= self.relevance_threshold

        # If best candidate is pure ungrounded boilerplate or no keywords match on a content query
        if not passes_threshold and not has_keyword_evidence:
            return [], False

        # Filter out negative/boilerplate chunks from final prompt context unless user requested metadata
        clean_passages = [p for p in top_candidates if not p.is_boilerplate or p.rerank_score > 0.40]
        if not clean_passages:
            clean_passages = top_candidates[:1]

        has_sufficient = len(clean_passages) > 0 and (passes_threshold or has_keyword_evidence)
        return clean_passages, has_sufficient

    # =========================================================================
    # STAGE 7: CONTEXT CONSTRUCTION
    # =========================================================================
    @staticmethod
    def construct_context(passages: List[RetrievedPassage]) -> str:
        """
        Construct clean, ordered context prompt blocks grouped by document and page.
        """
        # Sort by document name then page number for sequential narrative flow
        sorted_passages = sorted(passages, key=lambda p: (p.document_name, p.page_number))

        blocks = []
        for idx, p in enumerate(sorted_passages, start=1):
            clean_text = "\n".join(line.strip() for line in p.text.splitlines() if line.strip())
            blocks.append(
                f"[Source {idx} - Document: {p.document_name}, Page: {p.page_number}]:\n{clean_text}"
            )
        return "\n\n".join(blocks)

    # =========================================================================
    # FULL RETRIEVAL PIPELINE EXECUTION
    # =========================================================================
    async def execute(
        self,
        db: AsyncSession,
        query: str,
        user_id: uuid.UUID,
        notebook_id: uuid.UUID,
        document_ids: Optional[List[uuid.UUID]] = None,
        top_k: int = 5,
    ) -> Tuple[List[RetrievedPassage], bool, str, Dict[str, Any]]:
        """
        Executes Stages 1 through 7 with detailed telemetry and audit logging.
        Returns: (passages, has_sufficient_context, context_string, audit_log)
        """
        t0 = time.perf_counter()

        # 1. Normalize
        cleaned_query, keywords = self.normalize_query(query)

        # 2 & 3. Parallel retrieval: Dense + BM25
        dense_task = self.dense_retrieval(cleaned_query, user_id, notebook_id, document_ids, limit=20)
        bm25_task = self.bm25_retrieval(keywords, user_id, notebook_id, document_ids, limit=20)
        dense_hits, bm25_hits = await asyncio.gather(dense_task, bm25_task)

        # 4. Hybrid Reciprocal Rank Fusion
        fused_hits = self.reciprocal_rank_fusion(dense_hits, bm25_hits, rrf_k=60)

        # Fetch document filenames from DB
        doc_uuids = set()
        for h in fused_hits:
            did = h.get("document_id")
            if did:
                try:
                    doc_uuids.add(uuid.UUID(str(did)))
                except (ValueError, TypeError):
                    doc_uuids.add(uuid.uuid5(uuid.NAMESPACE_DNS, str(did)))
        doc_names: Dict[str, str] = {}
        if doc_uuids:
            stmt = select(Document.id, Document.filename).where(Document.id.in_(list(doc_uuids)))
            res = await db.execute(stmt)
            doc_names = {str(row.id): row.filename for row in res.all()}

        # 5. Rerank & Penalize Boilerplate
        reranked_passages = self.rerank_and_penalize(fused_hits, query, keywords, doc_names)

        # 6. Filter Relevance & Check Sufficiency
        final_passages, has_sufficient = self.filter_relevance(reranked_passages, keywords, top_k=top_k)

        # 7. Construct Context
        context_str = self.construct_context(final_passages) if has_sufficient else ""

        latency_ms = int((time.perf_counter() - t0) * 1000)

        # TASK 3 Audit Logging
        audit_log = {
            "query": query,
            "normalized_query": cleaned_query,
            "keywords": keywords,
            "embedding_model": embedding_service.model,
            "latency_ms": latency_ms,
            "dense_candidates_count": len(dense_hits),
            "bm25_candidates_count": len(bm25_hits),
            "has_sufficient_context": has_sufficient,
            "retrieved_chunks": [
                {
                    "chunk_id": p.chunk_id,
                    "document_name": p.document_name,
                    "page_number": p.page_number,
                    "dense_score": round(p.raw_dense_score, 4),
                    "bm25_score": round(p.bm25_score, 4),
                    "fused_score": round(p.fused_score, 4),
                    "rerank_score": round(p.rerank_score, 4),
                    "is_boilerplate": p.is_boilerplate,
                    "keyword_matches": p.keyword_matches,
                    "text_preview": p.text[:120].replace("\n", " "),
                }
                for p in final_passages
            ],
        }

        logger.info(
            f"[RAG AUDIT] query='{query[:50]}' | model={embedding_service.model} | "
            f"latency={latency_ms}ms | hits={len(final_passages)} | sufficient={has_sufficient}"
        )

        return final_passages, has_sufficient, context_str, audit_log


retrieval_pipeline = RetrievalPipeline(relevance_threshold=0.20)
