import uuid
import pytest
from app.ingestion.chunker import Chunker
from app.ingestion.text_cleaner import TextCleaner


def test_text_cleaner():
    raw = "This is a test-\nword with multiple   spaces and\x00 null bytes.\n\n\n\nParagraph 2."
    cleaned = TextCleaner.clean(raw)
    assert "testword" in cleaned
    assert "\x00" not in cleaned
    assert "   " not in cleaned
    assert "\n\n\n" not in cleaned


def test_chunker_page_retention():
    chunker = Chunker(chunk_size=100, chunk_overlap=20, min_chunk_length=10)
    pages = [
        {"page_number": 1, "text": "Page one content with sufficient length to verify chunking behavior and page assignment."},
        {"page_number": 2, "text": "Page two text with another set of paragraphs explaining quantum entanglement."},
    ]

    doc_id = uuid.uuid4()
    nb_id = uuid.uuid4()
    owner_id = uuid.uuid4()

    chunks = chunker.chunk_document(pages, doc_id, nb_id, owner_id)
    assert len(chunks) >= 2
    assert any(c.page_number == 1 for c in chunks)
    assert any(c.page_number == 2 for c in chunks)
    assert all(c.document_id == doc_id for c in chunks)

