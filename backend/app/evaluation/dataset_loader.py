"""
Dataset loader and validator for the NotebookLM Lite 70-question benchmark dataset.
Enforces Pydantic schema validation, category counts, and field constraints.
"""

import json
import logging
from pathlib import Path
from typing import List, Optional, Union

from pydantic import ValidationError

from app.evaluation.schemas import EvaluationDataset, EvaluationQuestion, QuestionCategory

logger = logging.getLogger("app.evaluation.loader")

# Candidate default paths relative to backend or workspace root
DEFAULT_DATASET_PATHS = [
    Path("notebooklm_lite_rag_evaluation_dataset.json"),
    Path("notebooklm_lite_rag_evaluation_dataset (1).json"),
    Path("../notebooklm_lite_rag_evaluation_dataset.json"),
    Path("../notebooklm_lite_rag_evaluation_dataset (1).json"),
    Path("app/evaluation/data/notebooklm_lite_rag_evaluation_dataset.json"),
]


def resolve_dataset_path(custom_path: Optional[Union[str, Path]] = None) -> Path:
    """
    Resolves the dataset file path, verifying existence.
    """
    if custom_path:
        p = Path(custom_path).resolve()
        if p.exists() and p.is_file():
            return p
        raise FileNotFoundError(f"Specified evaluation dataset not found: {custom_path}")

    # Search candidates
    for candidate in DEFAULT_DATASET_PATHS:
        resolved = candidate.resolve()
        if resolved.exists() and resolved.is_file():
            return resolved

    raise FileNotFoundError(
        "Could not automatically locate 'notebooklm_lite_rag_evaluation_dataset.json'. "
        "Please provide the path via the --dataset argument."
    )


def load_evaluation_dataset(dataset_path: Optional[Union[str, Path]] = None) -> EvaluationDataset:
    """
    Loads, parses, and validates the 70-question JSON evaluation dataset against
    the Pydantic EvaluationDataset schema.
    """
    path = resolve_dataset_path(dataset_path)
    logger.info(f"Loading evaluation dataset from: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Evaluation dataset at {path} is not valid JSON: {e}") from e

    try:
        dataset = EvaluationDataset.model_validate(raw_data)
    except ValidationError as e:
        logger.error(f"Evaluation dataset validation failed: {e}")
        raise ValueError(f"Evaluation dataset failed schema validation: {e}") from e

    # Cross-check category counts against declared counts
    actual_counts = {}
    for q in dataset.questions:
        cat_key = q.category.value
        actual_counts[cat_key] = actual_counts.get(cat_key, 0) + 1

    for cat_name, expected_count in dataset.category_counts.items():
        actual_count = actual_counts.get(cat_name, 0)
        if actual_count != expected_count:
            logger.warning(
                f"Category '{cat_name}' has count mismatch: declared={expected_count}, actual={actual_count}"
            )

    logger.info(
        f"Successfully loaded and validated dataset '{dataset.dataset_name}' v{dataset.dataset_version} "
        f"with {len(dataset.questions)} questions."
    )
    return dataset


def filter_questions(
    dataset: EvaluationDataset,
    category: Optional[Union[str, QuestionCategory]] = None,
    limit: Optional[int] = None,
) -> List[EvaluationQuestion]:
    """
    Filters questions from the dataset by category and/or limit.
    """
    questions = dataset.questions

    if category:
        target_cat = category.value if isinstance(category, QuestionCategory) else str(category).lower()
        questions = [q for q in questions if q.category.value == target_cat]

    if limit is not None and limit > 0:
        questions = questions[:limit]

    return questions

