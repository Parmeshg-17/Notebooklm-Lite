import pytest
import uuid
from app.rag.retrieval.context_builder import ContextBuilder
from app.rag.retrieval.hybrid_retriever import BM25Ranker, HybridRetriever
from app.rag.retrieval.reranker import PassageReranker
from app.rag.retrieval.retriever import ModularRetriever


def test_query_normalization():
    cleaned, kws = ModularRetriever.normalize_query("What are the KEY findings in this document??")
    assert "key" in kws
    assert "findings" in kws
    assert "what" not in kws


def test_bm25_scoring():
    corpus = [
        {"chunk_id": "c1", "text": "Speculative decoding accelerates LLM generation with draft models."},
        {"chunk_id": "c2", "text": "Cooking Italian lasagna with bechamel sauce and beef ragu."},
    ]
    bm25 = BM25Ranker(corpus)
    scores = bm25.score(["speculative", "decoding"])
    assert scores[0] > scores[1]
    assert scores[1] == 0.0


def test_boilerplate_reranking():
    candidates = [
        {
            "chunk_id": "bp",
            "page_number": 6,
            "text": "All rights reserved. ISBN 978-1-098-16630-4. Neither the author nor publisher...",
            "score": 0.40,
            "fused_score": 0.02,
        },
        {
            "chunk_id": "substantive",
            "page_number": 45,
            "text": "Key findings demonstrate that speculative decoding reduces token latency by 2.2x.",
            "score": 0.35,
            "fused_score": 0.02,
        },
    ]
    reranked = PassageReranker.rerank(candidates, "What are the key findings?", ["key", "findings"])
    assert reranked[0]["chunk_id"] == "substantive"
    assert reranked[1]["is_boilerplate"] is True


def test_context_builder():
    passages = [
        {"filename": "PaperB.pdf", "page_number": 12, "chunk_text": "Text from Paper B page 12"},
        {"filename": "PaperA.pdf", "page_number": 3, "chunk_text": "Text from Paper A page 3"},
        {"filename": "PaperA.pdf", "page_number": 1, "chunk_text": "Text from Paper A page 1"},
    ]
    ctx = ContextBuilder.build_context(passages)
    assert "[Source 1 - Document: PaperA.pdf, Page: 1" in ctx
    assert "[Source 2 - Document: PaperA.pdf, Page: 3" in ctx
    assert "[Source 3 - Document: PaperB.pdf, Page: 12" in ctx

