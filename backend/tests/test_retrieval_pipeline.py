import pytest
import uuid
from app.vectorstore.retrieval_pipeline import (
    BM25Okapi,
    RetrievalPipeline,
    RetrievedPassage,
    BOILERPLATE_PATTERNS,
)
from app.services.chat_service import ChatService, REFUSAL_MESSAGE


def test_query_normalization():
    query = "What are the KEY findings in this document??!"
    cleaned, keywords = RetrievalPipeline.normalize_query(query)
    assert "key" in keywords
    assert "findings" in keywords
    assert "document" in keywords
    # Stopwords like "what", "are", "the", "in", "this" should be filtered
    assert "what" not in keywords
    assert "the" not in keywords


def test_bm25_lexical_scoring():
    corpus = [
        {"chunk_id": "c1", "text": "FlashAttention-3 utilizes TMA and WGMMA instructions on H100 GPUs."},
        {"chunk_id": "c2", "text": "AlexNet popularized convolutional neural networks on ImageNet in 2012."},
        {"chunk_id": "c3", "text": "Cooking Italian pizza with sourdough crust and mozzarella."},
    ]
    bm25 = BM25Okapi(corpus)
    scores = bm25.score(["flashattention-3", "tma", "h100"])
    assert scores[0] > scores[1]
    assert scores[0] > scores[2]
    assert scores[2] == 0.0


def test_reciprocal_rank_fusion():
    dense_hits = [
        {"chunk_id": "c1", "score": 0.85},
        {"chunk_id": "c2", "score": 0.80},
    ]
    bm25_hits = [
        ({"chunk_id": "c2", "text": "Chunk 2"}, 5.2),
        ({"chunk_id": "c1", "text": "Chunk 1"}, 2.1),
    ]
    fused = RetrievalPipeline.reciprocal_rank_fusion(dense_hits, bm25_hits, rrf_k=60)
    assert len(fused) == 2
    # Both c1 and c2 should have fused scores
    assert fused[0]["fused_score"] > 0
    assert fused[1]["fused_score"] > 0


def test_boilerplate_penalty():
    query = "What are the key findings in this document?"
    _, keywords = RetrievalPipeline.normalize_query(query)

    fused_hits = [
        {
            "chunk_id": "c_bp",
            "document_id": "d1",
            "filename": "AI Engineering.pdf",
            "page_number": 6,
            "text": "All rights reserved. ISBN 978-1-098-16630-4. Neither the author nor the publisher shall be liable for findings in this document.",
            "raw_dense_score": 0.38,
            "bm25_score": 1.0,
            "fused_score": 0.03,
        },
        {
            "chunk_id": "c_substantive",
            "document_id": "d1",
            "filename": "AI Engineering.pdf",
            "page_number": 45,
            "text": "The key findings show that speculative decoding yields a 2.5x latency improvement across standard transformer workloads.",
            "raw_dense_score": 0.36,
            "bm25_score": 3.5,
            "fused_score": 0.03,
        },
    ]
    doc_names = {"d1": "AI Engineering.pdf"}
    passages = RetrievalPipeline.rerank_and_penalize(fused_hits, query, keywords, doc_names)

    # Substantive chunk should rank higher than boilerplate despite boilerplate's higher raw dense score
    assert passages[0].chunk_id == "c_substantive"
    assert passages[1].chunk_id == "c_bp"
    assert passages[1].is_boilerplate is True


def test_relevance_filtering_refusal():
    pipeline = RetrievalPipeline(relevance_threshold=0.30)
    # Passages with 0 keyword match and low score
    passages = [
        RetrievedPassage(
            chunk_id="c1",
            document_id="d1",
            document_name="AI Engineering.pdf",
            page_number=10,
            text="Unrelated text about gardening and soil pH levels.",
            raw_dense_score=0.10,
            bm25_score=0.0,
            fused_score=0.01,
            rerank_score=0.12,
            is_boilerplate=False,
            keyword_matches=[],
        )
    ]
    filtered, has_sufficient = pipeline.filter_relevance(passages, ["kv", "cache"])
    assert has_sufficient is False
    assert len(filtered) == 0


def test_citation_validation():
    passages = [
        RetrievedPassage(
            chunk_id="c1",
            document_id="doc-123",
            document_name="Test.pdf",
            page_number=12,
            text="Speculative decoding achieves 2.5x speedup.",
            rerank_score=0.82,
        ),
        RetrievedPassage(
            chunk_id="c_bp",
            document_id="doc-123",
            document_name="Test.pdf",
            page_number=6,
            text="All rights reserved.",
            rerank_score=0.05,
            is_boilerplate=True,
        ),
    ]
    # If answer contains refusal, citations must be empty
    cits_refusal = ChatService.validate_citations(REFUSAL_MESSAGE, passages)
    assert len(cits_refusal) == 0

    # Valid answer should include non-boilerplate passage
    cits_valid = ChatService.validate_citations("Speculative decoding achieves 2.5x speedup.", passages)
    assert len(cits_valid) == 1
    assert cits_valid[0].pageNumber == 12
    assert cits_valid[0].documentId == "doc-123"
