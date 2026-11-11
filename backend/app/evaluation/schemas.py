"""
Data models and validation schemas for the NotebookLM Lite RAG Evaluation Harness.
Covers the 70-question benchmark dataset schema, execution outputs,
fine-grained metric scores, category summaries, and full evaluation reports.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class QuestionCategory(str, Enum):
    STRAIGHTFORWARD = "straightforward"
    MULTI_DOCUMENT = "multi_document"
    COMPARISON = "comparison"
    PAGE_SPECIFIC = "page_specific"
    UNANSWERABLE = "unanswerable"


class EvaluationMode(str, Enum):
    GROUNDED_ANSWER = "grounded_answer"
    ABSTAIN_IF_NOT_IN_SOURCES = "abstain_if_not_in_sources"


class EvaluationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"


class EvaluationQuestion(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(..., description="Unique question identifier, e.g., Q001")
    category: QuestionCategory = Field(..., description="Question classification category")
    question: str = Field(..., min_length=3, description="The user query or prompt")
    answerable_from_source: bool = Field(..., description="Whether source document contains the answer")
    evaluation_mode: EvaluationMode = Field(..., description="Expected evaluation mode")
    expected_behavior: str = Field(..., description="Human-readable expectation specification")
    requires_multiple_documents: Optional[bool] = Field(
        default=False, description="True if answering requires synthesizing >= 2 documents"
    )
    page_hint_printed: Optional[str] = Field(
        default=None, description="Printed book page or range hint (e.g. '256' or '218-220')"
    )


class EvaluationDataset(BaseModel):
    model_config = ConfigDict(extra="ignore")

    dataset_name: str = Field(..., description="Name of the benchmark dataset")
    dataset_version: str = Field(..., description="Version of the benchmark dataset")
    source_documents: List[str] = Field(..., description="Target source documents, e.g. AI Engineering.pdf")
    source_scope: Optional[str] = Field(default=None, description="Document coverage description")
    total_questions: int = Field(..., ge=1, description="Declared total question count")
    category_counts: Dict[str, int] = Field(..., description="Counts per category declared in header")
    schema_notes: Optional[Dict[str, str]] = Field(default=None, description="Evaluation schema instructions")
    questions: List[EvaluationQuestion] = Field(..., description="List of validated questions")

    @field_validator("questions")
    @classmethod
    def validate_question_count(cls, v: List[EvaluationQuestion], info) -> List[EvaluationQuestion]:
        declared = info.data.get("total_questions")
        if declared is not None and len(v) != declared:
            raise ValueError(
                f"Question count mismatch: declared total_questions={declared}, but questions list contains {len(v)}"
            )
        return v


class CitationResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    document_id: Optional[str] = None
    filename: Optional[str] = None
    page_number: Optional[int] = None
    relevance_score: Optional[float] = None
    text_excerpt: Optional[str] = None


class ChunkResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    chunk_id: Optional[str] = None
    document_id: Optional[str] = None
    page_number: Optional[int] = None
    score: Optional[float] = None
    text_snippet: Optional[str] = None


class MetricScores(BaseModel):
    model_config = ConfigDict(extra="ignore")

    answer_relevance: float = Field(0.0, ge=0.0, le=1.0)
    retrieval_relevance: float = Field(0.0, ge=0.0, le=1.0)
    citation_precision: float = Field(0.0, ge=0.0, le=1.0)
    citation_page_accuracy: float = Field(0.0, ge=0.0, le=1.0)
    claim_grounding: float = Field(0.0, ge=0.0, le=1.0)
    abstention_accuracy: float = Field(0.0, ge=0.0, le=1.0)
    overall: float = Field(0.0, ge=0.0, le=1.0)


class QuestionEvaluationResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    category: str
    question: str
    answerable_from_source: bool
    status: EvaluationStatus
    latency_ms: float = 0.0
    token_usage: Optional[Dict[str, int]] = None
    generated_answer: Optional[str] = None
    citations: List[CitationResult] = Field(default_factory=list)
    retrieved_chunks: List[ChunkResult] = Field(default_factory=list)
    retrieved_chunk_count: int = 0
    scores: MetricScores = Field(default_factory=MetricScores)
    reason: Optional[str] = None


class CategoryEvaluationSummary(BaseModel):
    model_config = ConfigDict(extra="ignore")

    category: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    blocked: int = 0
    errors: int = 0
    pass_rate: float = 0.0
    mean_latency_ms: float = 0.0
    mean_answer_relevance: float = 0.0
    mean_retrieval_relevance: float = 0.0
    mean_citation_precision: float = 0.0
    mean_citation_page_accuracy: float = 0.0
    mean_claim_grounding: float = 0.0
    mean_abstention_accuracy: float = 0.0


class EvaluationSummary(BaseModel):
    model_config = ConfigDict(extra="ignore")

    total_questions: int = 0
    passed: int = 0
    failed: int = 0
    blocked: int = 0
    errors: int = 0
    overall_pass_rate: float = 0.0
    mean_latency_ms: float = 0.0
    mean_answer_relevance: float = 0.0
    mean_retrieval_relevance: float = 0.0
    mean_citation_precision: float = 0.0
    mean_citation_page_accuracy: float = 0.0
    mean_claim_grounding: float = 0.0
    mean_abstention_accuracy: float = 0.0


class EvaluationReport(BaseModel):
    model_config = ConfigDict(extra="ignore")

    metadata: Dict[str, Any]
    summary: EvaluationSummary
    category_scores: Dict[str, CategoryEvaluationSummary]
    questions: List[QuestionEvaluationResult]

