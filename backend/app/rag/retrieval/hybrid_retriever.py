import math
import re
from collections import Counter
from typing import Any, Dict, List, Tuple

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


class BM25Ranker:
    """Fast Okapi BM25 implementation for lexical candidate scoring."""
    def __init__(self, corpus: List[Dict[str, Any]], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus = corpus
        self.corpus_size = len(corpus)
        self.doc_lengths = []
        self.doc_tokens = []
        self.df = Counter()

        for item in corpus:
            text = item.get("chunk_text") or item.get("text", "")
            tokens = self._tokenize(text)
            self.doc_tokens.append(tokens)
            self.doc_lengths.append(len(tokens))
            for t in set(tokens):
                self.df[t] += 1

        self.avg_doc_len = (sum(self.doc_lengths) / self.corpus_size) if self.corpus_size > 0 else 1.0

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        words = re.findall(r"\b[a-zA-Z0-9_\-\.]{2,}\b", text.lower())
        return [w for w in words if w not in STOPWORDS]

    def score(self, query_keywords: List[str]) -> List[float]:
        scores = [0.0] * self.corpus_size
        if self.corpus_size == 0 or not query_keywords:
            return scores

        for q in query_keywords:
            q_clean = q.lower()
            df = self.df.get(q_clean, 0)
            if df == 0:
                continue

            idf = math.log(1.0 + (self.corpus_size - df + 0.5) / (df + 0.5))
            if idf <= 0:
                idf = 0.05

            for idx, d_tokens in enumerate(self.doc_tokens):
                tf = d_tokens.count(q_clean)
                if tf == 0:
                    continue
                d_len = self.doc_lengths[idx]
                numerator = tf * (self.k1 + 1.0)
                denominator = tf + self.k1 * (1.0 - self.b + self.b * (d_len / self.avg_doc_len))
                scores[idx] += idf * (numerator / denominator)

        return scores


class HybridRetriever:
    """Fuses dense vector results with lexical BM25 results using Reciprocal Rank Fusion (RRF)."""

    @staticmethod
    def reciprocal_rank_fusion(
        dense_hits: List[Dict[str, Any]],
        bm25_hits: List[Tuple[Dict[str, Any], float]],
        rrf_k: int = 60,
    ) -> List[Dict[str, Any]]:
        fused_scores: Dict[str, float] = {}
        chunk_map: Dict[str, Dict[str, Any]] = {}
        dense_score_map: Dict[str, float] = {}
        bm25_score_map: Dict[str, float] = {}

        # 1. Dense ranks
        for rank, hit in enumerate(dense_hits, start=1):
            c_id = hit.get("chunk_id")
            if not c_id:
                continue
            chunk_map[c_id] = hit
            dense_score_map[c_id] = float(hit.get("score", 0.0))
            fused_scores[c_id] = fused_scores.get(c_id, 0.0) + (1.0 / (rrf_k + rank))

        # 2. BM25 ranks
        for rank, (chunk, sc) in enumerate(bm25_hits, start=1):
            c_id = chunk.get("chunk_id")
            if not c_id:
                continue
            if c_id not in chunk_map:
                chunk_map[c_id] = chunk
            bm25_score_map[c_id] = float(sc)
            fused_scores[c_id] = fused_scores.get(c_id, 0.0) + (1.0 / (rrf_k + rank))

        ranked_ids = sorted(fused_scores.keys(), key=lambda cid: fused_scores[cid], reverse=True)

        results = []
        for cid in ranked_ids:
            item = dict(chunk_map[cid])
            item["fused_score"] = fused_scores[cid]
            item["raw_dense_score"] = dense_score_map.get(cid, 0.0)
            item["bm25_score"] = bm25_score_map.get(cid, 0.0)
            results.append(item)

        return results

