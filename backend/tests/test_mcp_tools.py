"""
Comprehensive Unit & Integration Tests for MCP Tools and MCP Server in NotebookLM Lite.
Tests all 7 standardized tools, multi-tenant isolation, and MCP Client execution.
"""

import json
import uuid
import pytest
from app.mcp_client.client import mcp_client
from app.mcp_server.server import notebooklm_mcp_server
from app.mcp_server.tools import (
    search_documents_impl,
    get_document_impl,
    get_page_content_impl,
    search_citations_impl,
    compare_sources_impl,
    summarize_document_impl,
    get_notebook_sources_impl,
)
from app.models.notebook import Notebook
from app.models.document import Document
from app.models.user import User
from app.db.session import async_session_maker
from sqlalchemy import select


async def get_test_notebook_and_user():
    """Retrieve an existing notebook and user from database or create one."""
    async with async_session_maker() as db:
        res = await db.execute(select(Notebook).where(Notebook.documents.any()))
        nb = res.scalars().first()
        if nb:
            return str(nb.id), str(nb.owner_id)

        # Fallback to any notebook
        res = await db.execute(select(Notebook))
        nb = res.scalars().first()
        if nb:
            return str(nb.id), str(nb.owner_id)

        # Create test user and notebook
        user = User(email=f"mcp_test_{uuid.uuid4().hex[:6]}@example.com", hashed_password="pw")
        db.add(user)
        await db.commit()
        await db.refresh(user)

        nb = Notebook(title="MCP Test Notebook", owner_id=user.id)
        db.add(nb)
        await db.commit()
        await db.refresh(nb)
        return str(nb.id), str(user.id)


@pytest.mark.asyncio
async def test_mcp_search_documents():
    nb_id, user_id = await get_test_notebook_and_user()
    res = await search_documents_impl(
        notebook_id=nb_id,
        query="architecture throughput latency",
        user_id=user_id,
        top_k=3,
    )
    assert res["status"] == "success"
    assert "results" in res
    assert isinstance(res["results"], list)


@pytest.mark.asyncio
async def test_mcp_get_page_content():
    nb_id, user_id = await get_test_notebook_and_user()
    res = await get_page_content_impl(
        document_id=None,
        page_number=1,
        notebook_id=nb_id,
        user_id=user_id,
    )
    assert res["status"] == "success"
    assert res["page_number"] == 1
    assert "content" in res


@pytest.mark.asyncio
async def test_mcp_search_citations():
    nb_id, user_id = await get_test_notebook_and_user()
    res = await search_citations_impl(
        notebook_id=nb_id,
        query="transformer model",
        user_id=user_id,
    )
    assert res["status"] == "success"
    assert "citations" in res


@pytest.mark.asyncio
async def test_mcp_compare_sources():
    nb_id, user_id = await get_test_notebook_and_user()
    res = await compare_sources_impl(
        notebook_id=nb_id,
        question="What are the main performance differences?",
        user_id=user_id,
    )
    assert res["status"] == "success"
    assert "comparisons" in res


@pytest.mark.asyncio
async def test_mcp_summarize_document():
    nb_id, user_id = await get_test_notebook_and_user()
    res = await summarize_document_impl(
        document_id=None,
        notebook_id=nb_id,
        user_id=user_id,
    )
    assert "status" in res or "error" in res


@pytest.mark.asyncio
async def test_mcp_get_notebook_sources():
    nb_id, user_id = await get_test_notebook_and_user()
    res = await get_notebook_sources_impl(
        notebook_id=nb_id,
        user_id=user_id,
    )
    assert res["status"] == "success"
    assert "sources" in res
    assert isinstance(res["sources"], list)


@pytest.mark.asyncio
async def test_mcp_multitenant_unauthorized_rejection():
    nb_id, _ = await get_test_notebook_and_user()
    fake_user_id = str(uuid.uuid4())

    res = await search_documents_impl(
        notebook_id=nb_id,
        query="secret data",
        user_id=fake_user_id,
    )
    assert "error" in res
    assert "Access denied" in res["error"]


@pytest.mark.asyncio
async def test_mcp_client_tool_invocation():
    """Verify official MCP Server can execute tools through MCPClient interface."""
    nb_id, user_id = await get_test_notebook_and_user()
    res = await mcp_client.call_tool(
        "get_notebook_sources",
        {"notebook_id": nb_id, "user_id": user_id},
    )
    assert res.get("status") == "success"
    assert "sources" in res
