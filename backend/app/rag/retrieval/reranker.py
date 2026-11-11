import re
from typing import Any, Dict, List, Set

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


class PassageReranker:
    """
    Reranks candidate chunks using exact keyword coverage and down-weights
    front-matter publisher boilerplate unless explicitly requested.
    """

    @staticmethod
    def is_boilerplate(text: str, page_number: int) -> bool:
        if page_number > 8:
            return False
        for pattern in BOILERPLATE_PATTERNS:
            if pattern.search(text):
                return True
        return False

    @classmethod
    def rerank(
        cls,
        candidates: List[Dict[str, Any]],
        query: str,
        query_keywords: List[str],
    ) -> List[Dict[str, Any]]:
        query_lower = query.lower()
        is_metadata_query = any(
            k in query_lower
            for k in ["copyright", "isbn", "publisher", "author", "edition", "published", "errata"]
        )

        reranked = []
        kw_set = set(k.lower() for k in query_keywords if len(k) > 1)

        for item in candidates:
            chunk = dict(item)
            text = chunk.get("chunk_text") or chunk.get("text", "")
            page_num = int(chunk.get("page_number", 1))
            dense_score = float(chunk.get("score", 0.0) or chunk.get("raw_dense_score", 0.0))
            fused_score = float(chunk.get("fused_score", 0.0))
            bm25_score = float(chunk.get("bm25_score", 0.0))

            text_words = set(re.findall(r"\b[a-zA-Z0-9_\-\.]{2,}\b", text.lower()))
            matched_kws = list(kw_set.intersection(text_words))
            overlap_ratio = (len(matched_kws) / len(kw_set)) if kw_set else 0.0

            is_bp = cls.is_boilerplate(text, page_num) and not is_metadata_query

            # Composite calibrated relevance score
            composite = (fused_score * 25.0) + (dense_score * 0.30) + (overlap_ratio * 0.45)
            if is_bp:
                composite *= 0.15

            chunk["rerank_score"] = composite
            chunk["is_boilerplate"] = is_bp
            chunk["matched_keywords"] = matched_kws
            reranked.append(chunk)

        reranked.sort(key=lambda x: x["rerank_score"], reverse=True)
        return reranked

