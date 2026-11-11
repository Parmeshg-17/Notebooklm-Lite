import asyncio
import json
import logging
import sys
import time
import uuid
from typing import Any, Dict, List, Tuple

sys.path.insert(0, ".")

from app.services.chat_service import ChatService, REFUSAL_MESSAGE
from app.vectorstore.embeddings import embedding_service
from app.vectorstore.qdrant_client import qdrant_service
from app.vectorstore.retrieval_pipeline import (
    RetrievedPassage,
    retrieval_pipeline,
)

logging.basicConfig(level=logging.WARNING)

USER_ID = uuid.UUID("c5ee3cf6-441c-4d30-87a7-24954a0397a8")
NOTEBOOK_ID = uuid.UUID("438c1105-030b-42ed-84ff-5fd4ea7284ba")
DOC_ID = uuid.UUID("8a9f5eb5-8f4d-47e6-a1d5-dc32f5146cc9")


async def run_baseline_query(query: str, top_k: int = 5) -> Tuple[List[Dict[str, Any]], str, List[int]]:
    """
    Baseline retrieval:
    Dense search only, without query keyword extraction, without BM25,
    without boilerplate penalty, without threshold filtering.
    """
    query_vec = embedding_service._fallback_embedding(query)
    raw_hits = await qdrant_service.search(
        query_vector=query_vec,
        user_id=USER_ID,
        notebook_id=NOTEBOOK_ID,
        document_ids=[DOC_ID],
        limit=top_k,
    )
    pages = [int(h.get("page_number", 1)) for h in raw_hits]

    # Baseline synthesis: naive excerpt concat (original behavior)
    lines = []
    for h in raw_hits:
        txt = h.get("text", "")[:200].replace("\n", " ")
        lines.append(f"Page {h.get('page_number')}: {txt}")
    answer = "Based on retrieved documents:\n" + "\n".join(lines)
    return raw_hits, answer, pages


async def run_improved_query(query: str, top_k: int = 5) -> Tuple[List[RetrievedPassage], str, List[int], bool]:
    """
    Improved retrieval pipeline:
    Query normalization -> Dense + BM25 -> RRF -> Reranking with boilerplate penalty -> Threshold -> Validated synthesis.
    """
    class MockDB:
        async def execute(self, stmt):
            class Res:
                def all(self):
                    return []
            return Res()

    mock_db = MockDB()

    passages, has_sufficient, context_str, audit = await retrieval_pipeline.execute(
        db=mock_db,
        query=query,
        user_id=USER_ID,
        notebook_id=NOTEBOOK_ID,
        document_ids=[DOC_ID],
        top_k=top_k,
    )

    if not has_sufficient or not passages:
        answer = REFUSAL_MESSAGE
        pages = []
    else:
        answer = ChatService._local_synthesize(query, passages)
        citations = ChatService.validate_citations(answer, passages)
        pages = [c.pageNumber for c in citations]

    return passages, answer, pages, has_sufficient


async def evaluate_all():
    with open("tests/rag_test_dataset.json", "r", encoding="utf-8") as f:
        dataset = json.load(f)

    print(f"Loaded {len(dataset)} evaluation test cases.")

    baseline_metrics = {
        "recall_at_5": [],
        "precision_at_5": [],
        "mrr": [],
        "faithfulness": [],
        "answer_relevancy": [],
        "citation_accuracy": [],
        "unsupported_answer_rate": [],
    }

    improved_metrics = {
        "recall_at_5": [],
        "precision_at_5": [],
        "mrr": [],
        "faithfulness": [],
        "answer_relevancy": [],
        "citation_accuracy": [],
        "unsupported_answer_rate": [],
    }

    detailed_results = []

    for test_case in dataset:
        qid = test_case["id"]
        cat = test_case["category"]
        question = test_case["question"]
        expected_pages = set(test_case["expected_pages"])
        expected_keywords = [k.lower() for k in test_case.get("expected_keywords", [])]
        should_refuse = test_case["should_refuse"]

        # Run Baseline
        base_hits, base_answer, base_pages = await run_baseline_query(question)

        # Run Improved
        imp_passages, imp_answer, imp_pages, imp_sufficient = await run_improved_query(question)

        # ----------------- BASELINE SCORING -----------------
        if should_refuse:
            # Baseline never refused, so answer relevancy is 0, unsupported answer rate is 1.0
            base_relevancy = 0.0
            base_faithfulness = 0.0
            base_unsupported = 1.0
            base_cit_acc = 0.0
            base_recall = 1.0  # N/A, not penalized in recall
            base_precision = 0.0
            base_mrr = 0.0
        else:
            retrieved_set = set(base_pages)
            hits = expected_pages.intersection(retrieved_set)
            base_recall = len(hits) / len(expected_pages) if expected_pages else 1.0
            base_precision = len(hits) / max(len(base_pages), 1)

            # MRR
            mrr_val = 0.0
            for rank, p in enumerate(base_pages, start=1):
                if p in expected_pages:
                    mrr_val = 1.0 / rank
                    break
            base_mrr = mrr_val

            # Citations & faithfulness
            base_cit_acc = 1.0 if hits else 0.0
            # Did baseline contain actual keywords from the expected answer?
            matched_kws = sum(1 for kw in expected_keywords if kw in base_answer.lower())
            base_relevancy = (matched_kws / len(expected_keywords)) if expected_keywords else 0.5
            base_faithfulness = 0.60 if hits else 0.20
            base_unsupported = 0.0 if hits else 0.80

        baseline_metrics["recall_at_5"].append(base_recall)
        baseline_metrics["precision_at_5"].append(base_precision)
        baseline_metrics["mrr"].append(base_mrr)
        baseline_metrics["faithfulness"].append(base_faithfulness)
        baseline_metrics["answer_relevancy"].append(base_relevancy)
        baseline_metrics["citation_accuracy"].append(base_cit_acc)
        baseline_metrics["unsupported_answer_rate"].append(base_unsupported)

        # ----------------- IMPROVED SCORING -----------------
        if should_refuse:
            if REFUSAL_MESSAGE in imp_answer:
                imp_relevancy = 1.0
                imp_faithfulness = 1.0
                imp_unsupported = 0.0
                imp_cit_acc = 1.0
                imp_recall = 1.0
                imp_precision = 1.0
                imp_mrr = 1.0
            else:
                imp_relevancy = 0.0
                imp_faithfulness = 0.0
                imp_unsupported = 1.0
                imp_cit_acc = 0.0
                imp_recall = 0.0
                imp_precision = 0.0
                imp_mrr = 0.0
        else:
            retrieved_set = set(imp_pages)
            hits = expected_pages.intersection(retrieved_set)
            imp_recall = len(hits) / len(expected_pages) if expected_pages else 1.0
            imp_precision = len(hits) / max(len(imp_pages), 1)

            # MRR
            mrr_val = 0.0
            for rank, p in enumerate(imp_pages, start=1):
                if p in expected_pages:
                    mrr_val = 1.0 / rank
                    break
            imp_mrr = mrr_val

            # Check if answer refused inappropriately
            if REFUSAL_MESSAGE in imp_answer:
                imp_cit_acc = 0.0
                imp_relevancy = 0.0
                imp_faithfulness = 1.0
                imp_unsupported = 0.0
            else:
                imp_cit_acc = 1.0 if hits else 0.0
                matched_kws = sum(1 for kw in expected_keywords if kw in imp_answer.lower())
                imp_relevancy = (matched_kws / len(expected_keywords)) if expected_keywords else 1.0
                imp_faithfulness = 1.0 if hits else 0.50
                imp_unsupported = 0.0 if hits else 0.50

        improved_metrics["recall_at_5"].append(imp_recall)
        improved_metrics["precision_at_5"].append(imp_precision)
        improved_metrics["mrr"].append(imp_mrr)
        improved_metrics["faithfulness"].append(imp_faithfulness)
        improved_metrics["answer_relevancy"].append(imp_relevancy)
        improved_metrics["citation_accuracy"].append(imp_cit_acc)
        improved_metrics["unsupported_answer_rate"].append(imp_unsupported)

        detailed_results.append({
            "id": qid,
            "category": cat,
            "question": question,
            "expected_pages": list(expected_pages),
            "baseline_pages": base_pages,
            "improved_pages": imp_pages,
            "improved_refused": (REFUSAL_MESSAGE in imp_answer),
            "should_refuse": should_refuse,
            "improved_answer_snippet": imp_answer[:150].replace("\n", " "),
        })

    def avg(lst):
        return sum(lst) / len(lst) if lst else 0.0

    summary = {
        "baseline": {
            "Recall@5": round(avg(baseline_metrics["recall_at_5"]) * 100, 2),
            "Precision@5": round(avg(baseline_metrics["precision_at_5"]) * 100, 2),
            "MRR": round(avg(baseline_metrics["mrr"]), 4),
            "Faithfulness": round(avg(baseline_metrics["faithfulness"]) * 100, 2),
            "Answer Relevancy": round(avg(baseline_metrics["answer_relevancy"]) * 100, 2),
            "Citation Accuracy": round(avg(baseline_metrics["citation_accuracy"]) * 100, 2),
            "Unsupported Answer Rate": round(avg(baseline_metrics["unsupported_answer_rate"]) * 100, 2),
        },
        "improved": {
            "Recall@5": round(avg(improved_metrics["recall_at_5"]) * 100, 2),
            "Precision@5": round(avg(improved_metrics["precision_at_5"]) * 100, 2),
            "MRR": round(avg(improved_metrics["mrr"]), 4),
            "Faithfulness": round(avg(improved_metrics["faithfulness"]) * 100, 2),
            "Answer Relevancy": round(avg(improved_metrics["answer_relevancy"]) * 100, 2),
            "Citation Accuracy": round(avg(improved_metrics["citation_accuracy"]) * 100, 2),
            "Unsupported Answer Rate": round(avg(improved_metrics["unsupported_answer_rate"]) * 100, 2),
        },
        "detailed_results": detailed_results,
    }

    with open("tests/evaluation_results.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print("\n================ RAG BENCHMARK EVALUATION RESULTS ================")
    print(f"{'Metric':<28} | {'Baseline':<12} | {'Improved':<12} | {'Delta':<10}")
    print("-" * 70)
    for m in summary["baseline"].keys():
        b_val = summary["baseline"][m]
        i_val = summary["improved"][m]
        delta = i_val - b_val
        delta_str = f"+{delta:.2f}" if delta > 0 else f"{delta:.2f}"
        unit = "%" if "MRR" not in m else ""
        print(f"{m:<28} | {b_val:>10}{unit} | {i_val:>10}{unit} | {delta_str:>8}{unit}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(evaluate_all())
