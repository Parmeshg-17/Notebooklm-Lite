"""
Intent Router for NotebookLM Lite LangGraph Agent.
Classifies user queries into 6 distinct intents:
1. SIMPLE_QUESTION
2. MULTI_DOCUMENT_QUESTION
3. COMPARISON_QUESTION
4. DOCUMENT_SUMMARY
5. PAGE_SPECIFIC_QUESTION
6. INSUFFICIENT_EVIDENCE
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("app.agents.router")

# Precompiled regex patterns for deterministic fast-path classification
PAGE_PATTERN = re.compile(
    r"\b(?:on\s+page|at\s+page|page\s+number|page|p\.)\s*(\d+)\b",
    re.IGNORECASE,
)
COMPARISON_PATTERN = re.compile(
    r"\b(compare|comparison|versus|vs\.?|differences? between|differ between|contrast|trade-?offs?)\b",
    re.IGNORECASE,
)
SUMMARY_PATTERN = re.compile(
    r"\b(summarize|summary|overview|abstract|outline|tldr|key findings in this document|what is this document about|give me a breakdown)\b",
    re.IGNORECASE,
)
MULTI_DOC_PATTERN = re.compile(
    r"\b(across (?:both|all|the) documents|in both papers|all sources|across documents|cross-document)\b",
    re.IGNORECASE,
)
OFF_TOPIC_PATTERN = re.compile(
    r"^(hi|hello|hey|who are you|what is the weather|tell me a joke|write a poem|sing a song|recipe for)\b",
    re.IGNORECASE,
)


class IntentRouter:
    """
    Evaluates queries and routes them to optimal retrieval and reasoning nodes.
    Features deterministic regex classification with Gemini LLM fallback.
    """

    @classmethod
    def classify_heuristically(
        cls,
        question: str,
        num_documents: int = 1,
    ) -> Tuple[str, Optional[int], List[str]]:
        """
        Fast, zero-latency heuristic classifier.
        Returns (intent, target_page, sub_questions).
        """
        q_clean = question.strip()

        # Check off-topic / chitchat first
        if OFF_TOPIC_PATTERN.search(q_clean):
            return "INSUFFICIENT_EVIDENCE", None, []

        # Check page-specific
        page_match = PAGE_PATTERN.search(q_clean)
        if page_match:
            try:
                page_num = int(page_match.group(1))
                return "PAGE_SPECIFIC_QUESTION", page_num, [q_clean]
            except (ValueError, IndexError):
                pass

        # Check comparison
        if COMPARISON_PATTERN.search(q_clean):
            sub_q = [
                f"Core approach and findings for query: {q_clean}",
                f"Distinguishing differences and metrics for: {q_clean}",
            ]
            return "COMPARISON_QUESTION", None, sub_q

        # Check summary
        if SUMMARY_PATTERN.search(q_clean):
            return "DOCUMENT_SUMMARY", None, [
                "Main objective and key methodology",
                "Key empirical findings and results",
            ]

        # Check multi-document
        if MULTI_DOC_PATTERN.search(q_clean) or (num_documents > 1 and "both" in q_clean.lower()):
            return "MULTI_DOCUMENT_QUESTION", None, [
                f"Evidence from source 1 for: {q_clean}",
                f"Evidence from source 2 for: {q_clean}",
            ]

        return "SIMPLE_QUESTION", None, [q_clean]

    @classmethod
    async def route_question(
        cls,
        question: str,
        document_titles: Optional[List[str]] = None,
        has_documents: bool = True,
    ) -> Dict[str, Any]:
        """
        Determines the routing intent, target page (if applicable), and sub-questions.
        """
        if not has_documents:
            return {
                "intent": "INSUFFICIENT_EVIDENCE",
                "target_page": None,
                "reasoning": "Notebook contains no indexed documents.",
                "sub_questions": [],
            }

        doc_count = len(document_titles) if document_titles else 1
        intent, target_page, sub_questions = cls.classify_heuristically(question, num_documents=doc_count)

        logger.info(
            f"[INTENT ROUTER] Query='{question[:40]}' -> Intent={intent} | "
            f"Page={target_page} | SubQuestions={len(sub_questions)}"
        )

        return {
            "intent": intent,
            "target_page": target_page,
            "reasoning": f"Heuristically routed to {intent}",
            "sub_questions": sub_questions,
        }

