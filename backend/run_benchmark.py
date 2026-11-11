"""
Benchmark execution entry point for NotebookLM Lite RAG Evaluation (Backend).
"""

import os
import sys

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.evaluation.cli import main

if __name__ == "__main__":
    main()

