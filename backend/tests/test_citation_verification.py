"""
Unit Tests for Citation Verification Service in NotebookLM Lite.
Enforces: NO SOURCE, NO SENTENCE.
Verifies real document and page references, hallucination rejection, and factual grounding.
"""

import uuid
import pytest
from app.services.citation_verifier import CitationVerifier


def test_valid_citation_verification():
    doc_id = str(uuid.uuid4())
    retrieved_chunks = [
        {
            "chunk_id": "c1",
            "document_id": doc_id,
            "filename": "inference_optimization.pdf",
            "page_number": 4,
            "text": "FlashAttention-3 leverages TMA (Tensor Memory Accelerator) to enable asynchronous memory copies between global memory and shared memory (SRAM) without register file allocation.",
            "score": 0.95,
        }
    ]

    answer = "FlashAttention-3 uses the Tensor Memory Accelerator for asynchronous transfers without register allocation."
    citations = [
        {
            "document_id": doc_id,
            "filename": "inference_optimization.pdf",
            "page_number": 4,
            "excerpt": "FlashAttention-3 leverages TMA (Tensor Memory Accelerator) to enable asynchronous memory copies",
        }
    ]

    verified, is_grounded, status = CitationVerifier.verify_citations(
        citations=citations,
        retrieved_chunks=retrieved_chunks,
        answer_text=answer,
    )

    assert status == "VERIFIED"
    assert is_grounded is True
    assert len(verified) == 1
    assert verified[0]["page_number"] == 4
    assert verified[0]["document_id"] == doc_id


def test_hallucinated_page_citation_stripped():
    doc_id = str(uuid.uuid4())
    retrieved_chunks = [
        {
            "chunk_id": "c1",
            "document_id": doc_id,
            "filename": "speculative_decoding.pdf",
            "page_number": 2,
            "text": "Draft models generate candidate tokens that are subsequently verified in parallel.",
            "score": 0.88,
        }
    ]

    answer = "Draft models generate tokens verified in parallel."
    # Fabricated page 99
    citations = [
        {
            "document_id": doc_id,
            "filename": "speculative_decoding.pdf",
            "page_number": 99,
            "excerpt": "Draft models generate candidate tokens",
        }
    ]

    verified, is_grounded, status = CitationVerifier.verify_citations(
        citations=citations,
        retrieved_chunks=retrieved_chunks,
        answer_text=answer,
    )

    # Page 99 should be rejected
    assert len(verified) == 0
    assert status == "FAILED"
    assert is_grounded is False


def test_hallucinated_document_id_stripped():
    retrieved_chunks = [
        {
            "chunk_id": "c1",
            "document_id": str(uuid.uuid4()),
            "filename": "real_doc.pdf",
            "page_number": 1,
            "text": "Real content from source.",
            "score": 0.9,
        }
    ]

    # Fabricated document ID and non-existent page
    citations = [
        {
            "document_id": str(uuid.uuid4()),
            "filename": "invented_doc.pdf",
            "page_number": 50,
            "excerpt": "Invented passage that doesn't exist.",
        }
    ]

    verified, is_grounded, status = CitationVerifier.verify_citations(
        citations=citations,
        retrieved_chunks=retrieved_chunks,
        answer_text="Some invented claim.",
    )

    assert len(verified) == 0
    assert status == "FAILED"
    assert is_grounded is False


def test_refusal_with_zero_citations_is_valid():
    refusal_text = "The available documents do not contain sufficient evidence to answer this question."
    verified, is_grounded, status = CitationVerifier.verify_citations(
        citations=[],
        retrieved_chunks=[],
        answer_text=refusal_text,
    )

    assert status == "VERIFIED"
    assert is_grounded is True
    assert len(verified) == 0

