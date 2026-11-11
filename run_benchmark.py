"""
Benchmark execution entry point for NotebookLM Lite RAG Evaluation.
Runs the 70-question benchmark dataset against the existing LangGraph + MCP + Qdrant pipeline.

Usage:
    python run_benchmark.py
    python run_benchmark.py --category straightforward --limit 5
    python run_benchmark.py --category unanswerable
    python run_benchmark.py --help
"""

import os
import sys

# Ensure backend directory is in sys.path
root_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(root_dir, "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.evaluation.cli import main

if __name__ == "__main__":
    main()

