import re
from typing import Any, Dict, List
from app.rag.generation.answer_parser import GroundedCitationItem


class CitationExtractor:
    """Extracts claim-level citations from parsed responses or generated text."""

    @staticmethod
    def extract_citations(
        raw_citations: List[GroundedCitationItem],
        answer_text: str,
        retrieved_chunks: List[Dict[str, Any]],
    ) -> List[GroundedCitationItem]:
        if raw_citations:
            return raw_citations

        # Fallback: regex search for [Source X, Page Y] or (Doc, p. Y) in answer text
        extracted: List[GroundedCitationItem] = []
        pattern = re.compile(r"(?:\[Source\s*(\d+).*?Page[:\s]*(\d+)\])|(?:\(([^,)]+).*?p\.?\s*(\d+)\))", re.IGNORECASE)

        chunk_by_idx = {i: c for i, c in enumerate(retrieved_chunks, start=1)}
        for match in pattern.finditer(answer_text):
            src_num = match.group(1)
            p_num = match.group(2) or match.group(4)
            doc_name = match.group(3)

            matched_chunk = None
            if src_num and int(src_num) in chunk_by_idx:
                matched_chunk = chunk_by_idx[int(src_num)]
            elif p_num:
                # Find chunk matching page number
                for c in retrieved_chunks:
                    if int(c.get("page_number", 0)) == int(p_num):
                        matched_chunk = c
                        break

            if matched_chunk:
                extracted.append(
                    GroundedCitationItem(
                        claim=answer_text[max(0, match.start() - 60) : match.end()],
                        document_id=str(matched_chunk.get("document_id", "")),
                        filename=str(matched_chunk.get("filename") or doc_name or "Document"),
                        page_number=int(matched_chunk.get("page_number", 1)),
                        chunk_id=str(matched_chunk.get("chunk_id", "")),
                        excerpt=str(matched_chunk.get("chunk_text") or matched_chunk.get("text", ""))[:280],
                    )
                )

        return extracted

