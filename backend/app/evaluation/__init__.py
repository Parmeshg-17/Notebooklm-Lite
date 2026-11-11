"""
Evaluation module for NotebookLM Lite.
Provides automated benchmark execution, dataset validation, fine-grained metrics,
and reporting for RAG quality assurance.
"""

from app.evaluation.dataset_loader import (
    DEFAULT_DATASET_PATHS,
    filter_questions,
    load_evaluation_dataset,
    resolve_dataset_path,
)
from app.evaluation.evaluator import RAGEvaluator
from app.evaluation.metrics import RAGEvaluationMetrics
from app.evaluation.runner import (
    aggregate_summaries,
    execute_question_pipeline,
    resolve_benchmark_notebook,
    run_benchmark,
)
from app.evaluation.schemas import (
    CategoryEvaluationSummary,
    ChunkResult,
    CitationResult,
    EvaluationDataset,
    EvaluationMode,
    EvaluationQuestion,
    EvaluationReport,
    EvaluationStatus,
    EvaluationSummary,
    MetricScores,
    QuestionCategory,
    QuestionEvaluationResult,
)

__all__ = [
    "QuestionCategory",
    "EvaluationMode",
    "EvaluationStatus",
    "EvaluationQuestion",
    "EvaluationDataset",
    "CitationResult",
    "ChunkResult",
    "MetricScores",
    "QuestionEvaluationResult",
    "CategoryEvaluationSummary",
    "EvaluationSummary",
    "EvaluationReport",
    "resolve_dataset_path",
    "load_evaluation_dataset",
    "filter_questions",
    "RAGEvaluationMetrics",
    "RAGEvaluator",
    "resolve_benchmark_notebook",
    "aggregate_summaries",
    "execute_question_pipeline",
    "run_benchmark",
    "DEFAULT_DATASET_PATHS",
]

