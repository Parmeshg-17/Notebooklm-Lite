import pytest
from app.rag.generation.answer_parser import AnswerParser, GroundedCitationItem
from app.rag.generation.prompts import REFUSAL_MESSAGE
from app.rag.citations.citation_validator import CitationValidator


def test_answer_parser_json():
    raw_json = """```json
    {
        "answer": "Speculative decoding achieves 2.5x speedup.",
        "citations": [
            {
                "claim": "2.5x speedup",
                "document_id": "doc-1",
                "filename": "paper.pdf",
                "page_number": 45,
                "chunk_id": "c-1",
                "excerpt": "Results indicate speculative decoding achieves 2.5x speedup."
            }
        ],
        "supporting_claims": ["2.5x speedup"],
        "insufficient_evidence": false
    }
    ```"""
    parsed = AnswerParser.parse_raw_response(raw_json, [])
    assert "2.5x speedup" in parsed.answer
    assert len(parsed.citations) == 1
    assert parsed.citations[0].page_number == 45
    assert parsed.citations[0].document_id == "doc-1"
    assert parsed.insufficient_evidence is False


def test_citation_validator_valid():
    retrieved_chunks = [
        {
            "chunk_id": "c-1",
            "document_id": "doc-1",
            "filename": "paper.pdf",
            "page_number": 45,
            "chunk_text": "Results indicate speculative decoding achieves 2.5x speedup on H100 GPUs.",
            "rerank_score": 0.85,
        }
    ]
    citations = [
        GroundedCitationItem(
            claim="speculative decoding achieves 2.5x speedup",
            document_id="doc-1",
            filename="paper.pdf",
            page_number=45,
            chunk_id="c-1",
            excerpt="Results indicate speculative decoding achieves 2.5x speedup",
        )
    ]
    valid_cits, is_grounded = CitationValidator.validate_citations(
        citations, retrieved_chunks, "Speculative decoding achieves 2.5x speedup."
    )
    assert is_grounded is True
    assert len(valid_cits) == 1
    assert valid_cits[0]["page_number"] == 45
    assert valid_cits[0]["document_id"] == "doc-1"
    assert valid_cits[0]["documentId"] == "doc-1"  # Frontend compatibility


def test_citation_validator_rejects_hallucinated_page():
    retrieved_chunks = [
        {
            "chunk_id": "c-1",
            "document_id": "doc-1",
            "filename": "paper.pdf",
            "page_number": 45,
            "chunk_text": "Real text on page 45.",
        }
    ]
    citations = [
        GroundedCitationItem(
            claim="Hallucinated claim",
            document_id="doc-1",
            filename="paper.pdf",
            page_number=999,  # Hallucinated page not in retrieved chunks!
            chunk_id="c-fake",
            excerpt="Fake excerpt",
        )
    ]
    valid_cits, is_grounded = CitationValidator.validate_citations(
        citations, retrieved_chunks, "Some answer."
    )
    # The hallucinated citation should not be validated
    assert not any(c["page_number"] == 999 for c in valid_cits)
    assert is_grounded is False


def test_refusal_returns_no_citations():
    retrieved_chunks = [
        {"chunk_id": "c-1", "document_id": "doc-1", "page_number": 1, "chunk_text": "Text"}
    ]
    valid_cits, is_grounded = CitationValidator.validate_citations(
        [], retrieved_chunks, REFUSAL_MESSAGE
    )
    assert len(valid_cits) == 0
    assert is_grounded is False

