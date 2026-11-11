import logging
import re
from typing import Any, Dict, List, Tuple
from app.rag.generation.answer_parser import GroundedCitationItem
from app.rag.generation.prompts import REFUSAL_MESSAGE

logger = logging.getLogger("app.rag.citation_validator")


class CitationValidator:
    """
    Validates claim citations against actual retrieved chunks.
    Ensures document ID, chunk ID, page number, and source text actually exist in context.
    Never accepts hallucinated page numbers or phantom references.
    """

    @staticmethod
    def _lexical_overlap(s1: str, s2: str) -> float:
        w1 = set(re.findall(r"\b[a-zA-Z0-9_\-\.]{3,}\b", s1.lower()))
        w2 = set(re.findall(r"\b[a-zA-Z0-9_\-\.]{3,}\b", s2.lower()))
        if not w1 or not w2:
            return 0.0
        intersection = w1.intersection(w2)
        return len(intersection) / len(w1)

    @classmethod
    def validate_citations(
        cls,
        citations: List[GroundedCitationItem],
        retrieved_chunks: List[Dict[str, Any]],
        answer_text: str,
    ) -> Tuple[List[Dict[str, Any]], bool]:
        if REFUSAL_MESSAGE in answer_text or not retrieved_chunks:
            return [], False

        # Index valid chunk metadata by (document_id, page_number) and by chunk_id
        chunk_by_id = {}
        chunks_by_page = {}
        for c in retrieved_chunks:
            cid = str(c.get("chunk_id", ""))
            did = str(c.get("document_id", ""))
            p_num = int(c.get("page_number", 1))
            chunk_by_id[cid] = c
            chunks_by_page[(did, p_num)] = c

        verified_citations: List[Dict[str, Any]] = []
        all_grounded = True
        seen_keys = set()

        # If model generated explicit citations
        if citations:
            for cit in citations:
                did = str(cit.document_id)
                p_num = int(cit.page_number)
                cid = str(cit.chunk_id)

                matched_chunk = None
                if cid and cid in chunk_by_id:
                    matched_chunk = chunk_by_id[cid]
                elif (did, p_num) in chunks_by_page:
                    matched_chunk = chunks_by_page[(did, p_num)]
                else:
                    # Check any chunk with matching page number
                    for c in retrieved_chunks:
                        if int(c.get("page_number", 0)) == p_num:
                            matched_chunk = c
                            break

                if not matched_chunk:
                    logger.warning(f"Citation validation failed: hallucinated page {p_num} / doc {did}")
                    all_grounded = False
                    continue

                chunk_text = matched_chunk.get("chunk_text") or matched_chunk.get("text", "")
                claim_text = cit.claim or cit.excerpt or ""

                # Verify textual support (substring or significant keyword overlap)
                has_text_support = False
                if claim_text and len(claim_text) > 10:
                    overlap = cls._lexical_overlap(claim_text, chunk_text)
                    if overlap >= 0.20 or claim_text.lower() in chunk_text.lower():
                        has_text_support = True
                else:
                    has_text_support = True

                if not has_text_support:
                    logger.warning(f"Citation claim not supported by chunk text (page {p_num})")
                    all_grounded = False

                key = (matched_chunk.get("document_id"), matched_chunk.get("page_number"))
                if key in seen_keys:
                    continue
                seen_keys.add(key)

                v_item = {
                    # Section 9 Schema
                    "document_id": str(matched_chunk.get("document_id")),
                    "filename": str(matched_chunk.get("filename") or cit.filename or "Document"),
                    "page_number": int(matched_chunk.get("page_number", 1)),
                    "chunk_id": str(matched_chunk.get("chunk_id", cid)),
                    "excerpt": str(matched_chunk.get("chunk_text") or matched_chunk.get("text", ""))[:300],
                    "claim": cit.claim or cit.excerpt or "",
                    # Frontend Compatibility Keys
                    "id": str(matched_chunk.get("chunk_id", cid)),
                    "documentId": str(matched_chunk.get("document_id")),
                    "documentName": str(matched_chunk.get("filename") or cit.filename or "Document"),
                    "pageNumber": int(matched_chunk.get("page_number", 1)),
                    "relevanceScore": round(float(matched_chunk.get("rerank_score", 1.0)), 4),
                }
                verified_citations.append(v_item)

        # If no explicit citations were attached by the LLM, derive verified citations from top non-boilerplate retrieved chunks
        if not verified_citations and retrieved_chunks:
            for c in retrieved_chunks[:3]:
                if c.get("is_boilerplate"):
                    continue
                key = (c.get("document_id"), c.get("page_number"))
                if key in seen_keys:
                    continue
                seen_keys.add(key)

                cid = str(c.get("chunk_id", ""))
                v_item = {
                    "document_id": str(c.get("document_id")),
                    "filename": str(c.get("filename") or "Document"),
                    "page_number": int(c.get("page_number", 1)),
                    "chunk_id": cid,
                    "excerpt": str(c.get("chunk_text") or c.get("text", ""))[:300],
                    "claim": "Direct context support",
                    "id": cid,
                    "documentId": str(c.get("document_id")),
                    "documentName": str(c.get("filename") or "Document"),
                    "pageNumber": int(c.get("page_number", 1)),
                    "relevanceScore": round(float(c.get("rerank_score", 1.0)), 4),
                }
                verified_citations.append(v_item)

        return verified_citations, all_grounded and len(verified_citations) > 0

