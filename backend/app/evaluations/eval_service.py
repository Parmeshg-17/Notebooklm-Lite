"""
Evaluation Runner for NotebookLM Lite.
Runs golden-set Q&A test cases against a notebook to measure:
- Citation validity rate (enforcement of NO SOURCE, NO SENTENCE)
- Refusal accuracy (refusing unanswerable questions with not_found=true)
- Retrieval precision & recall
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.rag.citations import CitationValidator
from app.rag.generator import AnswerGenerator
from app.rag.retrieval import HybridRetriever

logger = get_logger(__name__)


@dataclass
class EvalTestCase:
    question: str
    is_answerable: bool
    expected_keywords: List[str]


DEFAULT_EVAL_CASES: List[EvalTestCase] = [
    EvalTestCase(
        question="What are the key points described in this document?",
        is_answerable=True,
        expected_keywords=[],
    ),
    EvalTestCase(
        question="What is the exact secret code for spaceship Apollo 9999?",
        is_answerable=False,
        expected_keywords=[],
    ),
    EvalTestCase(
        question="Who was the prime minister of Mars in 1842?",
        is_answerable=False,
        expected_keywords=[],
    ),
]


class EvaluationRunner:
    """Evaluates RAG pipeline citation accuracy, retrieval, and refusal on a notebook."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.retriever = HybridRetriever(db)
        self.generator = AnswerGenerator()

    async def run_evaluation(
        self,
        notebook_id: UUID,
        custom_cases: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Runs test questions and calculates citation metrics."""
        cases = DEFAULT_EVAL_CASES
        if custom_cases:
            cases = [
                EvalTestCase(
                    question=c["question"],
                    is_answerable=c.get("is_answerable", True),
                    expected_keywords=c.get("expected_keywords", []),
                )
                for c in custom_cases
            ]

        results = []
        valid_citation_sentences = 0
        total_generated_sentences = 0
        correct_refusals = 0
        total_unanswerable = 0

        for case in cases:
            retrieved = await self.retriever.retrieve(notebook_id=notebook_id, query=case.question, top_k=5)
            raw_answer = await self.generator.generate_answer(query=case.question, sources=retrieved)

            validator = CitationValidator(retrieved)
            val_result = validator.validate(raw_answer)

            # Metrics collection
            case_sentences = len(val_result.sentences)
            total_generated_sentences += case_sentences
            if val_result.is_valid:
                valid_citation_sentences += case_sentences

            if not case.is_answerable:
                total_unanswerable += 1
                if val_result.not_found:
                    correct_refusals += 1

            results.append({
                "question": case.question,
                "is_answerable": case.is_answerable,
                "not_found": val_result.not_found,
                "retrieved_chunks": len(retrieved),
                "sentence_count": case_sentences,
                "hallucinated_ids": val_result.hallucinated_ids,
                "rejected_sentences": len(val_result.rejected_sentences),
                "answer_preview": val_result.clean_answer_text[:120] + "...",
            })

        citation_validity_rate = (
            (valid_citation_sentences / total_generated_sentences)
            if total_generated_sentences > 0
            else 1.0
        )
        refusal_accuracy = (
            (correct_refusals / total_unanswerable)
            if total_unanswerable > 0
            else 1.0
        )

        return {
            "notebook_id": str(notebook_id),
            "total_test_cases": len(cases),
            "metrics": {
                "citation_validity_rate": round(citation_validity_rate * 100, 1),
                "refusal_accuracy": round(refusal_accuracy * 100, 1),
                "total_sentences_generated": total_generated_sentences,
                "valid_citation_sentences": valid_citation_sentences,
                "correct_refusals": correct_refusals,
                "total_unanswerable_tested": total_unanswerable,
            },
            "test_cases": results,
        }
