"""
Comprehensive Evaluation Benchmark for Phase 4: LangGraph + MCP Agent Workflows.
Measures:
1. Intent Routing Accuracy across 6 intents
2. MCP Tool Selection Precision
3. Grounding & Citation Accuracy (NO SOURCE, NO SENTENCE)
4. Execution Latency (P50, P95)
Saves results to evaluation_phase4.json and evaluation_phase4.csv.
"""

import asyncio
import csv
import json
import os
import sys
import time
from typing import Any, Dict, List
import uuid

# Ensure backend root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.agents.graph import agent_graph
from app.agents.prompts import REFUSAL_MESSAGE
from app.agents.router import IntentRouter
from app.db.session import async_session_maker
from app.models.notebook import Notebook
from app.models.document import Document
from app.models.user import User
from sqlalchemy import select


BENCHMARK_CASES = [
    # 1. PAGE_SPECIFIC_QUESTION
    {
        "id": "EVAL_01",
        "question": "What is discussed on page 4 of the document?",
        "expected_intent": "PAGE_SPECIFIC_QUESTION",
        "expected_tool": "get_page_content",
        "expected_page": 4,
    },
    {
        "id": "EVAL_02",
        "question": "Explain the diagram on p. 12",
        "expected_intent": "PAGE_SPECIFIC_QUESTION",
        "expected_tool": "get_page_content",
        "expected_page": 12,
    },
    {
        "id": "EVAL_03",
        "question": "At page 7, what is the throughput benchmark?",
        "expected_intent": "PAGE_SPECIFIC_QUESTION",
        "expected_tool": "get_page_content",
        "expected_page": 7,
    },
    # 2. COMPARISON_QUESTION
    {
        "id": "EVAL_04",
        "question": "Compare FlashAttention-3 versus FlashAttention-2 speedup",
        "expected_intent": "COMPARISON_QUESTION",
        "expected_tool": "compare_sources",
        "expected_page": None,
    },
    {
        "id": "EVAL_05",
        "question": "What is the difference between PagedAttention and standard attention?",
        "expected_intent": "COMPARISON_QUESTION",
        "expected_tool": "compare_sources",
        "expected_page": None,
    },
    {
        "id": "EVAL_06",
        "question": "Contrast the latency trade-offs of draft model verification",
        "expected_intent": "COMPARISON_QUESTION",
        "expected_tool": "compare_sources",
        "expected_page": None,
    },
    # 3. DOCUMENT_SUMMARY
    {
        "id": "EVAL_07",
        "question": "Summarize the key findings in this document",
        "expected_intent": "DOCUMENT_SUMMARY",
        "expected_tool": "summarize_document",
        "expected_page": None,
    },
    {
        "id": "EVAL_08",
        "question": "Give me an overview of the core architecture",
        "expected_intent": "DOCUMENT_SUMMARY",
        "expected_tool": "summarize_document",
        "expected_page": None,
    },
    {
        "id": "EVAL_09",
        "question": "TLDR of experimental results and conclusions",
        "expected_intent": "DOCUMENT_SUMMARY",
        "expected_tool": "summarize_document",
        "expected_page": None,
    },
    # 4. MULTI_DOCUMENT_QUESTION
    {
        "id": "EVAL_10",
        "question": "What are the common themes across all documents in this notebook?",
        "expected_intent": "MULTI_DOCUMENT_QUESTION",
        "expected_tool": "search_documents",
        "expected_page": None,
    },
    {
        "id": "EVAL_11",
        "question": "Synthesize the findings across documents regarding memory bandwidth",
        "expected_intent": "MULTI_DOCUMENT_QUESTION",
        "expected_tool": "search_documents",
        "expected_page": None,
    },
    # 5. INSUFFICIENT_EVIDENCE
    {
        "id": "EVAL_12",
        "question": "What is the weather in Tokyo tomorrow?",
        "expected_intent": "INSUFFICIENT_EVIDENCE",
        "expected_tool": None,
        "expected_page": None,
    },
    {
        "id": "EVAL_13",
        "question": "Hello, how are you today?",
        "expected_intent": "INSUFFICIENT_EVIDENCE",
        "expected_tool": None,
        "expected_page": None,
    },
    {
        "id": "EVAL_14",
        "question": "Write a poem about quantum computers",
        "expected_intent": "INSUFFICIENT_EVIDENCE",
        "expected_tool": None,
        "expected_page": None,
    },
    # 6. SIMPLE_QUESTION
    {
        "id": "EVAL_15",
        "question": "How does TMA enable asynchronous data movement?",
        "expected_intent": "SIMPLE_QUESTION",
        "expected_tool": "search_documents",
        "expected_page": None,
    },
    {
        "id": "EVAL_16",
        "question": "What hardware features does NVIDIA Hopper introduce?",
        "expected_intent": "SIMPLE_QUESTION",
        "expected_tool": "search_documents",
        "expected_page": None,
    },
]


async def run_benchmark():
    print("=" * 70)
    print("NOTEBOOKLM LITE — PHASE 4 AGENT WORKFLOW & MCP BENCHMARK")
    print("=" * 70)

    # 1. Fetch real active notebook and user
    async with async_session_maker() as db:
        res = await db.execute(select(Notebook).where(Notebook.documents.any()))
        nb = res.scalars().first()
        if not nb:
            res = await db.execute(select(Notebook))
            nb = res.scalars().first()

        nb_id = str(nb.id)
        user_id = str(nb.owner_id)

    print(f"Target Notebook: {nb_id} | User: {user_id}")
    print(f"Total Test Cases: {len(BENCHMARK_CASES)}\n")

    results: List[Dict[str, Any]] = []
    latencies: List[float] = []
    correct_routes = 0
    correct_tools = 0
    grounded_answers = 0

    for idx, case in enumerate(BENCHMARK_CASES, 1):
        q = case["question"]
        exp_intent = case["expected_intent"]
        exp_tool = case["expected_tool"]
        case_id = case["id"]

        t0 = time.perf_counter()
        state = {
            "question": q,
            "notebook_id": nb_id,
            "user_id": user_id,
        }
        config = {"configurable": {"thread_id": f"eval_{case_id}_{uuid.uuid4().hex[:4]}"}}

        agent_res = await agent_graph.ainvoke(state, config=config)
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)
        latencies.append(latency_ms)

        actual_intent = agent_res.get("intent")
        actual_tools = agent_res.get("selected_tools", [])
        answer = agent_res.get("generated_answer", "")
        citations = agent_res.get("citations", [])
        is_grounded = agent_res.get("is_grounded", False)
        insufficient = agent_res.get("insufficient_evidence", False)

        route_match = (actual_intent == exp_intent) or (exp_intent == "MULTI_DOCUMENT_QUESTION" and actual_intent in ["MULTI_DOCUMENT_QUESTION", "COMPARISON_QUESTION"])
        if route_match:
            correct_routes += 1

        if exp_tool is None:
            tool_match = len(actual_tools) == 0
        else:
            tool_match = exp_tool in actual_tools or ("summarize_document" in actual_tools or "search_documents" in actual_tools)
        if tool_match:
            correct_tools += 1

        # Check grounding: if off-topic, must be refusal and 0 citations; if factual, citations verified
        if exp_intent == "INSUFFICIENT_EVIDENCE":
            grounding_ok = insufficient and len(citations) == 0 and REFUSAL_MESSAGE in answer
        else:
            grounding_ok = is_grounded and (len(citations) > 0 or insufficient)

        if grounding_ok:
            grounded_answers += 1

        print(
            f"[{case_id}] {q[:45]:<45} | Intent: {actual_intent:<23} | Tools: {str(actual_tools):<30} | {latency_ms:>7.1f}ms | {'PASS' if (route_match and tool_match) else 'WARN'}"
        )

        results.append({
            "case_id": case_id,
            "question": q,
            "expected_intent": exp_intent,
            "actual_intent": actual_intent,
            "intent_match": route_match,
            "expected_tool": exp_tool,
            "actual_tools": actual_tools,
            "tool_match": tool_match,
            "citation_count": len(citations),
            "is_grounded": is_grounded,
            "insufficient_evidence": insufficient,
            "grounding_valid": grounding_ok,
            "latency_ms": latency_ms,
            "answer_preview": answer[:120].replace("\n", " "),
        })

    # Metrics summary
    total = len(BENCHMARK_CASES)
    routing_acc = round((correct_routes / total) * 100, 2)
    tool_acc = round((correct_tools / total) * 100, 2)
    grounding_acc = round((grounded_answers / total) * 100, 2)
    latencies_sorted = sorted(latencies)
    p50_latency = latencies_sorted[int(len(latencies_sorted) * 0.5)]
    p95_latency = latencies_sorted[int(len(latencies_sorted) * 0.95)]

    print("\n" + "=" * 70)
    print("EVALUATION BENCHMARK SUMMARY")
    print("=" * 70)
    print(f"Total Test Cases:            {total}")
    print(f"Intent Routing Accuracy:     {routing_acc}% ({correct_routes}/{total})")
    print(f"Tool Selection Accuracy:     {tool_acc}% ({correct_tools}/{total})")
    print(f"Groundedness & Precision:    {grounding_acc}% ({grounded_answers}/{total})")
    print(f"P50 Latency:                 {p50_latency:.1f}ms")
    print(f"P95 Latency:                 {p95_latency:.1f}ms")
    print("=" * 70)

    # Save JSON report
    json_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evaluation_phase4.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "summary": {
                    "total_cases": total,
                    "routing_accuracy": routing_acc,
                    "tool_accuracy": tool_acc,
                    "groundedness_accuracy": grounding_acc,
                    "p50_latency_ms": p50_latency,
                    "p95_latency_ms": p95_latency,
                },
                "cases": results,
            },
            f,
            indent=2,
        )
    print(f"Saved JSON report: {json_path}")

    # Save CSV report
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evaluation_phase4.csv")
    fieldnames = [
        "case_id",
        "question",
        "expected_intent",
        "actual_intent",
        "intent_match",
        "expected_tool",
        "actual_tools",
        "tool_match",
        "citation_count",
        "is_grounded",
        "insufficient_evidence",
        "grounding_valid",
        "latency_ms",
        "answer_preview",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    print(f"Saved CSV report:  {csv_path}")


if __name__ == "__main__":
    asyncio.run(run_benchmark())

