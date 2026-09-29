"""
Evaluation API router.
Implements POST /notebooks/{id}/evals to benchmark citation validity and refusal accuracy.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.evaluations.eval_service import EvaluationRunner
from app.models.models import Notebook

router = APIRouter(tags=["Evaluations"])


class EvalRunRequest(BaseModel):
    custom_cases: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Optional custom list of test cases with question, is_answerable, and expected_keywords",
    )


@router.post(
    "/notebooks/{notebook_id}/evals",
    summary="Run golden-set evaluation on a notebook's indexed documents",
)
async def run_notebook_evals(
    notebook_id: UUID,
    payload: Optional[EvalRunRequest] = None,
    db: AsyncSession = Depends(get_db),
):
    notebook = await db.get(Notebook, notebook_id)
    if notebook is None:
        raise HTTPException(status_code=404, detail="Notebook not found")

    custom_cases = payload.custom_cases if payload else None
    runner = EvaluationRunner(db)
    return await runner.run_evaluation(notebook_id=notebook_id, custom_cases=custom_cases)
