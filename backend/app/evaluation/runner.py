"""
RAG Benchmark Runner for NotebookLM Lite.
Executes the evaluation dataset against the active LangGraph + MCP + Qdrant pipeline,
records outputs and telemetry, computes category scores, and exports comprehensive JSON reports.
"""

import asyncio
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import sqlite3
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import uuid

from app.agents.graph import agent_graph
from app.evaluation.dataset_loader import filter_questions, load_evaluation_dataset
from app.evaluation.evaluator import RAGEvaluator
from app.evaluation.schemas import (
    CategoryEvaluationSummary,
    EvaluationDataset,
    EvaluationQuestion,
    EvaluationReport,
    EvaluationStatus,
    EvaluationSummary,
    QuestionCategory,
    QuestionEvaluationResult,
)

logger = logging.getLogger("app.evaluation.runner")


def resolve_benchmark_notebook(
    custom_notebook_id: Optional[str] = None,
    db_path: str = "backend/notebooklm.db",
) -> Tuple[str, str, int]:
    """
    Resolves the benchmark notebook UUID, owner UUID, and count of indexed documents.
    If no notebook_id is provided, automatically finds the notebook containing 'AI Engineering.pdf'.
    """
    if not os.path.exists(db_path) and os.path.exists("notebooklm.db"):
        db_path = "notebooklm.db"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        if custom_notebook_id:
            raw_id = custom_notebook_id.replace("-", "").lower()
            row = cursor.execute(
                "SELECT n.id, n.owner_id, "
                "(SELECT COUNT(d.id) FROM documents d WHERE d.notebook_id = n.id AND d.processing_status = 'INDEXED') "
                "FROM notebooks n WHERE n.id = ? OR n.id = ?",
                (raw_id, custom_notebook_id),
            ).fetchone()
            if not row:
                raise ValueError(f"Notebook with ID '{custom_notebook_id}' not found in database.")
            nb_uuid = str(uuid.UUID(hex=row[0])) if len(row[0]) == 32 else str(row[0])
            owner_uuid = str(uuid.UUID(hex=row[1])) if len(row[1]) == 32 else str(row[1])
            doc_count = int(row[2])
            return nb_uuid, owner_uuid, doc_count

        # Auto-detect notebook containing AI Engineering.pdf
        row = cursor.execute(
            "SELECT n.id, n.owner_id, "
            "(SELECT COUNT(d.id) FROM documents d WHERE d.notebook_id = n.id AND d.processing_status = 'INDEXED') "
            "FROM notebooks n "
            "JOIN documents doc ON doc.notebook_id = n.id "
            "WHERE doc.filename LIKE '%AI Engineering%' AND doc.processing_status = 'INDEXED' "
            "ORDER BY (SELECT COUNT(d2.id) FROM documents d2 WHERE d2.notebook_id = n.id AND d2.processing_status = 'INDEXED') DESC, n.created_at DESC LIMIT 1"
        ).fetchone()

        if row:
            nb_uuid = str(uuid.UUID(hex=row[0])) if len(row[0]) == 32 else str(row[0])
            owner_uuid = str(uuid.UUID(hex=row[1])) if len(row[1]) == 32 else str(row[1])
            doc_count = int(row[2])
            return nb_uuid, owner_uuid, doc_count

        # Fallback to any notebook if AI Engineering is not specifically marked
        fallback = cursor.execute(
            "SELECT n.id, n.owner_id, "
            "(SELECT COUNT(d.id) FROM documents d WHERE d.notebook_id = n.id AND d.processing_status = 'INDEXED') "
            "FROM notebooks n ORDER BY n.created_at DESC LIMIT 1"
        ).fetchone()

        if fallback:
            nb_uuid = str(uuid.UUID(hex=fallback[0])) if len(fallback[0]) == 32 else str(fallback[0])
            owner_uuid = str(uuid.UUID(hex=fallback[1])) if len(fallback[1]) == 32 else str(fallback[1])
            doc_count = int(fallback[2])
            return nb_uuid, owner_uuid, doc_count

        # Default fallback demo IDs if database is completely empty
        return "438c1105-030b-42ed-84ff-5fd4ea7284ba", "c5ee3cf6-441c-4d30-87a7-24954a0397a8", 1

    finally:
        conn.close()


def aggregate_summaries(
    results: List[QuestionEvaluationResult],
    total_dataset_questions: int,
) -> Tuple[EvaluationSummary, Dict[str, CategoryEvaluationSummary]]:
    """
    Computes overall summary and category-level summaries from question evaluation results.
    """
    category_buckets: Dict[str, List[QuestionEvaluationResult]] = {}
    for r in results:
        category_buckets.setdefault(r.category, []).append(r)

    category_summaries: Dict[str, CategoryEvaluationSummary] = {}
    for cat_name, items in category_buckets.items():
        total = len(items)
        passed = sum(1 for x in items if x.status == EvaluationStatus.PASS)
        failed = sum(1 for x in items if x.status == EvaluationStatus.FAIL)
        blocked = sum(1 for x in items if x.status == EvaluationStatus.BLOCKED)
        errors = sum(1 for x in items if x.status == EvaluationStatus.ERROR)

        pass_rate = round(passed / total, 3) if total > 0 else 0.0

        # Mean scores across items that were executed or relevant
        executed = [x for x in items if x.status in (EvaluationStatus.PASS, EvaluationStatus.FAIL)]
        scored_items = executed if executed else items

        mean_latency = (
            round(sum(x.latency_ms for x in executed) / len(executed), 1) if executed else 0.0
        )
        mean_ans_rel = (
            round(sum(x.scores.answer_relevance for x in scored_items) / len(scored_items), 3)
            if scored_items
            else 0.0
        )
        mean_ret_rel = (
            round(sum(x.scores.retrieval_relevance for x in scored_items) / len(scored_items), 3)
            if scored_items
            else 0.0
        )
        mean_cit_prec = (
            round(sum(x.scores.citation_precision for x in scored_items) / len(scored_items), 3)
            if scored_items
            else 0.0
        )
        mean_cit_page = (
            round(sum(x.scores.citation_page_accuracy for x in scored_items) / len(scored_items), 3)
            if scored_items
            else 0.0
        )
        mean_claim_grd = (
            round(sum(x.scores.claim_grounding for x in scored_items) / len(scored_items), 3)
            if scored_items
            else 0.0
        )
        mean_abst_acc = (
            round(sum(x.scores.abstention_accuracy for x in scored_items) / len(scored_items), 3)
            if scored_items
            else 0.0
        )

        category_summaries[cat_name] = CategoryEvaluationSummary(
            category=cat_name,
            total=total,
            passed=passed,
            failed=failed,
            blocked=blocked,
            errors=errors,
            pass_rate=pass_rate,
            mean_latency_ms=mean_latency,
            mean_answer_relevance=mean_ans_rel,
            mean_retrieval_relevance=mean_ret_rel,
            mean_citation_precision=mean_cit_prec,
            mean_citation_page_accuracy=mean_cit_page,
            mean_claim_grounding=mean_claim_grd,
            mean_abstention_accuracy=mean_abst_acc,
        )

    # Global summary
    total_evaluated = len(results)
    global_passed = sum(1 for x in results if x.status == EvaluationStatus.PASS)
    global_failed = sum(1 for x in results if x.status == EvaluationStatus.FAIL)
    global_blocked = sum(1 for x in results if x.status == EvaluationStatus.BLOCKED)
    global_errors = sum(1 for x in results if x.status == EvaluationStatus.ERROR)

    overall_pass_rate = round(global_passed / total_evaluated, 3) if total_evaluated > 0 else 0.0

    executed_all = [x for x in results if x.status in (EvaluationStatus.PASS, EvaluationStatus.FAIL)]
    scored_all = executed_all if executed_all else results

    global_summary = EvaluationSummary(
        total_questions=total_evaluated,
        passed=global_passed,
        failed=global_failed,
        blocked=global_blocked,
        errors=global_errors,
        overall_pass_rate=overall_pass_rate,
        mean_latency_ms=(
            round(sum(x.latency_ms for x in executed_all) / len(executed_all), 1)
            if executed_all
            else 0.0
        ),
        mean_answer_relevance=(
            round(sum(x.scores.answer_relevance for x in scored_all) / len(scored_all), 3)
            if scored_all
            else 0.0
        ),
        mean_retrieval_relevance=(
            round(sum(x.scores.retrieval_relevance for x in scored_all) / len(scored_all), 3)
            if scored_all
            else 0.0
        ),
        mean_citation_precision=(
            round(sum(x.scores.citation_precision for x in scored_all) / len(scored_all), 3)
            if scored_all
            else 0.0
        ),
        mean_citation_page_accuracy=(
            round(sum(x.scores.citation_page_accuracy for x in scored_all) / len(scored_all), 3)
            if scored_all
            else 0.0
        ),
        mean_claim_grounding=(
            round(sum(x.scores.claim_grounding for x in scored_all) / len(scored_all), 3)
            if scored_all
            else 0.0
        ),
        mean_abstention_accuracy=(
            round(sum(x.scores.abstention_accuracy for x in scored_all) / len(scored_all), 3)
            if scored_all
            else 0.0
        ),
    )

    return global_summary, category_summaries


async def execute_question_pipeline(
    question: EvaluationQuestion,
    notebook_id: str,
    user_id: str,
) -> Tuple[Optional[Dict[str, Any]], float, Optional[Dict[str, int]], Optional[str]]:
    """
    Executes a single question against the existing LangGraph Agent workflow.
    Captures answer, citations, retrieved chunks, latency, and telemetry.
    """
    conversation_id = str(uuid.uuid4())
    initial_state = {
        "question": question.question,
        "original_query": question.question,
        "notebook_id": notebook_id,
        "user_id": user_id,
        "document_ids": None,
        "conversation_id": conversation_id,
    }
    config = {"configurable": {"thread_id": conversation_id}}

    t0 = time.perf_counter()
    try:
        agent_result = await agent_graph.ainvoke(initial_state, config=config)
        latency_ms = round((time.perf_counter() - t0) * 1000, 1)

        token_usage = None
        telemetry = agent_result.get("telemetry") or {}
        if "tokens" in telemetry:
            token_usage = telemetry["tokens"]
        elif agent_result.get("generated_answer"):
            # Estimate tokens if not directly available (approx 4 chars per token)
            token_usage = {
                "prompt_tokens": len(question.question) // 4,
                "completion_tokens": len(agent_result.get("generated_answer", "")) // 4,
                "total_tokens": (
                    len(question.question) + len(agent_result.get("generated_answer", ""))
                )
                // 4,
            }

        return agent_result, latency_ms, token_usage, None

    except Exception as exc:
        latency_ms = round((time.perf_counter() - t0) * 1000, 1)
        logger.exception(f"Error executing question {question.id}: {exc}")
        return None, latency_ms, None, str(exc)


async def run_benchmark(
    dataset_path: Optional[Union[str, Path]] = None,
    notebook_id: Optional[str] = None,
    category: Optional[Union[str, QuestionCategory]] = None,
    limit: Optional[int] = None,
    output_path: Optional[Union[str, Path]] = None,
    rate_limit_delay_seconds: float = 0.5,
) -> EvaluationReport:
    """
    Executes the benchmark across the dataset questions and produces an EvaluationReport.
    """
    # 1. Load dataset
    dataset = load_evaluation_dataset(dataset_path)
    questions = filter_questions(dataset, category=category, limit=limit)

    # 2. Resolve notebook and document count
    resolved_nb, resolved_owner, available_doc_count = resolve_benchmark_notebook(notebook_id)
    logger.info(
        f"Target Notebook: {resolved_nb} (Owner: {resolved_owner}, Indexed Documents: {available_doc_count})"
    )

    results: List[QuestionEvaluationResult] = []
    total = len(questions)

    for idx, q in enumerate(questions, start=1):
        logger.info(f"[{idx}/{total}] Evaluating {q.id} ({q.category.value}): '{q.question[:60]}...'")

        # Precondition check: if multi-document and doc_count < 2, mark BLOCKED immediately
        is_multi_doc = (
            q.category == QuestionCategory.MULTI_DOCUMENT or q.requires_multiple_documents is True
        )
        if is_multi_doc and available_doc_count < 2:
            res = RAGEvaluator.evaluate_question(
                question=q,
                available_doc_count=available_doc_count,
            )
            results.append(res)
            continue

        # Execute pipeline
        pipeline_output, latency_ms, token_usage, error = await execute_question_pipeline(
            question=q,
            notebook_id=resolved_nb,
            user_id=resolved_owner,
        )

        # Evaluate question result
        res = RAGEvaluator.evaluate_question(
            question=q,
            available_doc_count=available_doc_count,
            pipeline_output=pipeline_output,
            latency_ms=latency_ms,
            token_usage=token_usage,
            execution_error=error,
        )
        results.append(res)

        # Throttle slightly to respect Gemini API RPM limits
        if rate_limit_delay_seconds > 0 and idx < total:
            await asyncio.sleep(rate_limit_delay_seconds)

    # 3. Aggregate summaries
    global_summary, category_summaries = aggregate_summaries(results, dataset.total_questions)

    report = EvaluationReport(
        metadata={
            "dataset_name": dataset.dataset_name,
            "dataset_version": dataset.dataset_version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "target_notebook_id": resolved_nb,
            "target_owner_id": resolved_owner,
            "available_doc_count": available_doc_count,
            "evaluated_questions_count": len(results),
            "filter_category": category.value if isinstance(category, QuestionCategory) else category,
            "filter_limit": limit,
        },
        summary=global_summary,
        category_scores=category_summaries,
        questions=results,
    )

    # 4. Save report
    if not output_path:
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs("evaluation_reports", exist_ok=True)
        output_path = Path("evaluation_reports") / f"rag_benchmark_report_{timestamp_str}.json"

    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report.model_dump(), f, indent=2)

    # Also update canonical backend/evaluation_report.json
    canonical_file = Path("backend/evaluation_report.json").resolve()
    try:
        with open(canonical_file, "w", encoding="utf-8") as f:
            json.dump(report.model_dump(), f, indent=2)
    except Exception as e:
        logger.warning(f"Could not write canonical report: {e}")

    logger.info(f"Evaluation report successfully written to {out_file}")
    return report

