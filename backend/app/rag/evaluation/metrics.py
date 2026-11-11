from typing import List, Set


class RAGMetrics:
    @staticmethod
    def recall_at_k(retrieved_pages: List[int], expected_pages: Set[int]) -> float:
        if not expected_pages:
            return 1.0
        hits = expected_pages.intersection(set(retrieved_pages))
        return len(hits) / len(expected_pages)

    @staticmethod
    def precision_at_k(retrieved_pages: List[int], expected_pages: Set[int]) -> float:
        if not retrieved_pages:
            return 1.0 if not expected_pages else 0.0
        if not expected_pages:
            return 0.0
        hits = expected_pages.intersection(set(retrieved_pages))
        return len(hits) / len(retrieved_pages)

    @staticmethod
    def mean_reciprocal_rank(retrieved_pages: List[int], expected_pages: Set[int]) -> float:
        if not expected_pages:
            return 1.0
        for rank, p in enumerate(retrieved_pages, start=1):
            if p in expected_pages:
                return 1.0 / rank
        return 0.0

    @staticmethod
    def context_precision(retrieved_pages: List[int], expected_pages: Set[int]) -> float:
        if not retrieved_pages or not expected_pages:
            return 1.0 if not expected_pages else 0.0
        relevant_count = 0
        cumulative_precisions = []
        for rank, p in enumerate(retrieved_pages, start=1):
            if p in expected_pages:
                relevant_count += 1
                cumulative_precisions.append(relevant_count / rank)
        if not cumulative_precisions:
            return 0.0
        return sum(cumulative_precisions) / len(expected_pages)

    @staticmethod
    def answer_relevancy(answer_text: str, expected_keywords: List[str], should_refuse: bool, is_refusal: bool) -> float:
        if should_refuse:
            return 1.0 if is_refusal else 0.0
        if is_refusal:
            return 0.0
        if not expected_keywords:
            return 1.0
        ans_lower = answer_text.lower()
        matched = sum(1 for kw in expected_keywords if kw in ans_lower)
        return matched / len(expected_keywords)

    @staticmethod
    def faithfulness(is_grounded: bool, should_refuse: bool, is_refusal: bool) -> float:
        if should_refuse and is_refusal:
            return 1.0
        if should_refuse and not is_refusal:
            return 0.0
        return 1.0 if is_grounded else 0.40

    @staticmethod
    def citation_accuracy(citations: List[int], expected_pages: Set[int], should_refuse: bool) -> float:
        if should_refuse:
            return 1.0 if not citations else 0.0
        if not citations:
            return 0.0
        valid_citations = sum(1 for p in citations if p in expected_pages)
        return valid_citations / len(citations)

    @staticmethod
    def unsupported_claim_rate(citations: List[int], expected_pages: Set[int], should_refuse: bool, is_refusal: bool) -> float:
        if should_refuse:
            return 0.0 if is_refusal else 1.0
        if is_refusal:
            return 0.0
        if not citations:
            return 0.80
        invalid_citations = sum(1 for p in citations if p not in expected_pages)
        return invalid_citations / len(citations)

    @staticmethod
    def refusal_accuracy(should_refuse: bool, is_refusal: bool) -> float:
        if should_refuse:
            return 1.0 if is_refusal else 0.0
        return 1.0 if not is_refusal else 0.0

