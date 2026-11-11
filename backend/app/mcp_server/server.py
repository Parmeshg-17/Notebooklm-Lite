"""
Custom MCP Server implementation for NotebookLM Lite using the Model Context Protocol SDK.
Exposes 7 standardized tools for retrieval, citation inspection, document reading,
and multi-source comparison.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from mcp.server.mcpserver import MCPServer

from app.mcp_server.tools import (
    search_documents_impl,
    get_document_impl,
    get_page_content_impl,
    search_citations_impl,
    compare_sources_impl,
    summarize_document_impl,
    get_notebook_sources_impl,
)

logger = logging.getLogger("app.mcp_server.server")

# Alias for backwards compatibility with FastMCP patterns
FastMCP = MCPServer

# Initialize official MCP Server
notebooklm_mcp_server = MCPServer("notebooklm-mcp")


@notebooklm_mcp_server.tool()
async def search_documents(
    notebook_id: str,
    query: str,
    document_ids: Optional[List[str]] = None,
    user_id: Optional[str] = None,
    top_k: int = 5,
) -> str:
    """Search for relevant document passages within a notebook using hybrid retrieval."""
    res = await search_documents_impl(
        notebook_id=notebook_id,
        query=query,
        document_ids=document_ids,
        user_id=user_id,
        top_k=top_k,
    )
    return json.dumps(res)


@notebooklm_mcp_server.tool()
async def get_document(
    document_id: str,
    notebook_id: str,
    user_id: Optional[str] = None,
) -> str:
    """Retrieve metadata, page count, and indexing status of a document."""
    res = await get_document_impl(
        document_id=document_id,
        notebook_id=notebook_id,
        user_id=user_id,
    )
    return json.dumps(res)


@notebooklm_mcp_server.tool()
async def get_page_content(
    page_number: int,
    notebook_id: str,
    document_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> str:
    """Retrieve the exact text and passages from a specific page of a document."""
    res = await get_page_content_impl(
        document_id=document_id,
        page_number=page_number,
        notebook_id=notebook_id,
        user_id=user_id,
    )
    return json.dumps(res)


@notebooklm_mcp_server.tool()
async def search_citations(
    notebook_id: str,
    query: str,
    user_id: Optional[str] = None,
) -> str:
    """Search for exact citation candidate excerpts matching a query."""
    res = await search_citations_impl(
        notebook_id=notebook_id,
        query=query,
        user_id=user_id,
    )
    return json.dumps(res)


@notebooklm_mcp_server.tool()
async def compare_sources(
    notebook_id: str,
    question: str,
    document_ids: Optional[List[str]] = None,
    user_id: Optional[str] = None,
) -> str:
    """Retrieve and partition evidence across multiple documents to compare viewpoints or findings."""
    res = await compare_sources_impl(
        notebook_id=notebook_id,
        question=question,
        document_ids=document_ids,
        user_id=user_id,
    )
    return json.dumps(res)


@notebooklm_mcp_server.tool()
async def summarize_document(
    notebook_id: str,
    document_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> str:
    """Generate structured summary excerpts for an entire document."""
    res = await summarize_document_impl(
        document_id=document_id,
        notebook_id=notebook_id,
        user_id=user_id,
    )
    return json.dumps(res)


@notebooklm_mcp_server.tool()
async def get_notebook_sources(
    notebook_id: str,
    user_id: Optional[str] = None,
) -> str:
    """List all available documents and their indexing statuses in a notebook."""
    res = await get_notebook_sources_impl(
        notebook_id=notebook_id,
        user_id=user_id,
    )
    return json.dumps(res)
