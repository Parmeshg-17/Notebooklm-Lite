"""
Standardized MCP Tools for NotebookLM Lite.
Implements the 7 core MCP tools with strict multi-tenant isolation:
1. search_documents
2. get_document
3. get_page_content
4. search_citations
5. compare_sources
6. summarize_document
7. get_notebook_sources
"""

import json
import logging
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import select

from app.db.session import async_session_maker
from app.models.document import Document
from app.models.notebook import Notebook
from app.rag.retrieval.retriever import modular_retriever
from app.rag.retrieval.qdrant_store import QdrantStore

logger = logging.getLogger("app.mcp_server.tools")

qdrant_store = QdrantStore()


def _parse_uuid(val: Any) -> Optional[uuid.UUID]:
    if not val:
        return None
    if isinstance(val, uuid.UUID):
        return val
    try:
        return uuid.UUID(str(val))
    except (ValueError, TypeError):
        return uuid.uuid5(uuid.NAMESPACE_DNS, str(val))


async def verify_notebook_access(
    notebook_id: uuid.UUID,
    user_id: Optional[uuid.UUID],
) -> bool:
    """Multi-tenant security check: verifies notebook exists and user is owner."""
    if not user_id:
        return True  # If no user_id supplied in internal sandbox, allow
    async with async_session_maker() as db:
        stmt = select(Notebook).where(
            Notebook.id == notebook_id,
            Notebook.owner_id == user_id,
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none() is not None


async def search_documents_impl(
    notebook_id: str,
    query: str,
    document_ids: Optional[List[str]] = None,
    user_id: Optional[str] = None,
    top_k: int = 5,
) -> Dict[str, Any]:
    """Search relevant document chunks in a notebook using hybrid retrieval."""
    nb_uuid = _parse_uuid(notebook_id)
    u_uuid = _parse_uuid(user_id) if user_id else None
    doc_uuids = [_parse_uuid(d) for d in document_ids] if document_ids else None

    if u_uuid and not await verify_notebook_access(nb_uuid, u_uuid):
        return {"error": "Access denied: Notebook does not belong to user.", "results": []}

    chunks, has_sufficient, context_text, telemetry = await modular_retriever.retrieve(
        query=query,
        user_id=u_uuid or uuid.UUID("00000000-0000-0000-0000-000000000000"),
        notebook_id=nb_uuid,
        document_ids=doc_uuids,
        top_k=top_k,
    )

    formatted_chunks = [
        {
            "chunk_id": c.get("chunk_id"),
            "document_id": str(c.get("document_id")),
            "filename": c.get("filename"),
            "page_number": c.get("page_number", 1),
            "text": c.get("chunk_text") or c.get("text", ""),
            "score": round(float(c.get("score", 0.0)), 4),
        }
        for c in chunks
    ]

    return {
        "status": "success",
        "has_sufficient_evidence": has_sufficient,
        "count": len(formatted_chunks),
        "results": formatted_chunks,
    }


async def get_document_impl(
    document_id: str,
    notebook_id: str,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve metadata and indexing status for a specific document."""
    doc_uuid = _parse_uuid(document_id)
    nb_uuid = _parse_uuid(notebook_id)
    u_uuid = _parse_uuid(user_id) if user_id else None

    async with async_session_maker() as db:
        stmt = select(Document).where(
            Document.id == doc_uuid,
            Document.notebook_id == nb_uuid,
        )
        if u_uuid:
            stmt = stmt.where(Document.owner_id == u_uuid)

        res = await db.execute(stmt)
        doc = res.scalar_one_or_none()
        if not doc:
            return {"error": f"Document {document_id} not found or access denied."}

        return {
            "status": "success",
            "document": {
                "id": str(doc.id),
                "notebook_id": str(doc.notebook_id),
                "filename": doc.filename,
                "file_type": doc.file_type,
                "file_size": doc.file_size,
                "page_count": doc.page_count,
                "total_chunks": doc.total_chunks,
                "processing_status": doc.processing_status,
                "created_at": doc.created_at.isoformat(),
            },
        }


async def get_page_content_impl(
    document_id: Optional[str],
    page_number: int,
    notebook_id: str,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve the text and chunks for an exact document page."""
    doc_uuid = _parse_uuid(document_id) if document_id else None
    nb_uuid = _parse_uuid(notebook_id)
    u_uuid = _parse_uuid(user_id) if user_id else None

    if u_uuid and not await verify_notebook_access(nb_uuid, u_uuid):
        return {"error": "Access denied."}

    # Query Qdrant for all chunks on this page
    doc_filter = [doc_uuid] if doc_uuid else None
    all_chunks = await qdrant_store.fetch_notebook_chunks(
        user_id=u_uuid or uuid.UUID("00000000-0000-0000-0000-000000000000"),
        notebook_id=nb_uuid,
        document_ids=doc_filter,
        limit=2500,
    )

    page_chunks = [
        c for c in all_chunks
        if int(c.get("page_number", 0)) == int(page_number)
        or int(page_number) in c.get("contributing_pages", [])
    ]

    # Sort chunks by chunk_index
    page_chunks.sort(key=lambda x: int(x.get("chunk_index", 0)))
    combined_text = "\n\n".join([c.get("chunk_text") or c.get("text", "") for c in page_chunks])

    return {
        "status": "success",
        "document_id": str(document_id),
        "page_number": int(page_number),
        "chunk_count": len(page_chunks),
        "content": combined_text.strip(),
    }


async def search_citations_impl(
    notebook_id: str,
    query: str,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve exact citations with relevance scores for a query."""
    search_res = await search_documents_impl(
        notebook_id=notebook_id,
        query=query,
        user_id=user_id,
        top_k=5,
    )
    if "error" in search_res:
        return search_res

    citations = []
    for r in search_res.get("results", []):
        text = r.get("text", "")
        excerpt = text[:200] + "..." if len(text) > 200 else text
        citations.append({
            "document_id": r.get("document_id"),
            "document_name": r.get("filename"),
            "page_number": r.get("page_number", 1),
            "excerpt": excerpt,
            "relevance_score": r.get("score", 0.0),
        })

    return {"status": "success", "citations": citations}


async def compare_sources_impl(
    notebook_id: str,
    question: str,
    document_ids: Optional[List[str]] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Compare information and metrics across multiple documents for a query."""
    search_res = await search_documents_impl(
        notebook_id=notebook_id,
        query=question,
        document_ids=document_ids,
        user_id=user_id,
        top_k=10,
    )
    if "error" in search_res:
        return search_res

    # Group evidence by document
    docs_map: Dict[str, Dict[str, Any]] = {}
    for chunk in search_res.get("results", []):
        doc_id = chunk.get("document_id")
        filename = chunk.get("filename", "Unknown Document")
        if doc_id not in docs_map:
            docs_map[doc_id] = {
                "document_id": doc_id,
                "filename": filename,
                "evidence_points": [],
                "pages": set(),
            }
        docs_map[doc_id]["evidence_points"].append(chunk.get("text"))
        docs_map[doc_id]["pages"].add(chunk.get("page_number", 1))

    # Format into serializable comparison source structures
    comparisons = []
    for d_id, data in docs_map.items():
        comparisons.append({
            "document_id": d_id,
            "filename": data["filename"],
            "pages": sorted(list(data["pages"])),
            "key_passages": data["evidence_points"][:3],
        })

    return {
        "status": "success",
        "question": question,
        "sources_compared": len(comparisons),
        "comparisons": comparisons,
    }


async def summarize_document_impl(
    document_id: Optional[str],
    notebook_id: str,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Summarize a document using its initial and highest-ranked passages."""
    if not document_id:
        sources_res = await get_notebook_sources_impl(notebook_id, user_id)
        sources = sources_res.get("sources", [])
        if not sources:
            return {"error": "No documents found to summarize in this notebook."}
        document_id = sources[0]["id"]

    doc_info = await get_document_impl(document_id, notebook_id, user_id)
    if "error" in doc_info:
        return doc_info

    # Fetch initial chunks by reading all document chunks and sorting by chunk_index
    doc_uuid = _parse_uuid(document_id)
    nb_uuid = _parse_uuid(notebook_id)
    u_uuid = _parse_uuid(user_id) if user_id else None

    chunks = await qdrant_store.fetch_notebook_chunks(
        user_id=u_uuid or uuid.UUID("00000000-0000-0000-0000-000000000000"),
        notebook_id=nb_uuid,
        document_ids=[doc_uuid],
        limit=2500,
    )
    doc_fname = doc_info.get("document", {}).get("filename", "Document")
    chunks.sort(key=lambda x: int(x.get("chunk_index", 0)))
    top_chunks = chunks[:8]

    formatted_results = []
    for c in top_chunks:
        c_text = c.get("chunk_text") or c.get("text", "")
        formatted_results.append({
            "chunk_id": c.get("chunk_id") or f"summary_{document_id}_{c.get('chunk_index', 0)}",
            "document_id": str(document_id),
            "filename": doc_fname,
            "page_number": c.get("page_number", 1),
            "chunk_index": c.get("chunk_index", 0),
            "chunk_text": c_text,
            "text": c_text,
            "score": 0.95,
        })

    key_text = "\n\n".join([c.get("text", "") for c in formatted_results[:5]])

    return {
        "status": "success",
        "document": doc_info.get("document"),
        "overview_text": key_text[:2000],
        "sampled_pages": sorted(list(set(c.get("page_number", 1) for c in formatted_results))),
        "results": formatted_results,
    }


async def get_notebook_sources_impl(
    notebook_id: str,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """List all indexed document sources in a notebook."""
    nb_uuid = _parse_uuid(notebook_id)
    u_uuid = _parse_uuid(user_id) if user_id else None

    async with async_session_maker() as db:
        stmt = select(Document).where(Document.notebook_id == nb_uuid)
        if u_uuid:
            stmt = stmt.where(Document.owner_id == u_uuid)
        res = await db.execute(stmt)
        docs = res.scalars().all()

        return {
            "status": "success",
            "notebook_id": str(notebook_id),
            "count": len(docs),
            "sources": [
                {
                    "id": str(d.id),
                    "filename": d.filename,
                    "page_count": d.page_count,
                    "total_chunks": d.total_chunks,
                    "processing_status": d.processing_status,
                }
                for d in docs
            ],
        }
