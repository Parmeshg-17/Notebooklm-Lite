import pytest
from app.services.document_service import DocumentService


class MockDoc:
    def __init__(self, status, error=None):
        self.processing_status = status
        self.processing_error = error


def test_document_status_percentages():
    expected_mapping = {
        "UPLOADED": 10,
        "EXTRACTING": 25,
        "CHUNKING": 45,
        "EMBEDDING": 70,
        "INDEXING": 90,
        "INDEXED": 100,
        "FAILED": 0,
    }

    for status, expected_pct in expected_mapping.items():
        doc = MockDoc(status)
        pct, is_failed, err = DocumentService.calculate_status_progress(
            doc.processing_status, doc.processing_error
        )
        assert pct == expected_pct, f"Status {status} expected {expected_pct}%, got {pct}%"
        if status == "FAILED":
            assert is_failed is True
        else:
            assert is_failed is False


def test_failed_document_status():
    doc = MockDoc("FAILED", "Extraction error: corrupt PDF header")
    pct, is_failed, err = DocumentService.calculate_status_progress(
        doc.processing_status, doc.processing_error
    )
    assert pct == 0
    assert is_failed is True
    assert "Extraction error" in err
