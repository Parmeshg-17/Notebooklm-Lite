"""
Comprehensive test suite for the NotebookLM Lite Evaluation Module (Phase 4 / Evaluation Benchmark).
Validates:
1. Dataset loading and Pydantic schema validation across all 70 questions.
2. Malformed dataset validation errors.
3. Fine-grained scoring for all 6 metrics:
   - Answer relevance
   - Retrieval relevance
   - Citation precision
   - Citation page accuracy
   - Claim grounding
   - Abstention accuracy
4. Multi-document prerequisite enforcement (BLOCKED when doc count < 2).
5. Strict status guarantees (never treat failed/unexecuted as PASS).
6. Summary and category-level aggregation.
7. CLI parser validation.
8. End-to-end evaluation runner execution.
"""

import json
from pathlib import Path
import tempfile
import pytest

from app.evaluation.dataset_loader import (
    filter_questions,
    load_evaluation_dataset,
    resolve_dataset_path,
)
from app.evaluation.evaluator import RAGEvaluator
from app.evaluation.metrics import (
    RAGEvaluationMetrics,
    extract_keywords,
    is_refusal_text,
    parse_page_hint,
)
from app.evaluation.runner import aggregate_summaries, resolve_benchmark_notebook, run_benchmark
from app.evaluation.schemas import (
    EvaluationDataset,
    EvaluationMode,
    EvaluationQuestion,
    EvaluationStatus,
    QuestionCategory,
)
from app.evaluation.cli import build_parser


# ============================================================================
# 1. Dataset Loading and Schema Validation Tests
# ============================================================================

def test_load_full_evaluation_dataset():
    """Verify loading and validating the canonical 70-question benchmark dataset."""
    dataset = load_evaluation_dataset()

    assert dataset is not None
    assert dataset.total_questions == 70
    assert len(dataset.questions) == 70
    assert "AI Engineering.pdf" in dataset.source_documents

    # Verify declared category counts match question counts
    expected_counts = {
        "straightforward": 20,
        "multi_document": 15,
        "comparison": 10,
        "page_specific": 10,
        "unanswerable": 15,
    }
    assert dataset.category_counts == expected_counts

    actual_counts = {}
    for q in dataset.questions:
        cat = q.category.value
        actual_counts[cat] = actual_counts.get(cat, 0) + 1
    assert actual_counts == expected_counts


def test_question_field_integrity():
    """Verify individual question fields and types."""
    dataset = load_evaluation_dataset()

    for q in dataset.questions:
        assert q.id.startswith("Q")
        assert len(q.question) >= 5
        assert isinstance(q.answerable_from_source, bool)
        assert q.evaluation_mode in (
            EvaluationMode.GROUNDED_ANSWER,
            EvaluationMode.ABSTAIN_IF_NOT_IN_SOURCES,
        )

        if q.category == QuestionCategory.PAGE_SPECIFIC:
            assert q.page_hint_printed is not None
            assert len(q.page_hint_printed) > 0

        if q.category == QuestionCategory.MULTI_DOCUMENT:
            assert q.requires_multiple_documents is True

        if q.category == QuestionCategory.UNANSWERABLE:
            assert q.answerable_from_source is False
            assert q.evaluation_mode == EvaluationMode.ABSTAIN_IF_NOT_IN_SOURCES


def test_malformed_dataset_rejection():
    """Verify that datasets violating schema or count constraints are rejected."""
    # Test count mismatch
    bad_data = {
        "dataset_name": "Test",
        "dataset_version": "1.0",
        "source_documents": ["Doc.pdf"],
        "total_questions": 5,  # declared 5
        "category_counts": {"straightforward": 5},
        "questions": [  # only 1 provided
            {
                "id": "Q001",
                "category": "straightforward",
                "question": "What is AI?",
                "answerable_from_source": True,
                "evaluation_mode": "grounded_answer",
                "expected_behavior": "Grounded answer.",
            }
        ],
    }

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
        json.dump(bad_data, tf)
        temp_path = tf.name

    try:
        with pytest.raises(ValueError, match="Question count mismatch"):
            load_evaluation_dataset(temp_path)
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_filter_questions():
    """Verify filtering questions by category and limit."""
    dataset = load_evaluation_dataset()

    straightforward = filter_questions(dataset, category=QuestionCategory.STRAIGHTFORWARD)
    assert len(straightforward) == 20
    assert all(q.category == QuestionCategory.STRAIGHTFORWARD for q in straightforward)

    limited = filter_questions(dataset, limit=5)
    assert len(limited) == 5

    cat_limited = filter_questions(dataset, category="unanswerable", limit=3)
    assert len(cat_limited) == 3
    assert all(q.category == QuestionCategory.UNANSWERABLE for q in cat_limited)


# ============================================================================
# 2. Metric Scoring Unit Tests
# ============================================================================

def test_metric_answer_relevance():
    """Verify answer relevance scoring for answerable and unanswerable queries."""
    # Answerable question with relevant answer
    q = "What is AI engineering?"
    ans = "AI engineering is the discipline of building software applications with foundation models."
    score = RAGEvaluationMetrics.score_answer_relevance(q, ans, answerable_from_source=True)
    assert score >= 0.70

    # Answerable question with false refusal
    false_refusal = "I couldn't find sufficient supporting information in your uploaded documents."
    score_refusal = RAGEvaluationMetrics.score_answer_relevance(q, false_refusal, answerable_from_source=True)
    assert score_refusal == 0.0

    # Unanswerable question with correct refusal
    unans_q = "What was the company's Q3 revenue in 2025?"
    score_unans_refusal = RAGEvaluationMetrics.score_answer_relevance(unans_q, false_refusal, answerable_from_source=False)
    assert score_unans_refusal == 1.0

    # Unanswerable question with hallucinated answer
    hallucinated = "The company generated 50 million dollars in Q3 2025."
    score_hallucinated = RAGEvaluationMetrics.score_answer_relevance(unans_q, hallucinated, answerable_from_source=False)
    assert score_hallucinated == 0.0


def test_metric_retrieval_relevance():
    """Verify retrieval relevance scoring."""
    q = "Explain retrieval augmented generation."
    chunks = [
        {"text": "Retrieval-augmented generation (RAG) combines search retrieval with language model generation.", "score": 0.88},
        {"text": "Document chunking and vector indexing are key steps in RAG pipelines.", "score": 0.75},
    ]
    score = RAGEvaluationMetrics.score_retrieval_relevance(q, chunks, answerable_from_source=True)
    assert score == 1.0

    # Empty chunks on answerable question
    assert RAGEvaluationMetrics.score_retrieval_relevance(q, [], answerable_from_source=True) == 0.0


def test_metric_citation_precision():
    """Verify citation precision for valid, invalid, and empty citations."""
    # Answerable with valid citations
    valid_citations = [
        {"document_id": "doc1", "filename": "AI_Engineering.pdf", "page_number": 14, "text_excerpt": "RAG architecture"},
        {"document_id": "doc1", "filename": "AI_Engineering.pdf", "page_number": 15, "text_excerpt": "Evaluation metrics"},
    ]
    assert RAGEvaluationMetrics.score_citation_precision(valid_citations, answerable_from_source=True) == 1.0

    # Answerable with invalid (null page) citation
    mixed = [
        {"document_id": "doc1", "page_number": 14, "text_excerpt": "Valid"},
        {"document_id": "doc1", "page_number": None, "text_excerpt": "Invalid"},
    ]
    assert RAGEvaluationMetrics.score_citation_precision(mixed, answerable_from_source=True) == 0.5

    # Answerable with 0 citations
    assert RAGEvaluationMetrics.score_citation_precision([], answerable_from_source=True) == 0.0

    # Unanswerable with 0 citations (expected)
    assert RAGEvaluationMetrics.score_citation_precision([], answerable_from_source=False) == 1.0

    # Unanswerable with fabricated citations
    assert RAGEvaluationMetrics.score_citation_precision(valid_citations, answerable_from_source=False) == 0.0


def test_metric_citation_page_accuracy():
    """Verify page accuracy with printed page hints."""
    # Single page hint "256"
    assert parse_page_hint("256").issuperset({254, 255, 256, 257, 258})

    # Range hint "218–220"
    assert parse_page_hint("218–220").issuperset({218, 219, 220})

    citations = [{"page_number": 256, "text_excerpt": "RAG overview"}]
    retrieved = [{"page_number": 256, "text": "RAG overview"}]

    score = RAGEvaluationMetrics.score_citation_page_accuracy(
        citations=citations,
        retrieved_chunks=retrieved,
        page_hint_printed="256",
        answerable_from_source=True,
    )
    assert score == 1.0

    # Mismatched page
    mismatched = [{"page_number": 40, "text_excerpt": "Unrelated topic"}]
    score_mismatch = RAGEvaluationMetrics.score_citation_page_accuracy(
        citations=mismatched,
        retrieved_chunks=mismatched,
        page_hint_printed="256",
        answerable_from_source=True,
    )
    assert score_mismatch == 0.0


def test_metric_abstention_accuracy():
    """Verify abstention accuracy evaluation."""
    # Unanswerable question: refused with 0 citations -> PASS
    score = RAGEvaluationMetrics.score_abstention_accuracy(
        answer="I couldn't find sufficient supporting information in your uploaded documents.",
        citations=[],
        insufficient_evidence_flag=True,
        answerable_from_source=False,
    )
    assert score == 1.0

    # Unanswerable question: answered with citations -> FAIL
    score_hallucinated = RAGEvaluationMetrics.score_abstention_accuracy(
        answer="The author was born in 1985.",
        citations=[{"page_number": 1}],
        insufficient_evidence_flag=False,
        answerable_from_source=False,
    )
    assert score_hallucinated == 0.0

    # Answerable question: answered with citations -> PASS
    score_ans = RAGEvaluationMetrics.score_abstention_accuracy(
        answer="RAG stands for retrieval augmented generation.",
        citations=[{"page_number": 256}],
        insufficient_evidence_flag=False,
        answerable_from_source=True,
    )
    assert score_ans == 1.0

    # Answerable question: falsely refused -> FAIL
    score_false_refusal = RAGEvaluationMetrics.score_abstention_accuracy(
        answer="I couldn't find sufficient supporting information in your uploaded documents.",
        citations=[],
        insufficient_evidence_flag=True,
        answerable_from_source=True,
    )
    assert score_false_refusal == 0.0


# ============================================================================
# 3. Multi-Document and Status Enforcement Tests (Req 6 & 7)
# ============================================================================

def test_multi_document_precondition_blocked():
    """
    Requirement 6: Mark multi-document tests BLOCKED if fewer than two relevant documents are available.
    """
    q_multi = EvaluationQuestion(
        id="Q021",
        category=QuestionCategory.MULTI_DOCUMENT,
        question="Across uploaded documents, compare their methodologies.",
        answerable_from_source=True,
        evaluation_mode=EvaluationMode.GROUNDED_ANSWER,
        expected_behavior="Multi-doc answer.",
        requires_multiple_documents=True,
    )

    # When available_doc_count == 1
    result = RAGEvaluator.evaluate_question(
        question=q_multi,
        available_doc_count=1,
    )

    assert result.status == EvaluationStatus.BLOCKED
    assert "BLOCKED" in (result.reason or "")
    assert "only 1 document is available" in (result.reason or "").lower()


def test_never_treat_unexecuted_or_failed_as_pass():
    """
    Requirement 7: Never treat an unexecuted or failed test as PASS.
    """
    q_straight = EvaluationQuestion(
        id="Q001",
        category=QuestionCategory.STRAIGHTFORWARD,
        question="What is AI engineering?",
        answerable_from_source=True,
        evaluation_mode=EvaluationMode.GROUNDED_ANSWER,
        expected_behavior="Answer from source.",
    )

    # 1. Unexecuted / empty output -> FAIL
    res_empty = RAGEvaluator.evaluate_question(q_straight, available_doc_count=1, pipeline_output=None)
    assert res_empty.status == EvaluationStatus.FAIL
    assert res_empty.status != EvaluationStatus.PASS

    # 2. Execution error -> ERROR
    res_err = RAGEvaluator.evaluate_question(
        q_straight,
        available_doc_count=1,
        execution_error="Qdrant connection timeout",
    )
    assert res_err.status == EvaluationStatus.ERROR
    assert res_err.status != EvaluationStatus.PASS

    # 3. Failed citation check -> FAIL
    failed_output = {
        "generated_answer": "AI engineering is software engineering for AI.",
        "verified_citations": [],  # missing citations on answerable question
        "retrieved_chunks": [],
        "insufficient_evidence": False,
    }
    res_failed = RAGEvaluator.evaluate_question(
        q_straight,
        available_doc_count=1,
        pipeline_output=failed_output,
    )
    assert res_failed.status == EvaluationStatus.FAIL
    assert res_failed.status != EvaluationStatus.PASS


def test_evaluator_question_pass_grounded():
    """Verify that a properly grounded answer with citations passes."""
    q = EvaluationQuestion(
        id="Q001",
        category=QuestionCategory.STRAIGHTFORWARD,
        question="What is AI engineering?",
        answerable_from_source=True,
        evaluation_mode=EvaluationMode.GROUNDED_ANSWER,
        expected_behavior="Answer from source.",
    )

    good_output = {
        "generated_answer": "AI engineering is the discipline of building software applications with foundation models.",
        "verified_citations": [
            {
                "document_id": "doc-uuid",
                "filename": "AI Engineering.pdf",
                "page_number": 2,
                "relevance_score": 0.88,
                "text_excerpt": "AI engineering is the process of building applications with readily available foundation models.",
            }
        ],
        "retrieved_chunks": [
            {
                "id": "chunk-1",
                "document_id": "doc-uuid",
                "page_number": 2,
                "score": 0.88,
                "text": "author Chip Huyen discusses AI engineering: the process of building applications with readily available foundation models.",
            }
        ],
        "insufficient_evidence": False,
        "is_grounded": True,
    }

    result = RAGEvaluator.evaluate_question(
        question=q,
        available_doc_count=1,
        pipeline_output=good_output,
        latency_ms=1250.0,
    )

    assert result.status == EvaluationStatus.PASS
    assert result.scores.overall >= 0.70
    assert result.scores.abstention_accuracy == 1.0
    assert result.scores.citation_precision == 1.0


# ============================================================================
# 4. Summary Aggregation and CLI Tests
# ============================================================================

def test_aggregate_summaries_calculation():
    """Verify summary calculations and category aggregation."""
    q1 = EvaluationQuestion(
        id="Q001", category=QuestionCategory.STRAIGHTFORWARD, question="What is AI engineering?",
        answerable_from_source=True, evaluation_mode=EvaluationMode.GROUNDED_ANSWER, expected_behavior="B1"
    )
    q2 = EvaluationQuestion(
        id="Q021", category=QuestionCategory.MULTI_DOCUMENT, question="Explain multi-document agent design.",
        answerable_from_source=True, evaluation_mode=EvaluationMode.GROUNDED_ANSWER, expected_behavior="B2",
        requires_multiple_documents=True
    )
    q3 = EvaluationQuestion(
        id="Q056", category=QuestionCategory.UNANSWERABLE, question="What was the book sales volume in 2025?",
        answerable_from_source=False, evaluation_mode=EvaluationMode.ABSTAIN_IF_NOT_IN_SOURCES, expected_behavior="B3"
    )

    res1 = RAGEvaluator.evaluate_question(
        q1, 1,
        pipeline_output={
            "generated_answer": "AI engineering is the discipline of building software applications with foundation models.",
            "verified_citations": [{"page_number": 2, "text_excerpt": "AI engineering is the discipline of building applications with foundation models."}],
            "retrieved_chunks": [{"page_number": 2, "text": "AI engineering is the discipline of building applications with foundation models."}],
            "is_grounded": True,
        }
    )
    res2 = RAGEvaluator.evaluate_question(q2, 1)  # blocked
    res3 = RAGEvaluator.evaluate_question(
        q3, 1,
        pipeline_output={
            "generated_answer": "I couldn't find sufficient supporting information in your uploaded documents.",
            "verified_citations": [],
            "retrieved_chunks": [],
            "insufficient_evidence": True,
        }
    )

    global_sum, cat_sums = aggregate_summaries([res1, res2, res3], total_dataset_questions=3)

    assert global_sum.total_questions == 3
    assert global_sum.passed == 2
    assert global_sum.blocked == 1
    assert global_sum.failed == 0
    assert global_sum.overall_pass_rate == round(2 / 3, 3)

    assert "straightforward" in cat_sums
    assert cat_sums["straightforward"].passed == 1
    assert cat_sums["multi_document"].blocked == 1
    assert cat_sums["unanswerable"].passed == 1


def test_cli_parser():
    """Verify CLI argument parser configuration."""
    parser = build_parser()
    args = parser.parse_args(["--category", "straightforward", "--limit", "5", "--delay", "0.2"])
    assert args.category == "straightforward"
    assert args.limit == 5
    assert args.delay == 0.2


@pytest.mark.asyncio
async def test_run_benchmark_subset_execution():
    """
    Smoke test running the benchmark against a small subset (e.g. multi_document test).
    Verifies full end-to-end flow without excessive LLM calls.
    """
    report = await run_benchmark(
        category=QuestionCategory.MULTI_DOCUMENT,
        limit=2,
    )

    assert report is not None
    assert len(report.questions) == 2
    if report.metadata.get("available_doc_count", 0) < 2:
        assert report.summary.blocked == 2
        assert all(q.status == EvaluationStatus.BLOCKED for q in report.questions)
    else:
        # When >= 2 documents are present in notebook, multi-document questions execute
        assert report.summary.passed + report.summary.failed == 2
        assert report.summary.blocked == 0
