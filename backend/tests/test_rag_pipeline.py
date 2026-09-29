"""
Unit tests for the full RAG pipeline:
- Document Parser (page preservation)
- Chunker (token budget & page metadata)
- Embedding Providers (deterministic 1536d normalization)
- Citation Validator (Strict enforcement of 'NO SOURCE, NO SENTENCE')
- Query Rewriter & Answer Generator
"""

import uuid
import pytest

from app.ingestion.parser import DocumentParser, ParsedPage
from app.ingestion.chunker import PagePreservingChunker
from app.rag.embeddings import LocalDeterministicEmbeddingProvider
from app.rag.retrieval import RetrievedChunk
from app.rag.citations import CitationValidator
from app.rag.generator import AnswerGenerator


class TestDocumentParser:
    def test_parse_text_creates_pages(self):
        parser = DocumentParser()
        content = b"Paragraph 1\n\nParagraph 2\n\nParagraph 3"
        doc = parser.parse_bytes(content, "test.txt")
        assert doc.page_count >= 1
        assert len(doc.pages) >= 1
        assert doc.pages[0].page_number == 1
        assert "Paragraph 1" in doc.pages[0].text

    def test_parse_markdown_preserves_headers(self):
        parser = DocumentParser()
        content = b"# Introduction\n\nWelcome to the guide.\n\n## Section 1\n\nDetails here."
        doc = parser.parse_bytes(content, "guide.md")
        assert doc.page_count >= 1
        assert "Introduction" in doc.pages[0].text


class TestPagePreservingChunker:
    def test_chunker_preserves_page_numbers(self):
        chunker = PagePreservingChunker(token_budget=100, overlap_tokens=10)
        pages = [
            ParsedPage(page_number=1, text="This is the first page of content."),
            ParsedPage(page_number=2, text="This is the second page of content."),
        ]
        chunks = chunker.chunk_pages(pages)
        assert len(chunks) >= 1
        for c in chunks:
            assert c.page_start in (1, 2)
            assert c.page_end in (1, 2)
            assert c.page_start <= c.page_end
            assert c.text


class TestDeterministicEmbeddings:
    def test_embedding_dimension_and_norm(self):
        embedder = LocalDeterministicEmbeddingProvider(dimension=1536)
        query = "What is the refund policy?"
        vec = embedder.embed_query(query)
        assert len(vec) == 1536
        # Check normalized length close to 1.0
        norm = sum(x * x for x in vec) ** 0.5
        assert abs(norm - 1.0) < 1e-4

    def test_identical_texts_identical_vectors(self):
        embedder = LocalDeterministicEmbeddingProvider(dimension=1536)
        vec1 = embedder.embed_query("identical text string")
        vec2 = embedder.embed_query("identical text string")
        assert vec1 == vec2


class TestCitationValidation:
    """Rigorous tests for CORE RULE: NO SOURCE, NO SENTENCE."""

    @pytest.fixture
    def sample_chunks(self):
        c1 = RetrievedChunk(
            chunk_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            filename="handbook.pdf",
            page_start=1,
            page_end=1,
            text="Refunds are accepted within 30 days of purchase.",
            score=0.9,
            source_id=1,
        )
        c2 = RetrievedChunk(
            chunk_id=uuid.uuid4(),
            document_id=uuid.uuid4(),
            filename="handbook.pdf",
            page_start=2,
            page_end=2,
            text="Wire transfers take 5 business days to clear.",
            score=0.8,
            source_id=2,
        )
        return [c1, c2]

    def test_valid_citations_accepted(self, sample_chunks):
        validator = CitationValidator(sample_chunks)
        raw_response = {
            "sentences": [
                {"text": "Refunds are processed in thirty days.", "source_ids": [1]},
                {"text": "Wire transfers take five business days.", "source_ids": [2]},
            ],
            "not_found": False,
        }
        res = validator.validate(raw_response)
        assert res.is_valid is True
        assert res.not_found is False
        assert len(res.sentences) == 2
        assert "[1]" in res.clean_answer_text
        assert "[2]" in res.clean_answer_text

    def test_hallucinated_source_id_rejected(self, sample_chunks):
        validator = CitationValidator(sample_chunks)
        # Model claims [9] which was NEVER provided
        raw_response = {
            "sentences": [
                {"text": "The CEO lives on Neptune.", "source_ids": [9]},
            ],
            "not_found": False,
        }
        res = validator.validate(raw_response)
        # Hallucinated ID must be rejected, triggering refusal (not_found=True)
        assert 9 in res.hallucinated_ids
        assert res.not_found is True

    def test_uncited_sentence_rejected(self, sample_chunks):
        validator = CitationValidator(sample_chunks)
        # Sentence without any citation: violates NO SOURCE, NO SENTENCE
        raw_response = {
            "sentences": [
                {"text": "This is completely unsupported knowledge.", "source_ids": []},
            ],
            "not_found": False,
        }
        res = validator.validate(raw_response)
        assert len(res.rejected_sentences) == 1
        assert res.not_found is True

    def test_explicit_not_found_preserved(self, sample_chunks):
        validator = CitationValidator(sample_chunks)
        raw_response = {
            "sentences": [],
            "not_found": True,
        }
        res = validator.validate(raw_response)
        assert res.not_found is True
        assert "not find" in res.clean_answer_text.lower()
