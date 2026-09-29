"""
Citation Validation Engine.
Enforces the core rule: NO SOURCE, NO SENTENCE.
Validates that every single sentence references real supplied source IDs.
Filters out hallucinated citations, strips uncited claims, and detects refusals.
"""

from dataclasses import dataclass
import re
from typing import Dict, List, Set, Tuple
from uuid import UUID

from app.core.logging import get_logger
from app.rag.retrieval import RetrievedChunk

logger = get_logger(__name__)


@dataclass
class ValidatedSentence:
    text: str
    source_ids: List[int]
    quotes: List[str]  # exact quote or chunk snippet backing the sentence


@dataclass
class CitationValidationResult:
    is_valid: bool
    not_found: bool
    sentences: List[ValidatedSentence]
    clean_answer_text: str
    rejected_sentences: List[str]
    hallucinated_ids: List[int]
    citation_records: List[Dict]  # Ready to be inserted into DB citations table


class CitationValidator:
    """Strict validator for LLM-generated citation sentences."""

    def __init__(self, allowed_chunks: List[RetrievedChunk]) -> None:
        self.chunk_by_source_id: Dict[int, RetrievedChunk] = {
            c.source_id: c for c in allowed_chunks
        }
        self.valid_source_ids: Set[int] = set(self.chunk_by_source_id.keys())

    def validate(
        self,
        raw_response: dict | str,
        message_id: UUID | None = None,
    ) -> CitationValidationResult:
        """
        Validates model output against allowed source IDs.
        Handles both structured JSON output and Markdown text with [n] citation markers.
        """
        # 1. Check if model signaled refusal / not_found
        if isinstance(raw_response, dict):
            if raw_response.get("not_found") is True:
                return CitationValidationResult(
                    is_valid=True,
                    not_found=True,
                    sentences=[],
                    clean_answer_text="I could not find the answer in the provided documents.",
                    rejected_sentences=[],
                    hallucinated_ids=[],
                    citation_records=[],
                )
            raw_sentences = raw_response.get("sentences", [])
        else:
            # Parse text into sentences with bracketed citations e.g. "Sentence text. [1][2]"
            raw_sentences = self._parse_text_into_sentences(str(raw_response))

        if not raw_sentences:
            return CitationValidationResult(
                is_valid=True,
                not_found=True,
                sentences=[],
                clean_answer_text="I could not find the answer in the provided documents.",
                rejected_sentences=[],
                hallucinated_ids=[],
                citation_records=[],
            )

        validated_sentences: List[ValidatedSentence] = []
        rejected_sentences: List[str] = []
        hallucinated_ids: List[int] = []
        citation_records: List[Dict] = []

        for item in raw_sentences:
            if isinstance(item, dict):
                text_content = item.get("text", "").strip()
                ids = item.get("source_ids", [])
            else:
                text_content = str(item).strip()
                ids = self._extract_bracket_citations(text_content)
                text_content = re.sub(r"\[\d+\]", "", text_content).strip()

            if not text_content:
                continue

            # Check rule: NO SOURCE, NO SENTENCE
            if not ids:
                logger.warning("Rejected uncited sentence", sentence=text_content)
                rejected_sentences.append(text_content)
                continue

            # Filter valid vs hallucinated IDs
            valid_ids_for_sentence: List[int] = []
            quotes_for_sentence: List[str] = []

            for sid in ids:
                if sid in self.valid_source_ids:
                    valid_ids_for_sentence.append(sid)
                    chunk = self.chunk_by_source_id[sid]
                    # Extract best matching quote or representative snippet from chunk
                    quote_snippet = self._extract_supporting_quote(text_content, chunk.text)
                    quotes_for_sentence.append(quote_snippet)

                    if message_id:
                        citation_records.append({
                            "message_id": message_id,
                            "chunk_id": chunk.chunk_id,
                            "marker": sid,
                            "quote": quote_snippet,
                            "page": chunk.page_start,
                        })
                else:
                    logger.warning("Detected hallucinated citation ID", hallucinated_id=sid, sentence=text_content)
                    hallucinated_ids.append(sid)

            if not valid_ids_for_sentence:
                # All citations were hallucinated!
                rejected_sentences.append(text_content)
                continue

            validated_sentences.append(
                ValidatedSentence(
                    text=text_content,
                    source_ids=valid_ids_for_sentence,
                    quotes=quotes_for_sentence,
                )
            )

        # If no valid cited sentences survived, return not_found=True
        if not validated_sentences:
            return CitationValidationResult(
                is_valid=False,
                not_found=True,
                sentences=[],
                clean_answer_text="I could not find the answer in the provided documents.",
                rejected_sentences=rejected_sentences,
                hallucinated_ids=hallucinated_ids,
                citation_records=[],
            )

        # Assemble clean display text formatted with clickable markers [1], [2]
        formatted_parts = []
        for s in validated_sentences:
            markers = "".join(f" [{sid}]" for sid in s.source_ids)
            formatted_parts.append(f"{s.text}{markers}")

        clean_text = " ".join(formatted_parts)

        return CitationValidationResult(
            is_valid=len(rejected_sentences) == 0 and len(hallucinated_ids) == 0,
            not_found=False,
            sentences=validated_sentences,
            clean_answer_text=clean_text,
            rejected_sentences=rejected_sentences,
            hallucinated_ids=hallucinated_ids,
            citation_records=citation_records,
        )

    def _extract_bracket_citations(self, text: str) -> List[int]:
        """Extract [1], [2] citation markers from string."""
        matches = re.findall(r"\[(\d+)\]", text)
        return [int(m) for m in matches]

    def _parse_text_into_sentences(self, text: str) -> List[dict]:
        """Split unformatted model response into sentences with attached citation markers."""
        # Regex matches sentence ending with punctuation optionally followed by [n] markers
        sentence_regex = re.compile(r"([^.!?]+[.!?]+(?:\s*\[\d+\])*)")
        raw_chunks = sentence_regex.findall(text)
        if not raw_chunks:
            raw_chunks = [text]

        results = []
        for chunk in raw_chunks:
            c_clean = chunk.strip()
            if not c_clean:
                continue
            ids = self._extract_bracket_citations(c_clean)
            clean_s = re.sub(r"\[\d+\]", "", c_clean).strip()
            results.append({"text": clean_s, "source_ids": ids})
        return results

    def _extract_supporting_quote(self, sentence_text: str, chunk_text: str) -> str:
        """Find the most relevant sentence or phrase in chunk_text to use as citation quote."""
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", chunk_text) if s.strip()]
        if not sentences:
            return chunk_text[:200]

        # Calculate word overlap
        sentence_words = set(re.findall(r"\w+", sentence_text.lower()))
        best_sentence = sentences[0]
        max_overlap = -1

        for s in sentences:
            s_words = set(re.findall(r"\w+", s.lower()))
            overlap = len(sentence_words & s_words)
            if overlap > max_overlap:
                max_overlap = overlap
                best_sentence = s

        return best_sentence
