import pytest
import math
from app.rag.embeddings.gemini_embeddings import GeminiEmbeddingService, VECTOR_DIMENSION


@pytest.mark.asyncio
async def test_gemini_embedding_service_dimensions():
    service = GeminiEmbeddingService()
    vec = await service.aembed_query("What is speculative decoding in transformer inference?")
    assert len(vec) == VECTOR_DIMENSION
    assert VECTOR_DIMENSION == 768

    # Check unit normalization
    norm = math.sqrt(sum(x * x for x in vec))
    assert abs(norm - 1.0) < 1e-3


@pytest.mark.asyncio
async def test_batch_document_embedding():
    service = GeminiEmbeddingService(batch_size=2)
    docs = [
        "First document on neural attention mechanisms.",
        "Second document discussing KV cache memory bottlenecks.",
        "Third document detailing quantization techniques.",
    ]
    vectors = await service.aembed_documents(docs)
    assert len(vectors) == 3
    for v in vectors:
        assert len(v) == 768
        norm = math.sqrt(sum(x * x for x in v))
        assert abs(norm - 1.0) < 1e-3


@pytest.mark.asyncio
async def test_empty_text_handling():
    service = GeminiEmbeddingService()
    vec = await service.aembed_query("")
    assert len(vec) == 768
    norm = math.sqrt(sum(x * x for x in vec))
    assert abs(norm - 1.0) < 1e-3

    vectors = await service.aembed_documents(["   ", ""])
    assert len(vectors) == 2
    for v in vectors:
        assert len(v) == 768


def test_sync_langchain_interfaces():
    service = GeminiEmbeddingService()
    q_vec = service.embed_query("Sync query test")
    assert len(q_vec) == 768

    doc_vecs = service.embed_documents(["Doc one", "Doc two"])
    assert len(doc_vecs) == 2
    assert len(doc_vecs[0]) == 768


def test_telemetry():
    service = GeminiEmbeddingService()
    _ = service.embed_query("Telemetry sample")
    telemetry = service.get_telemetry()
    assert telemetry["dimension"] == 768
    assert "model_name" in telemetry

