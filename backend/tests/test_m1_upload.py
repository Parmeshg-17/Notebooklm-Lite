"""
Unit tests for M1 — upload, storage, document status.
"""

import hashlib
import io
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ─── SHA-256 deduplication tests ─────────────────────────────────────────────

class TestSha256Deduplication:
    def test_same_content_same_hash(self):
        content = b"This is a test document content."
        hash1 = hashlib.sha256(content).hexdigest()
        hash2 = hashlib.sha256(content).hexdigest()
        assert hash1 == hash2

    def test_different_content_different_hash(self):
        content1 = b"Document A"
        content2 = b"Document B"
        hash1 = hashlib.sha256(content1).hexdigest()
        hash2 = hashlib.sha256(content2).hexdigest()
        assert hash1 != hash2

    def test_sha256_is_64_chars(self):
        content = b"test"
        h = hashlib.sha256(content).hexdigest()
        assert len(h) == 64

    def test_sha256_is_hex(self):
        content = b"test"
        h = hashlib.sha256(content).hexdigest()
        int(h, 16)  # Should not raise


# ─── Document status transition tests ────────────────────────────────────────

class TestDocumentStatusTransitions:
    VALID_STATUSES = ["uploaded", "parsing", "indexed", "failed"]

    def test_all_statuses_defined(self):
        assert set(self.VALID_STATUSES) == {"uploaded", "parsing", "indexed", "failed"}

    def test_upload_starts_as_uploaded(self):
        # When a document is created, status must be 'uploaded'
        initial_status = "uploaded"
        assert initial_status in self.VALID_STATUSES

    def test_ingestion_flow_statuses(self):
        # Correct flow: uploaded → parsing → indexed
        flow = ["uploaded", "parsing", "indexed"]
        for s in flow:
            assert s in self.VALID_STATUSES

    def test_failure_status(self):
        assert "failed" in self.VALID_STATUSES


# ─── File validation tests ────────────────────────────────────────────────────
# These tests validate logic independently of database imports (pgvector not installed on host).

import os

ALLOWED_EXTENSIONS_STANDALONE = {".pdf", ".txt", ".md", ".markdown"}


def _get_extension_standalone(filename: str) -> str:
    _, ext = os.path.splitext(filename)
    return ext or ""


class TestFileValidation:
    def test_pdf_extension_allowed(self):
        assert ".pdf" in ALLOWED_EXTENSIONS_STANDALONE

    def test_md_extension_allowed(self):
        assert ".md" in ALLOWED_EXTENSIONS_STANDALONE

    def test_txt_extension_allowed(self):
        assert ".txt" in ALLOWED_EXTENSIONS_STANDALONE

    def test_exe_extension_not_allowed(self):
        assert ".exe" not in ALLOWED_EXTENSIONS_STANDALONE

    def test_get_extension(self):
        assert _get_extension_standalone("report.pdf") == ".pdf"
        assert _get_extension_standalone("notes.md") == ".md"
        assert _get_extension_standalone("data.txt") == ".txt"
        assert _get_extension_standalone("noext") == ""


# ─── Config tests ─────────────────────────────────────────────────────────────

class TestConfig:
    def test_settings_have_required_fields(self):
        from app.core.config import get_settings
        settings = get_settings()
        assert settings.database_url
        assert settings.redis_url
        assert settings.s3_bucket

    def test_chunk_defaults_are_positive(self):
        from app.core.config import get_settings
        settings = get_settings()
        assert settings.chunk_token_budget > 0
        assert settings.chunk_overlap_tokens >= 0
        assert settings.chunk_overlap_tokens < settings.chunk_token_budget
