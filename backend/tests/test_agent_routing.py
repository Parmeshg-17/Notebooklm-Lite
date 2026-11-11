"""
Unit and Integration Tests for LangGraph Intent Routing in NotebookLM Lite.
Validates the 6 supported question intents and regex/heuristic extraction.
"""

import pytest
from app.agents.router import IntentRouter


@pytest.mark.asyncio
async def test_route_page_specific_question():
    """Verify explicit page references are routed to PAGE_SPECIFIC_QUESTION with target page extracted."""
    queries = [
        ("What does page 4 discuss regarding attention latency?", 4),
        ("Explain the diagram on p. 12", 12),
        ("At page 7, what is the throughput benchmark?", 7),
    ]
    for q, expected_page in queries:
        res = await IntentRouter.route_question(q)
        assert res["intent"] == "PAGE_SPECIFIC_QUESTION"
        assert res["target_page"] == expected_page


@pytest.mark.asyncio
async def test_route_comparison_question():
    """Verify comparison, versus, and difference queries route to COMPARISON_QUESTION."""
    queries = [
        "Compare FlashAttention-3 versus FlashAttention-2 in terms of speedup.",
        "What are the differences between PagedAttention and vLLM memory management?",
        "Contrast the trade-offs of FP8 quantization versus FP16 precision.",
    ]
    for q in queries:
        res = await IntentRouter.route_question(q)
        assert res["intent"] == "COMPARISON_QUESTION"
        assert len(res["sub_questions"]) >= 2


@pytest.mark.asyncio
async def test_route_document_summary():
    """Verify summary, overview, and outline queries route to DOCUMENT_SUMMARY."""
    queries = [
        "Summarize the key findings in this document",
        "Give me an overview of the architecture proposed",
        "TLDR of the experimental results and conclusions",
    ]
    for q in queries:
        res = await IntentRouter.route_question(q)
        assert res["intent"] == "DOCUMENT_SUMMARY"


@pytest.mark.asyncio
async def test_route_multi_document_question():
    """Verify queries spanning multiple sources route to MULTI_DOCUMENT_QUESTION."""
    queries = [
        "What are the findings across all documents in this notebook?",
        "Compare the conclusions in both papers regarding inference cost.",
    ]
    for q in queries:
        res = await IntentRouter.route_question(q, document_titles=["Paper 1", "Paper 2"])
        assert res["intent"] in ["MULTI_DOCUMENT_QUESTION", "COMPARISON_QUESTION"]


@pytest.mark.asyncio
async def test_route_insufficient_evidence():
    """Verify off-topic questions, greetings, and chit-chat route to INSUFFICIENT_EVIDENCE."""
    queries = [
        "What is the weather in Paris tomorrow?",
        "Hello, how are you today?",
        "Write a poem about the sunrise",
        "Tell me a joke about computers",
    ]
    for q in queries:
        res = await IntentRouter.route_question(q)
        assert res["intent"] == "INSUFFICIENT_EVIDENCE"


@pytest.mark.asyncio
async def test_route_simple_question():
    """Verify targeted factual queries default to SIMPLE_QUESTION."""
    queries = [
        "What is the effective FLOPS equation?",
        "How does the Tensor Memory Accelerator work?",
        "What was the perplexity regression on LLaMA-3 70B?",
    ]
    for q in queries:
        res = await IntentRouter.route_question(q)
        assert res["intent"] == "SIMPLE_QUESTION"
        assert res["target_page"] is None


@pytest.mark.asyncio
async def test_route_empty_notebook_refusal():
    """Verify notebooks with zero documents immediately trigger INSUFFICIENT_EVIDENCE."""
    res = await IntentRouter.route_question("Explain everything", has_documents=False)
    assert res["intent"] == "INSUFFICIENT_EVIDENCE"

