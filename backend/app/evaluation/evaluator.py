"""
RAG Evaluator for individual test cases.
Enforces strict PASS / FAIL / BLOCKED / ERROR determination, multi-document preconditions,
and score aggregation per test question.
"""

import logging
from typing import Any, Dict, List, Optional

from app.evaluation.metrics import RAGEvaluationMetrics
from app.evaluation.schemas import (
    ChunkResult,
    CitationResult,
    EvaluationQuestion,
    EvaluationStatus,
    MetricScores,
    QuestionCategory,
    QuestionEvaluationResult,
)

logger = logging.getLogger("app.evaluation.evaluator")


class RAGEvaluator:
    """
    Evaluator that validates pipeline responses against benchmark criteria.
    """

    @staticmethod
    def evaluate_question(
        question: EvaluationQuestion,
        available_doc_count: int,
        pipeline_output: Optional[Dict[str, Any]] = None,
        latency_ms: float = 0.0,
        token_usage: Optional[Dict[str, int]] = None,
        execution_error: Optional[str] = None,
    ) -> QuestionEvaluationResult:
        """
        Evaluates a single benchmark question response.
        Enforces:
        - Multi-document tests BLOCKED when available_doc_count < 2.
        - Strict PASS / FAIL determination.
        - Never treating unexecuted or failed questions as PASS.
        """
        # 1. Check multi-document precondition (Requirement 6)
        is_multi_doc = (
            question.category == QuestionCategory.MULTI_DOCUMENT
            or question.requires_multiple_documents is True
        )
        if is_multi_doc and available_doc_count < 2:
            reason = (
                f"BLOCKED: Question requires multiple documents, but only {available_doc_count} "
                f"document is available in notebook."
            )
            logger.info(f"Question {question.id} marked as BLOCKED: {reason}")
            return QuestionEvaluationResult(
                id=question.id,
                category=question.category.value,
                question=question.question,
                answerable_from_source=question.answerable_from_source,
                status=EvaluationStatus.BLOCKED,
                latency_ms=0.0,
                token_usage=None,
                generated_answer=None,
                citations=[],
                retrieved_chunks=[],
                retrieved_chunk_count=0,
                scores=MetricScores(),
                reason=reason,
            )

        # 2. Check execution error
        if execution_error:
            logger.warning(f"Question {question.id} encountered execution error: {execution_error}")
            return QuestionEvaluationResult(
                id=question.id,
                category=question.category.value,
                question=question.question,
                answerable_from_source=question.answerable_from_source,
                status=EvaluationStatus.ERROR,
                latency_ms=latency_ms,
                token_usage=token_usage,
                generated_answer=None,
                citations=[],
                retrieved_chunks=[],
                retrieved_chunk_count=0,
                scores=MetricScores(),
                reason=f"Execution error: {execution_error}",
            )

        if not pipeline_output:
            return QuestionEvaluationResult(
                id=question.id,
                category=question.category.value,
                question=question.question,
                answerable_from_source=question.answerable_from_source,
                status=EvaluationStatus.FAIL,
                latency_ms=latency_ms,
                token_usage=token_usage,
                generated_answer=None,
                citations=[],
                retrieved_chunks=[],
                retrieved_chunk_count=0,
                scores=MetricScores(),
                reason="Pipeline produced no output",
            )

        # 3. Extract output components
        answer = pipeline_output.get("generated_answer") or pipeline_output.get("answer") or ""
        raw_citations = pipeline_output.get("verified_citations") or pipeline_output.get("citations") or []
        raw_chunks = (
            pipeline_output.get("retrieved_chunks")
            or pipeline_output.get("evidence_chunks")
            or pipeline_output.get("chunks")
            or []
        )
        insufficient_evidence = pipeline_output.get("insufficient_evidence")
        is_grounded = pipeline_output.get("is_grounded")

        # Map to structured result models
        citations: List[CitationResult] = []
        for c in raw_citations:
            citations.append(
                CitationResult(
                    document_id=c.get("document_id"),
                    filename=c.get("filename"),
                    page_number=c.get("page_number"),
                    relevance_score=c.get("relevance_score") or c.get("score"),
                    text_excerpt=c.get("text_excerpt") or c.get("snippet"),
                )
            )

        chunks: List[ChunkResult] = []
        for ch in raw_chunks:
            chunks.append(
                ChunkResult(
                    chunk_id=ch.get("chunk_id") or ch.get("id"),
                    document_id=ch.get("document_id"),
                    page_number=ch.get("page_number"),
                    score=ch.get("score"),
                    text_snippet=(ch.get("text", "") or ch.get("text_snippet", ""))[:200],
                )
            )

        # 4. Calculate fine-grained metrics
        metric_dict = RAGEvaluationMetrics.compute_all_metrics(
            question=question.question,
            answer=answer,
            citations=[c.model_dump() for c in citations],
            retrieved_chunks=[ch.model_dump() for ch in chunks],
            answerable_from_source=question.answerable_from_source,
            page_hint_printed=question.page_hint_printed,
            insufficient_evidence=insufficient_evidence,
            is_grounded=is_grounded,
        )
        scores = MetricScores(**metric_dict)

        # 5. Determine PASS / FAIL status strictly (Requirement 7)
        status = EvaluationStatus.FAIL
        failure_reasons = []

        if not question.answerable_from_source:
            # Unanswerable query criteria:
            if scores.abstention_accuracy < 1.0:
                failure_reasons.append("Failed to abstain on unanswerable query")
            if scores.citation_precision < 1.0:
                failure_reasons.append(f"Produced citations ({len(citations)}) for unanswerable query")
            if not failure_reasons and scores.overall >= 0.70:
                status = EvaluationStatus.PASS
        else:
            # Answerable query criteria:
            if scores.abstention_accuracy < 1.0:
                failure_reasons.append("Falsely abstained on answerable query")
            if scores.answer_relevance < 0.50:
                failure_reasons.append(f"Low answer relevance ({scores.answer_relevance:.2f})")
            if scores.citation_precision < 0.50:
                failure_reasons.append(f"Low citation precision ({scores.citation_precision:.2f})")
            if scores.claim_grounding < 0.50:
                failure_reasons.append(f"Low claim grounding ({scores.claim_grounding:.2f})")
            if question.page_hint_printed and scores.citation_page_accuracy < 1.0:
                failure_reasons.append(
                    f"Cited/retrieved pages did not match page hint '{question.page_hint_printed}'"
                )

            if not failure_reasons and scores.overall >= 0.60:
                status = EvaluationStatus.PASS

        reason = "; ".join(failure_reasons) if failure_reasons else None

        return QuestionEvaluationResult(
            id=question.id,
            category=question.category.value,
            question=question.question,
            answerable_from_source=question.answerable_from_source,
            status=status,
            latency_ms=latency_ms,
            token_usage=token_usage,
            generated_answer=answer,
            citations=citations,
            retrieved_chunks=chunks,
            retrieved_chunk_count=len(chunks),
            scores=scores,
            reason=reason,
        )

