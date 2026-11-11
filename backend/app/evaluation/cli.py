"""
Command Line Interface (CLI) for running the NotebookLM Lite RAG Benchmark.

Usage examples:
    python -m app.evaluation.cli
    python -m app.evaluation.cli --category straightforward --limit 5
    python -m app.evaluation.cli --category unanswerable
    python -m app.evaluation.cli --dataset custom_dataset.json --output report.json
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from app.evaluation.runner import run_benchmark
from app.evaluation.schemas import EvaluationStatus, QuestionCategory


def print_banner():
    print("=" * 80)
    print("      NOTEBOOKLM LITE — RAG EVALUATION HARNESS & BENCHMARK RUNNER")
    print("=" * 80)


def print_summary_table(report):
    s = report.summary
    print("\n" + "=" * 80)
    print("                        BENCHMARK SUMMARY RESULTS")
    print("=" * 80)
    print(f"Total Questions Evaluated : {s.total_questions}")
    print(f"Passed                    : {s.passed} [PASS]")
    print(f"Failed                    : {s.failed} [FAIL]")
    print(f"Blocked (Preconditions)   : {s.blocked} [BLOCKED]")
    print(f"Errors                    : {s.errors} [ERROR]")
    print(f"Overall Pass Rate         : {s.overall_pass_rate * 100:.1f}%")
    print(f"Mean Latency              : {s.mean_latency_ms} ms")
    print(f"Mean Answer Relevance     : {s.mean_answer_relevance * 100:.1f}%")
    print(f"Mean Retrieval Relevance  : {s.mean_retrieval_relevance * 100:.1f}%")
    print(f"Mean Citation Precision   : {s.mean_citation_precision * 100:.1f}%")
    print(f"Mean Page Accuracy        : {s.mean_citation_page_accuracy * 100:.1f}%")
    print(f"Mean Claim Grounding      : {s.mean_claim_grounding * 100:.1f}%")
    print(f"Mean Abstention Accuracy  : {s.mean_abstention_accuracy * 100:.1f}%")
    print("-" * 80)

    print("\nCATEGORY BREAKDOWN:")
    header = f"{'Category':<18} | {'Total':<5} | {'Pass':<5} | {'Fail':<5} | {'Block':<5} | {'Rate':<7} | {'AnsRel':<7} | {'CitPrec':<7} | {'Ground':<7}"
    print(header)
    print("-" * len(header))

    for cat_name, cat in report.category_scores.items():
        row = (
            f"{cat_name:<18} | "
            f"{cat.total:<5} | "
            f"{cat.passed:<5} | "
            f"{cat.failed:<5} | "
            f"{cat.blocked:<5} | "
            f"{cat.pass_rate * 100:>5.1f}% | "
            f"{cat.mean_answer_relevance * 100:>5.1f}% | "
            f"{cat.mean_citation_precision * 100:>5.1f}% | "
            f"{cat.mean_claim_grounding * 100:>5.1f}%"
        )
        print(row)
    print("=" * 80 + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="notebooklm-rag-benchmark",
        description="Run RAG evaluation benchmark for NotebookLM Lite against the 70-question dataset.",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default=None,
        help="Path to evaluation JSON dataset (default: auto-detected)",
    )
    parser.add_argument(
        "--notebook-id",
        type=str,
        default=None,
        help="Target notebook UUID (default: auto-detected containing AI Engineering.pdf)",
    )
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        choices=[c.value for c in QuestionCategory],
        help="Filter execution to a specific question category",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of questions to evaluate (useful for quick smoke tests)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Path to output JSON evaluation report",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Delay in seconds between pipeline calls to throttle API usage (default: 0.5s)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging output",
    )
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    print_banner()

    try:
        report = asyncio.run(
            run_benchmark(
                dataset_path=args.dataset,
                notebook_id=args.notebook_id,
                category=args.category,
                limit=args.limit,
                output_path=args.output,
                rate_limit_delay_seconds=args.delay,
            )
        )
        print_summary_table(report)
        print(f"Evaluation report generated successfully.")
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n[!] Evaluation interrupted by user.")
        sys.exit(130)
    except Exception as exc:
        print(f"\n[ERROR] Benchmark execution failed: {exc}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
