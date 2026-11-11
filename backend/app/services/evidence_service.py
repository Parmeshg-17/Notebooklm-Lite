"""
Evidence Collection and Synthesis Service for NotebookLM Lite.
Structures retrieved passages, deduplicates chunks, and prepares clean context.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("app.services.evidence_service")


class EvidenceService:
    """
    Manages cross-document evidence aggregation, deduplication, and context construction.
    """

    @classmethod
    def aggregate_evidence(
        cls,
        tool_results: List[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any], str, bool]:
        """
        Aggregates chunks from tool execution results.
        Returns:
            - unique_chunks: List of deduplicated chunk dicts
            - evidence_matrix: Document-grouped evidence
            - context_text: Structured context string for LLM
            - has_sufficient: Boolean indicating if evidence meets grounding criteria
        """
        raw_chunks: List[Dict[str, Any]] = []

        for tr in tool_results:
            res = tr.get("result", {})
            # From search_documents
            if "results" in res and isinstance(res["results"], list):
                raw_chunks.extend(res["results"])
            # From get_page_content
            elif "content" in res and res.get("content"):
                raw_chunks.append({
                    "chunk_id": f"page_{res.get('document_id')}_{res.get('page_number')}",
                    "document_id": res.get("document_id"),
                    "filename": f"Document (p. {res.get('page_number')})",
                    "page_number": res.get("page_number", 1),
                    "text": res.get("content"),
                    "score": 1.0,
                })
            # From compare_sources
            elif "comparisons" in res and isinstance(res["comparisons"], list):
                for comp in res["comparisons"]:
                    doc_id = comp.get("document_id")
                    fn = comp.get("filename")
                    for idx, passage in enumerate(comp.get("key_passages", [])):
                        raw_chunks.append({
                            "chunk_id": f"comp_{doc_id}_{idx}",
                            "document_id": doc_id,
                            "filename": fn,
                            "page_number": comp.get("pages", [1])[0] if comp.get("pages") else 1,
                            "text": passage,
                            "score": 0.85,
                        })
            # From summarize_document
            elif "overview_text" in res and res.get("overview_text"):
                doc_meta = res.get("document") or {}
                raw_chunks.append({
                    "chunk_id": f"summary_{doc_meta.get('id')}",
                    "document_id": doc_meta.get("id"),
                    "filename": doc_meta.get("filename", "Summary Source"),
                    "page_number": 1,
                    "text": res.get("overview_text"),
                    "score": 0.90,
                })

        # Deduplicate chunks
        seen_keys = set()
        unique_chunks: List[Dict[str, Any]] = []
        for c in raw_chunks:
            # deduplicate by chunk_id or text prefix
            txt = (c.get("text") or c.get("chunk_text") or "").strip()
            if not txt:
                continue
            key = c.get("chunk_id") or txt[:80]
            if key not in seen_keys:
                seen_keys.add(key)
                unique_chunks.append(c)

        # Build document-grouped evidence matrix
        evidence_matrix: Dict[str, Dict[str, Any]] = {}
        for c in unique_chunks:
            d_id = str(c.get("document_id", "unknown"))
            fn = c.get("filename", "Document")
            if d_id not in evidence_matrix:
                evidence_matrix[d_id] = {
                    "document_id": d_id,
                    "filename": fn,
                    "pages": set(),
                    "chunks": [],
                }
            evidence_matrix[d_id]["pages"].add(c.get("page_number", 1))
            evidence_matrix[d_id]["chunks"].append(c)

        # Build structured context string
        context_parts: List[str] = []
        for d_id, d_data in evidence_matrix.items():
            context_parts.append(f"=== SOURCE DOCUMENT: {d_data['filename']} (ID: {d_id}) ===")
            for c in d_data["chunks"]:
                p = c.get("page_number", 1)
                text = c.get("text") or c.get("chunk_text", "")
                context_parts.append(f"[Page {p}]:\n{text}")

        context_text = "\n\n".join(context_parts)
        has_sufficient = len(unique_chunks) > 0 and len(context_text.strip()) > 30

        return unique_chunks, evidence_matrix, context_text, has_sufficient


evidence_service = EvidenceService()

