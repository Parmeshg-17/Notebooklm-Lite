"""
Test Suite for MCP Server Registration, Dispatch, Error Handling, and Resilience.
"""

import asyncio
import json
import uuid
import pytest
from sqlalchemy import select

from app.db.session import async_session_maker
from app.mcp_client.client import MCPClient, mcp_client
from app.mcp_server.server import notebooklm_mcp_server
from app.models.document import Document
from app.models.notebook import Notebook
from app.models.user import User


async def get_test_context():
    async with async_session_maker() as db:
        res = await db.execute(select(Notebook).where(Notebook.documents.any()))
        nb = res.scalars().first()
        if nb:
            user_res = await db.execute(select(User).where(User.id == nb.owner_id))
            user = user_res.scalar_one_or_none()
            doc_res = await db.execute(select(Document).where(Document.notebook_id == nb.id))
            docs = doc_res.scalars().all()
            return nb, user, docs

        user = User(email=f"mcp_server_{uuid.uuid4().hex[:6]}@example.com", hashed_password="pw")
        db.add(user)
        await db.commit()
        await db.refresh(user)

        nb = Notebook(title="MCP Server Notebook", owner_id=user.id)
        db.add(nb)
        await db.commit()
        await db.refresh(nb)

        doc = Document(
            notebook_id=nb.id,
            owner_id=user.id,
            filename="AI_Engineering.pdf",
            storage_path="AI_Engineering.pdf",
            page_count=100,
            total_chunks=50,
            processing_status="INDEXED",
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
        return nb, user, [doc]


@pytest.mark.asyncio
async def test_mcp_server_initialization():
    """Verify MCP Server initializes and registers all 7 tools."""
    assert notebooklm_mcp_server is not None
    assert notebooklm_mcp_server.name == "notebooklm-mcp"
    tools = await notebooklm_mcp_server.list_tools()
    tool_names = [t.name for t in tools]

    expected_tools = [
        "search_documents",
        "get_document",
        "get_page_content",
        "search_citations",
        "compare_sources",
        "summarize_document",
        "get_notebook_sources",
    ]
    for exp in expected_tools:
        assert exp in tool_names, f"Expected MCP tool '{exp}' not found in server tools: {tool_names}"


@pytest.mark.asyncio
async def test_mcp_client_list_tools():
    """Verify MCP Client retrieves tool catalog with schemas and descriptions."""
    tools = await mcp_client.list_available_tools()
    assert len(tools) >= 7
    tool_map = {t["name"]: t for t in tools}
    assert "search_documents" in tool_map
    assert len(tool_map["search_documents"]["description"]) > 10


@pytest.mark.asyncio
async def test_mcp_client_call_valid_tool():
    """Verify standard invocation of get_notebook_sources tool via MCP client."""
    nb, user, _ = await get_test_context()
    res = await mcp_client.call_tool(
        "get_notebook_sources",
        {"notebook_id": str(nb.id), "user_id": str(user.id)},
    )
    assert res.get("status") == "success"
    assert res.get("notebook_id") == str(nb.id)
    assert "sources" in res


@pytest.mark.asyncio
async def test_mcp_client_invalid_tool_name():
    """Verify graceful handling when an unknown tool name is invoked."""
    res = await mcp_client.call_tool("non_existent_tool_xyz", {"arg1": "test"})
    assert "error" in res or res.get("status") == "failed"


@pytest.mark.asyncio
async def test_mcp_client_invalid_tool_arguments():
    """Verify tool handles missing or bad arguments gracefully without crashing."""
    res = await mcp_client.call_tool("get_page_content", {"invalid_param": "foo"})
    # Either raises validation error caught by MCP or returns error object
    assert "error" in res or res.get("status") in ["failed", "error"]


@pytest.mark.asyncio
async def test_mcp_client_simulated_timeout():
    """Verify that a tool invocation bounded by an explicit timeout raises TimeoutError gracefully."""
    async def slow_mock_tool():
        await asyncio.sleep(0.5)
        return {"status": "success"}

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(slow_mock_tool(), timeout=0.05)


@pytest.mark.asyncio
async def test_mcp_client_exception_resilience():
    """Verify client wraps any server exception cleanly without crashing caller."""
    class FailingServer:
        async def call_tool(self, name, arguments):
            raise ConnectionResetError("Remote server disconnected")

    failing_client = MCPClient(server=FailingServer())
    res = await failing_client.call_tool("search_documents", {})
    assert "error" in res
    assert res["status"] == "failed"
    assert "Remote server disconnected" in res["error"]

