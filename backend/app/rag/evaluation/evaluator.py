import asyncio
import csv
import json
import logging
import sys
import uuid
from typing import Any, Dict, List

from app.rag.citations.citation_validator import CitationValidator
from app.rag.evaluation.dataset import EVALUATION_DATASET, EvaluationTestCase
from app.rag.evaluation.metrics import RAGMetrics
from app.rag.generation.gemini_generator import gemini_generator
from app.rag.generation.prompts import REFUSAL_MESSAGE
from app.rag.retrieval.context_builder import ContextBuilder
from app.rag.retrieval.qdrant_store import qdrant_store
from app.rag.retrieval.retriever import modular_retriever

logger = logging.getLogger("app.rag.evaluator")

USER_ID = uuid.UUID("c5ee3cf6-441c-4d30-87a7-24954a0397a8")
NOTEBOOK_ID = uuid.UUID("438c1105-030b-42ed-84ff-5fd4ea7284ba")
DOC_ID = uuid.UUID("8a9f5eb5-8f4d-47e6-a1d5-dc32f5146cc9")


class RAGEvaluator:
    @staticmethod
    async def run_baseline(case: EvaluationTestCase) -> Dict[str, Any]:
        """
        Baseline RAG pipeline:
        Raw dense search only, without query normalization, without BM25,
        without boilerplate penalty, without threshold filtering, no citation validation.
        """
        from app.rag.embeddings.gemini_embeddings import gemini_embeddings
        query_vec = await gemini_embeddings.aembed_query(case.question)

        hits = await qdrant_store.similarity_search(
            query_vector=query_vec,
            user_id=USER_ID,
            notebook_id=NOTEBOOK_ID,
            document_ids=[DOC_ID],
            limit=5,
        )
        retrieved_pages = [int(h.get("page_number", 1)) for h in hits]

        # Naive synthesis (baseline never refused)
        lines = [f"Page {h.get('page_number')}: {h.get('text', '')[:120]}" for h in hits]
        answer = "Based on retrieved documents:\n" + "\n".join(lines)
        is_refusal = False

        citations = retrieved_pages

        return {
            "retrieved_pages": retrieved_pages,
            "answer": answer,
            "is_refusal": is_refusal,
            "citations": citations,
            "is_grounded": False,
        }

    @staticmethod
    async def run_improved(case: EvaluationTestCase) -> Dict[str, Any]:
        """
        Improved Production RAG engine:
        Normalized query -> Dense + BM25 -> RRF -> Reranking with boilerplate penalty ->
        Threshold filtering -> Strict Grounded Generation -> Strict Citation Validation.
        """
        chunks, has_sufficient, context_text, _ = await modular_retriever.retrieve(
            query=case.question,
            user_id=USER_ID,
            notebook_id=NOTEBOOK_ID,
            document_ids=[DOC_ID],
            top_k=5,
        )

        gen_result = await gemini_generator.generate_answer(
            query=case.question,
            context_text=context_text,
            candidate_chunks=chunks,
            has_sufficient_evidence=has_sufficient,
        )

        valid_cits, is_grounded = CitationValidator.validate_citations(
            citations=gen_result.citations,
            retrieved_chunks=chunks,
            answer_text=gen_result.answer,
        )

        is_refusal = (REFUSAL_MESSAGE in gen_result.answer) or gen_result.insufficient_evidence
        retrieved_pages = [int(c.get("page_number", 1)) for c in chunks] if not is_refusal else []
        citation_pages = [int(c["page_number"]) for c in valid_cits]

        return {
            "retrieved_pages": retrieved_pages,
            "answer": gen_result.answer,
            "is_refusal": is_refusal,
            "citations": citation_pages,
            "is_grounded": is_grounded,
        }

    @classmethod
    async def evaluate_suite(cls) -> Dict[str, Any]:
        results = []
        b_metrics = {
            "recall_5": [], "precision_5": [], "mrr": [], "context_prec": [],
            "faithfulness": [], "relevancy": [], "cit_accuracy": [],
            "unsupported_rate": [], "refusal_acc": []
        }
        i_metrics = {
            "recall_5": [], "precision_5": [], "mrr": [], "context_prec": [],
            "faithfulness": [], "relevancy": [], "cit_accuracy": [],
            "unsupported_rate": [], "refusal_acc": []
        }

        for case in EVALUATION_DATASET:
            exp_pages = set(case.expected_pages)

            base_res = await cls.run_baseline(case)
            imp_res = await cls.run_improved(case)

            # Baseline metrics
            b_r5 = RAGMetrics.recall_at_k(base_res["retrieved_pages"], exp_pages)
            b_p5 = RAGMetrics.precision_at_k(base_res["retrieved_pages"], exp_pages)
            b_mrr = RAGMetrics.mean_reciprocal_rank(base_res["retrieved_pages"], exp_pages)
            b_cp = RAGMetrics.context_precision(base_res["retrieved_pages"], exp_pages)
            b_rel = RAGMetrics.answer_relevancy(base_res["answer"], case.expected_keywords, case.should_refuse, base_res["is_refusal"])
            b_fth = RAGMetrics.faithfulness(base_res["is_grounded"], case.should_refuse, base_res["is_refusal"])
            b_cit = RAGMetrics.citation_accuracy(base_res["citations"], exp_pages, case.should_refuse)
            b_uns = RAGMetrics.unsupported_claim_rate(base_res["citations"], exp_pages, case.should_refuse, base_res["is_refusal"])
            b_ref = RAGMetrics.refusal_accuracy(case.should_refuse, base_res["is_refusal"])

            b_metrics["recall_5"].append(b_r5)
            b_metrics["precision_5"].append(b_p5)
            b_metrics["mrr"].append(b_mrr)
            b_metrics["context_prec"].append(b_cp)
            b_metrics["relevancy"].append(b_rel)
            b_metrics["faithfulness"].append(b_fth)
            b_metrics["cit_accuracy"].append(b_cit)
            b_metrics["unsupported_rate"].append(b_uns)
            b_metrics["refusal_acc"].append(b_ref)

            # Improved metrics
            i_r5 = RAGMetrics.recall_at_k(imp_res["retrieved_pages"], exp_pages)
            i_p5 = RAGMetrics.precision_at_k(imp_res["retrieved_pages"], exp_pages)
            i_mrr = RAGMetrics.mean_reciprocal_rank(imp_res["retrieved_pages"], exp_pages)
            i_cp = RAGMetrics.context_precision(imp_res["retrieved_pages"], exp_pages)
            i_rel = RAGMetrics.answer_relevancy(imp_res["answer"], case.expected_keywords, case.should_refuse, imp_res["is_refusal"])
            i_fth = RAGMetrics.faithfulness(imp_res["is_grounded"], case.should_refuse, imp_res["is_refusal"])
            i_cit = RAGMetrics.citation_accuracy(imp_res["citations"], exp_pages, case.should_refuse)
            i_uns = RAGMetrics.unsupported_claim_rate(imp_res["citations"], exp_pages, case.should_refuse, imp_res["is_refusal"])
            i_ref = RAGMetrics.refusal_accuracy(case.should_refuse, imp_res["is_refusal"])

            i_metrics["recall_5"].append(i_r5)
            i_metrics["precision_5"].append(i_p5)
            i_metrics["mrr"].append(i_mrr)
            i_metrics["context_prec"].append(i_cp)
            i_metrics["relevancy"].append(i_rel)
            i_metrics["faithfulness"].append(i_fth)
            i_metrics["cit_accuracy"].append(i_cit)
            i_metrics["unsupported_rate"].append(i_uns)
            i_metrics["refusal_acc"].append(i_ref)

            results.append({
                "id": case.id,
                "category": case.category,
                "question": case.question,
                "expected_pages": list(exp_pages),
                "baseline_pages": base_res["retrieved_pages"],
                "improved_pages": imp_res["retrieved_pages"],
                "baseline_citations": base_res["citations"],
                "improved_citations": imp_res["citations"],
                "improved_refused": imp_res["is_refusal"],
                "should_refuse": case.should_refuse,
                "improved_answer_preview": imp_res["answer"][:120].replace("\n", " "),
            })

        def avg(l):
            return sum(l) / len(l) if l else 0.0

        summary = {
            "baseline": {
                "Recall@5": round(avg(b_metrics["recall_5"]) * 100, 2),
                "Precision@5": round(avg(b_metrics["precision_5"]) * 100, 2),
                "MRR": round(avg(b_metrics["mrr"]), 4),
                "Context Precision": round(avg(b_metrics["context_prec"]) * 100, 2),
                "Faithfulness": round(avg(b_metrics["faithfulness"]) * 100, 2),
                "Answer Relevancy": round(avg(b_metrics["relevancy"]) * 100, 2),
                "Citation Accuracy": round(avg(b_metrics["cit_accuracy"]) * 100, 2),
                "Unsupported Claim Rate": round(avg(b_metrics["unsupported_rate"]) * 100, 2),
                "Refusal Accuracy": round(avg(b_metrics["refusal_acc"]) * 100, 2),
            },
            "improved": {
                "Recall@5": round(avg(i_metrics["recall_5"]) * 100, 2),
                "Precision@5": round(avg(i_metrics["precision_5"]) * 100, 2),
                "MRR": round(avg(i_metrics["mrr"]), 4),
                "Context Precision": round(avg(i_metrics["context_prec"]) * 100, 2),
                "Faithfulness": round(avg(i_metrics["faithfulness"]) * 100, 2),
                "Answer Relevancy": round(avg(i_metrics["relevancy"]) * 100, 2),
                "Citation Accuracy": round(avg(i_metrics["cit_accuracy"]) * 100, 2),
                "Unsupported Claim Rate": round(avg(i_metrics["unsupported_rate"]) * 100, 2),
                "Refusal Accuracy": round(avg(i_metrics["refusal_acc"]) * 100, 2),
            },
            "detailed_cases": results,
        }

        # Save JSON
        with open("evaluation_benchmark.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        # Save CSV
        with open("evaluation_benchmark.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Metric", "Baseline", "Improved", "Delta"])
            for m in summary["baseline"].keys():
                b_val = summary["baseline"][m]
                i_val = summary["improved"][m]
                delta = round(i_val - b_val, 2)
                writer.writerow([m, b_val, i_val, f"+{delta}" if delta > 0 else delta])

        return summary


async def main():
    print("Executing 30-Question RAG Benchmark Evaluation...")
    summary = await RAGEvaluator.evaluate_suite()
    print("\n" + "=" * 76)
    print(f"{'EVALUATION METRIC':<28} | {'BASELINE':<12} | {'IMPROVED RAG':<14} | {'DELTA':<10}")
    print("=" * 76)
    for m in summary["baseline"].keys():
        b_val = summary["baseline"][m]
        i_val = summary["improved"][m]
        delta = round(i_val - b_val, 2)
        unit = "%" if "MRR" not in m else ""
        delta_str = f"+{delta:.2f}{unit}" if delta > 0 else f"{delta:.2f}{unit}"
        print(f"{m:<28} | {b_val:>10.2f}{unit} | {i_val:>12.2f}{unit} | {delta_str:>10}")
    print("=" * 76)
    print("Evaluation benchmark results saved to evaluation_benchmark.json and evaluation_benchmark.csv")


if __name__ == "__main__":
    asyncio.run(main())

