import pytest
import uuid
from app.rag.ingestion.text_cleaner import TextCleaner
from app.rag.ingestion.text_splitter import DocumentSplitter
from app.rag.retrieval.qdrant_store import QdrantStore


def test_text_cleaner():
    raw = "Here is some text with ‘smart quotes’ and “curly quotes” and — em dash.\x00\x08"
    cleaned = TextCleaner.clean_text(raw)
    assert "'" in cleaned
    assert '"' in cleaned
    assert "-" in cleaned
    assert "\x00" not in cleaned
    assert "\x08" not in cleaned

    # Test table of contents dot collapse
    toc = "Chapter 1. . . . . . . . 15"
    cleaned_toc = TextCleaner.clean_text(toc)
    assert "Chapter 1...15" == cleaned_toc


def test_document_splitter_preserves_page_numbers():
    splitter = DocumentSplitter(chunk_size=100, chunk_overlap=20)
    pages = [
        {"page_number": 1, "text": "This is page one content about machine learning systems and foundations."},
        {"page_number": 2, "text": "This is page two content detailing model evaluation, metrics and testing."},
    ]
    doc_id = uuid.uuid4()
    nb_id = uuid.uuid4()
    user_id = uuid.uuid4()

    chunks = splitter.split_pages(
        pages=pages,
        document_id=doc_id,
        notebook_id=nb_id,
        user_id=user_id,
        filename="research.pdf",
    )

    assert len(chunks) >= 2
    # Check first chunk
    c1 = chunks[0]
    assert c1.page_number == 1
    assert c1.filename == "research.pdf"
    assert c1.document_id == str(doc_id)
    assert c1.user_id == str(user_id)
    assert c1.notebook_id == str(nb_id)
    assert c1.chunk_index == 0
    assert len(c1.chunk_id) > 10
    assert c1.contributing_pages == [1]

    # Check that second page chunk has page_number 2
    c2 = chunks[-1]
    assert c2.page_number == 2
    assert c2.contributing_pages == [2]

    # Check to_dict() schema
    d = c1.to_dict()
    assert d["chunk_id"] == c1.chunk_id
    assert d["page_number"] == 1
    assert "chunk_text" in d


@pytest.mark.asyncio
async def test_qdrant_store_isolation():
    # Use memory Qdrant store
    store = QdrantStore()
    store.url = ":memory:"
    store.collection_name = f"test_col_{uuid.uuid4().hex[:8]}"

    await store.ensure_collection(vector_size=4)

    user_a = uuid.uuid4()
    user_b = uuid.uuid4()
    notebook_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    class MockChunk:
        def __init__(self, cid, uid, nid, did, pg, txt):
            self.chunk_id = cid
            self.user_id = str(uid)
            self.notebook_id = str(nid)
            self.document_id = str(did)
            self.filename = "doc.pdf"
            self.page_number = pg
            self.chunk_index = 0
            self.chunk_text = txt
            self.contributing_pages = [pg]

        def to_dict(self):
            return {
                "chunk_id": self.chunk_id,
                "user_id": self.user_id,
                "owner_id": self.user_id,
                "notebook_id": self.notebook_id,
                "document_id": self.document_id,
                "filename": self.filename,
                "page_number": self.page_number,
                "chunk_index": self.chunk_index,
                "chunk_text": self.chunk_text,
                "text": self.chunk_text,
                "contributing_pages": self.contributing_pages,
            }

    c_a = MockChunk("c-a", user_a, notebook_id, doc_id, 1, "User A confidential data")
    c_b = MockChunk("c-b", user_b, notebook_id, doc_id, 2, "User B secret data")

    # Upsert both
    await store.upsert_chunks([c_a], [[1.0, 0.0, 0.0, 0.0]])
    await store.upsert_chunks([c_b], [[1.0, 0.0, 0.0, 0.0]])

    # Search as User A -> Must only return User A's chunks
    hits_a = await store.similarity_search(
        query_vector=[1.0, 0.0, 0.0, 0.0],
        user_id=user_a,
        notebook_id=notebook_id,
    )
    assert len(hits_a) == 1
    assert hits_a[0]["chunk_id"] == "c-a"
    assert "User A" in hits_a[0]["text"]

    # Search as User B -> Must only return User B's chunks
    hits_b = await store.similarity_search(
        query_vector=[1.0, 0.0, 0.0, 0.0],
        user_id=user_b,
        notebook_id=notebook_id,
    )
    assert len(hits_b) == 1
    assert hits_b[0]["chunk_id"] == "c-b"
    assert "User B" in hits_b[0]["text"]
