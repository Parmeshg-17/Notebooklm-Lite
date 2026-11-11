import pytest
import math
from app.vectorstore.embeddings import embedding_service, VECTOR_DIMENSION


def dot_product(v1, v2):
    return sum(a * b for a, b in zip(v1, v2))


def l2_norm(v):
    return math.sqrt(sum(a * a for a in v))


def test_embedding_dimension():
    vec = embedding_service._fallback_embedding("Transformers and attention mechanisms.")
    assert len(vec) == VECTOR_DIMENSION
    assert VECTOR_DIMENSION == 768


def test_embedding_normalization():
    texts = [
        "What are the key findings in this document?",
        "AlexNet won ImageNet in 2012.",
        "",
        "Short",
    ]
    for text in texts:
        vec = embedding_service._fallback_embedding(text)
        norm = l2_norm(vec)
        assert abs(norm - 1.0) < 1e-4, f"Norm {norm} is not unit for text: {text}"


def test_identical_texts_similarity():
    text = "FlashAttention-3 achieves 1.5-2.0x speedup over FlashAttention-2 on H100 GPUs."
    v1 = embedding_service._fallback_embedding(text)
    v2 = embedding_service._fallback_embedding(text)
    sim = dot_product(v1, v2)
    assert abs(sim - 1.0) < 1e-5, f"Expected 1.0 for identical text, got {sim}"


def test_unrelated_texts_orthogonality():
    t1 = "Cooking Italian pizza with sourdough mozzarella and organic tomato sauce."
    t2 = "Quantum error correction codes in fault-tolerant topological superconducting qubits."
    v1 = embedding_service._fallback_embedding(t1)
    v2 = embedding_service._fallback_embedding(t2)
    sim = dot_product(v1, v2)
    # With zero-mean signed hashing and stopword removal, unrelated topics should not sit at 0.35
    assert abs(sim) < 0.18, f"Expected near-orthogonal similarity (<0.18), got {sim:.4f}"


def test_related_texts_high_similarity():
    t1 = "FlashAttention-3 achieves 1.5-2.0x speedup on Hopper H100 GPUs using TMA."
    t2 = "FlashAttention-3 achieves 2.0x speedup on Hopper GPUs using Tensor Memory Accelerator."
    v1 = embedding_service._fallback_embedding(t1)
    v2 = embedding_service._fallback_embedding(t2)
    sim = dot_product(v1, v2)
    assert sim > 0.40, f"Expected related texts to have sim > 0.40, got {sim:.4f}"


def test_empty_string_handling():
    vec = embedding_service._fallback_embedding("")
    assert len(vec) == 768
    assert abs(l2_norm(vec) - 1.0) < 1e-4
