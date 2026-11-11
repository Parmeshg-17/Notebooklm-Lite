"""
RAG Evaluation Metrics for NotebookLM Lite.
Implements fine-grained scoring functions for:
- Answer relevance
- Retrieval relevance
- Citation precision
- Citation page accuracy
- Claim grounding
- Abstention accuracy
"""

import re
from typing import Any, Dict, List, Optional, Set, Tuple

REFUSAL_INDICATORS = [
    "couldn't find sufficient",
    "cannot find sufficient",
    "does not contain sufficient",
    "do not contain sufficient",
    "not contain sufficient",
    "insufficient evidence",
    "insufficient supporting information",
    "not enough information",
    "no source, no sentence",
    "cannot be found in the available",
    "do not have enough information",
    "not mentioned in the provided",
    "sources do not contain",
    "not found in the uploaded",
]

STOPWORDS = {
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "with", "by", "of",
    "is", "are", "was", "were", "what", "how", "why", "when", "where", "which", "who",
    "from", "into", "that", "this", "these", "those", "can", "could", "should", "would",
    "uploaded", "document", "documents", "source", "sources", "pdf", "explain", "describe",
    "according", "discuss", "book", "page", "pages", "printed"
}


def extract_keywords(text: str) -> Set[str]:
    """Extract clean lowercase keywords excluding common stopwords."""
    tokens = re.findall(r"\b[a-zA-Z0-9_\-]{3,}\b", text.lower())
    return {t for t in tokens if t not in STOPWORDS}


def is_refusal_text(answer: Optional[str]) -> bool:
    """Checks whether the generated answer text represents an explicit refusal/abstention."""
    if not answer or not answer.strip():
        return True
    lower = answer.lower()
    return any(indicator in lower for indicator in REFUSAL_INDICATORS)


def parse_page_hint(hint: Optional[str], front_matter_offset: int = 24) -> Set[int]:
    """
    Parses printed page hints like '256', '218–220', '218-220' into an integer page set.
    Includes both printed page numbers and PDF physical page numbers (offset +24 for front-matter),
    with a small ±2 leeway for book-to-PDF index drift.
    """
    if not hint:
        return set()

    # Normalize en-dash, em-dash to regular hyphen
    normalized = str(hint).replace("–", "-").replace("—", "-").strip()
    target_pages = set()

    range_match = re.match(r"^(\d+)\s*-\s*(\d+)$", normalized)
    if range_match:
        start, end = int(range_match.group(1)), int(range_match.group(2))
        for p in range(start, end + 1):
            target_pages.add(p)
    else:
        num_match = re.search(r"\b(\d+)\b", normalized)
        if num_match:
            target_pages.add(int(num_match.group(1)))

    # Expand with ±2 leeway to account for printed front-matter offset vs PDF index
    expanded = set()
    for p in target_pages:
        for base in [p, p + front_matter_offset]:
            for offset in range(-2, 3):
                if base + offset >= 1:
                    expanded.add(base + offset)

    return expanded


class RAGEvaluationMetrics:
    """
    Stateless metric calculation suite for RAG evaluation.
    Every metric returns a float in [0.0, 1.0].
    """

    @staticmethod
    def score_answer_relevance(
        question: str,
        answer: Optional[str],
        answerable_from_source: bool,
        insufficient_evidence_flag: Optional[bool] = None,
    ) -> float:
        """
        Evaluates whether the answer addresses the question.
        - If answerable: rewards substantive response covering question terms, penalizes false refusals.
        - If unanswerable: rewards explicit abstention, penalizes hallucinations.
        """
        if not answer or not answer.strip():
            return 0.0

        refusal = is_refusal_text(answer) or (insufficient_evidence_flag is True)

        if not answerable_from_source:
            # Unanswerable: should abstain
            return 1.0 if refusal else 0.0

        # Answerable: false refusal gets 0.0
        if refusal:
            return 0.0

        q_keywords = extract_keywords(question)
        if not q_keywords:
            return 1.0 if len(answer.strip()) > 20 else 0.5

        a_keywords = extract_keywords(answer)
        overlap = q_keywords.intersection(a_keywords)
        overlap_ratio = len(overlap) / len(q_keywords)

        # Baseline score if answer is substantive (>50 chars) plus overlap bonus
        length_factor = min(1.0, len(answer.strip()) / 80.0)
        relevance = 0.4 * length_factor + 0.6 * min(1.0, overlap_ratio * 1.5)
        return round(min(1.0, max(0.0, relevance)), 3)

    @staticmethod
    def score_retrieval_relevance(
        question: str,
        chunks: List[Dict[str, Any]],
        answerable_from_source: bool,
    ) -> float:
        """
        Evaluates the relevance of retrieved chunks to the question prompt.
        """
        if not answerable_from_source:
            # For unanswerable, having 0 chunks or low similarity chunks is expected
            if not chunks:
                return 1.0
            # If retrieved chunks have very high scores for an unanswerable query, slight penalty
            avg_score = sum(c.get("score", 0.0) or 0.0 for c in chunks) / max(1, len(chunks))
            return round(max(0.0, 1.0 - (avg_score * 0.5)), 3)

        if not chunks:
            return 0.0

        q_keywords = extract_keywords(question)
        if not q_keywords:
            return 1.0

        relevant_chunks_count = 0
        for chunk in chunks:
            text = chunk.get("text", "") or chunk.get("text_snippet", "")
            c_keywords = extract_keywords(text)
            if q_keywords.intersection(c_keywords) or (chunk.get("score") and chunk["score"] >= 0.5):
                relevant_chunks_count += 1

        ratio = relevant_chunks_count / len(chunks)
        return round(min(1.0, max(0.0, ratio)), 3)

    @staticmethod
    def score_citation_precision(
        citations: List[Dict[str, Any]],
        answerable_from_source: bool,
    ) -> float:
        """
        Calculates citation precision: ratio of valid citations to total citations.
        - Answerable: must have valid citations (>0) with non-null pages and excerpts.
        - Unanswerable: must have 0 citations.
        """
        if not answerable_from_source:
            # Unanswerable must have exactly 0 citations
            return 1.0 if len(citations) == 0 else 0.0

        if not citations:
            return 0.0

        valid_count = 0
        for c in citations:
            page = c.get("page_number")
            doc = c.get("document_id") or c.get("filename")
            snippet = c.get("text_excerpt") or c.get("snippet")
            if page is not None and int(page) >= 1 and (doc or snippet):
                valid_count += 1

        return round(valid_count / len(citations), 3)

    @staticmethod
    def score_citation_page_accuracy(
        citations: List[Dict[str, Any]],
        retrieved_chunks: List[Dict[str, Any]],
        page_hint_printed: Optional[str],
        answerable_from_source: bool,
    ) -> float:
        """
        Evaluates page-level citation accuracy.
        - If page_hint_printed is provided: checks whether cited/retrieved pages match target hint.
        - Otherwise: verifies all cited pages fall within valid bounds (1 to 550).
        """
        if not answerable_from_source:
            return 1.0

        if page_hint_printed:
            target_pages = parse_page_hint(page_hint_printed)
            if not target_pages:
                return 1.0

            # Gather all pages cited or retrieved
            cited_pages = {
                int(c["page_number"])
                for c in citations
                if c.get("page_number") is not None and str(c["page_number"]).isdigit()
            }
            retrieved_pages = {
                int(ch["page_number"])
                for ch in retrieved_chunks
                if ch.get("page_number") is not None and str(ch["page_number"]).isdigit()
            }

            all_pages = cited_pages.union(retrieved_pages)
            if not all_pages:
                return 0.0

            # Check overlap
            if all_pages.intersection(target_pages):
                return 1.0
            return 0.0

        # General question without page hint: verify cited pages are valid positive integers
        if not citations:
            return 0.0

        valid_page_count = 0
        for c in citations:
            p = c.get("page_number")
            if p is not None and 1 <= int(p) <= 600:
                valid_page_count += 1

        return round(valid_page_count / len(citations), 3)

    @staticmethod
    def score_claim_grounding(
        answer: Optional[str],
        retrieved_chunks: List[Dict[str, Any]],
        is_grounded_flag: Optional[bool] = None,
    ) -> float:
        """
        Evaluates whether claims in generated answer are grounded in retrieved chunks.
        If system abstained, claim grounding is 1.0 (no unsupported claims were made).
        """
        if not answer or not answer.strip():
            return 0.0

        if is_refusal_text(answer):
            return 1.0

        if is_grounded_flag is True:
            return 1.0

        if not retrieved_chunks:
            return 0.0

        combined_chunk_text = " ".join(
            (c.get("text", "") or c.get("text_snippet", "")) for c in retrieved_chunks
        ).lower()
        chunk_words = set(re.findall(r"\b\w{3,}\b", combined_chunk_text))

        sentences = [s.strip() for s in re.split(r"[.!?\n]", answer) if len(s.strip()) > 15]
        if not sentences:
            return 1.0

        grounded_sentences = 0
        for sentence in sentences:
            s_words = set(re.findall(r"\b\w{3,}\b", sentence.lower())) - STOPWORDS
            if not s_words:
                grounded_sentences += 1
                continue
            overlap = s_words.intersection(chunk_words)
            if (len(overlap) / len(s_words)) >= 0.40:
                grounded_sentences += 1

        return round(grounded_sentences / len(sentences), 3)

    @staticmethod
    def score_abstention_accuracy(
        answer: Optional[str],
        citations: List[Dict[str, Any]],
        insufficient_evidence_flag: Optional[bool],
        answerable_from_source: bool,
    ) -> float:
        """
        Evaluates abstention accuracy:
        - Unanswerable: 1.0 if properly refused with 0 citations; 0.0 if hallucinated.
        - Answerable: 1.0 if NOT falsely refused; 0.0 if false negative abstention.
        """
        refusal = is_refusal_text(answer) or (insufficient_evidence_flag is True)
        has_citations = len(citations) > 0

        if not answerable_from_source:
            # Should refuse and produce 0 citations
            if refusal and not has_citations:
                return 1.0
            return 0.0
        else:
            # Answerable: should not refuse
            if refusal:
                return 0.0
            return 1.0

    @classmethod
    def compute_all_metrics(
        cls,
        question: str,
        answer: Optional[str],
        citations: List[Dict[str, Any]],
        retrieved_chunks: List[Dict[str, Any]],
        answerable_from_source: bool,
        page_hint_printed: Optional[str] = None,
        insufficient_evidence: Optional[bool] = None,
        is_grounded: Optional[bool] = None,
    ) -> Dict[str, float]:
        """
        Computes all 6 metrics and calculates composite overall score.
        """
        ans_rel = cls.score_answer_relevance(
            question, answer, answerable_from_source, insufficient_evidence
        )
        ret_rel = cls.score_retrieval_relevance(question, retrieved_chunks, answerable_from_source)
        cit_prec = cls.score_citation_precision(citations, answerable_from_source)
        cit_page = cls.score_citation_page_accuracy(
            citations, retrieved_chunks, page_hint_printed, answerable_from_source
        )
        claim_grd = cls.score_claim_grounding(answer, retrieved_chunks, is_grounded)
        abst_acc = cls.score_abstention_accuracy(
            answer, citations, insufficient_evidence, answerable_from_source
        )

        if not answerable_from_source:
            # Unanswerable queries: weighted heavily toward abstention and 0 citations
            overall = round(
                0.35 * abst_acc + 0.35 * cit_prec + 0.15 * ans_rel + 0.15 * ret_rel,
                3,
            )
        else:
            # Answerable queries: balanced combination
            overall = round(
                0.25 * ans_rel + 0.15 * ret_rel + 0.20 * cit_prec + 0.15 * cit_page + 0.25 * claim_grd,
                3,
            )

        return {
            "answer_relevance": ans_rel,
            "retrieval_relevance": ret_rel,
            "citation_precision": cit_prec,
            "citation_page_accuracy": cit_page,
            "claim_grounding": claim_grd,
            "abstention_accuracy": abst_acc,
            "overall": overall,
        }
