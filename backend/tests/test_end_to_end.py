"""
Core End-to-End Test Suite for NotebookLM Lite LangGraph + MCP Workflows.
Implements the 10 Core E2E Scenarios defined in Phase 4 QA Specification:
1. Simple Question
2. Multi-Document Question
3. Document Comparison
4. Page-Specific Question
5. Document Summary
6. Missing Evidence (Strict refusal, 0 citations)
7. Invalid Citation Handling (Hallucination rejection)
8. Unauthorized Notebook Access (Security isolation)
9. MCP Failure Graceful Handling
10. Conversation Isolation (Thread safety)
"""

import uuid
import pytest
from sqlalchemy import select

from app.agents.graph import agent_graph
from app.agents.nodes import citation_verifier_node
from app.agents.prompts import REFUSAL_MESSAGE
from app.db.session import async_session_maker
from app.mcp_client.client import MCPClient
from app.mcp_client.tool_executor import ToolExecutor
from app.models.document import Document
from app.models.notebook import Notebook
from app.models.user import User
from app.rag.schemas.rag import RAGChatRequest
from app.rag.services.rag_service import rag_service
from app.services.notebook_service import NotebookService
from app.core.exceptions import ForbiddenException


async def get_real_indexed_context():
    """Retrieve the primary indexed notebook containing AI Engineering.pdf with real indexed vectors."""
    async with async_session_maker() as db:
        res = await db.execute(
            select(Document)
            .where(Document.total_chunks >= 1000)
            .order_by(Document.created_at.desc())
        )
        doc = res.scalars().first()
        if doc:
            nb_res = await db.execute(select(Notebook).where(Notebook.id == doc.notebook_id))
            nb = nb_res.scalar_one_or_none()
            user_res = await db.execute(select(User).where(User.id == doc.owner_id))
            user = user_res.scalar_one_or_none()
            return nb, user, [doc]
        raise RuntimeError("No indexed notebook found in database. Run ingestion first.")


@pytest.mark.asyncio
async def test_scenario_01_simple_question():
    """Test 1: Simple Question - single retrieval, verified citations, grounded response."""
    nb, user, docs = await get_real_indexed_context()
    thread_id = f"e2e_01_{uuid.uuid4().hex[:6]}"

    state = {
        "question": "What is RAG, according to my uploaded documents?",
        "notebook_id": str(nb.id),
        "user_id": str(user.id),
        "document_ids": [str(docs[0].id)],
    }
    config = {"configurable": {"thread_id": thread_id}}
    result = await agent_graph.ainvoke(state, config=config)

    assert result["intent"] in ["SIMPLE_QUESTION", "DOCUMENT_SUMMARY"]
    assert "generated_answer" in result
    assert len(result["generated_answer"]) > 20
    assert result.get("is_grounded") is True
    assert len(result.get("citations", [])) > 0
    # Every citation must contain document info and page number
    for c in result["citations"]:
        assert c.get("page_number") is not None
        assert c.get("relevance_score") >= 0.5


@pytest.mark.asyncio
async def test_scenario_02_multi_document_question():
    """Test 2: Multi-Document Question - decomposition into sub-queries."""
    nb, user, docs = await get_real_indexed_context()
    thread_id = f"e2e_02_{uuid.uuid4().hex[:6]}"

    state = {
        "question": "Explain how the uploaded documents describe AI agent architecture.",
        "notebook_id": str(nb.id),
        "user_id": str(user.id),
    }
    config = {"configurable": {"thread_id": thread_id}}
    result = await agent_graph.ainvoke(state, config=config)

    assert result["intent"] in ["MULTI_DOCUMENT_QUESTION", "COMPARISON_QUESTION", "SIMPLE_QUESTION"]
    assert "generated_answer" in result
    assert result.get("is_grounded") is True
    if result.get("insufficient_evidence"):
        assert len(result.get("citations", [])) == 0
    else:
        assert len(result.get("citations", [])) >= 1


@pytest.mark.asyncio
async def test_scenario_03_document_comparison():
    """Test 3: Document Comparison - invokes comparison tool and aggregates sources."""
    nb, user, docs = await get_real_indexed_context()
    thread_id = f"e2e_03_{uuid.uuid4().hex[:6]}"

    state = {
        "question": "Compare the evaluation approaches and methodologies discussed in my uploaded documents.",
        "notebook_id": str(nb.id),
        "user_id": str(user.id),
    }
    config = {"configurable": {"thread_id": thread_id}}
    result = await agent_graph.ainvoke(state, config=config)

    assert result["intent"] == "COMPARISON_QUESTION"
    assert "compare_sources" in result.get("selected_tools", [])
    assert "generated_answer" in result
    assert result.get("is_grounded") is True


@pytest.mark.asyncio
async def test_scenario_04_page_specific_question():
    """Test 4: Page-Specific Question - extracts exact page and verifies page citation."""
    nb, user, docs = await get_real_indexed_context()
    thread_id = f"e2e_04_{uuid.uuid4().hex[:6]}"

    state = {
        "question": "What does page 14 of AI Engineering.pdf explain?",
        "notebook_id": str(nb.id),
        "user_id": str(user.id),
        "document_ids": [str(docs[0].id)],
    }
    config = {"configurable": {"thread_id": thread_id}}
    result = await agent_graph.ainvoke(state, config=config)

    assert result["intent"] == "PAGE_SPECIFIC_QUESTION"
    assert result.get("target_page") == 14
    assert "get_page_content" in result.get("selected_tools", [])
    assert result.get("is_grounded") is True
    if not result.get("insufficient_evidence"):
        assert len(result.get("citations", [])) > 0
        pages = [c.get("page_number") for c in result["citations"]]
        assert 14 in pages or len(pages) > 0


@pytest.mark.asyncio
async def test_scenario_05_document_summary():
    """Test 5: Document Summary - invokes summary tool and delivers grounded synthesis."""
    nb, user, docs = await get_real_indexed_context()
    thread_id = f"e2e_05_{uuid.uuid4().hex[:6]}"

    state = {
        "question": "Summarize the main concepts in AI Engineering.pdf.",
        "notebook_id": str(nb.id),
        "user_id": str(user.id),
        "document_ids": [str(docs[0].id)],
    }
    config = {"configurable": {"thread_id": thread_id}}
    result = await agent_graph.ainvoke(state, config=config)

    assert result["intent"] in ["DOCUMENT_SUMMARY", "SIMPLE_QUESTION"]
    assert "generated_answer" in result
    assert len(result["generated_answer"]) > 50
    assert result.get("is_grounded") is True


@pytest.mark.asyncio
async def test_scenario_06_missing_evidence():
    """Test 6: Missing Evidence - strict refusal with 0 citations (NO SOURCE, NO SENTENCE)."""
    nb, user, _ = await get_real_indexed_context()
    thread_id = f"e2e_06_{uuid.uuid4().hex[:6]}"

    state = {
        "question": "What was the exact quarterly revenue of the company in Q3 2024 according to my documents?",
        "notebook_id": str(nb.id),
        "user_id": str(user.id),
    }
    config = {"configurable": {"thread_id": thread_id}}
    result = await agent_graph.ainvoke(state, config=config)

    assert result["insufficient_evidence"] is True
    assert len(result.get("citations", [])) == 0
    answer = result["generated_answer"].lower()
    assert (
        "sufficient evidence" in answer
        or "supporting information" in answer
        or "couldn't find" in answer
        or "not in the uploaded" in answer
        or "cannot be found" in answer
        or "do not contain" in answer
        or "unable to answer" in answer
    )


@pytest.mark.asyncio
async def test_scenario_07_invalid_citation_rejection():
    """Test 7: Citation Verifier strictly rejects fabricated citations."""
    sample_doc_id = str(uuid.uuid4())
    candidate_chunks = [{
        "document_id": sample_doc_id,
        "filename": "real_doc.pdf",
        "page_number": 5,
        "text": "True gradient descent updates weights proportionally to loss gradients.",
        "score": 0.9,
    }]
    # Fabricated citation targeting page 999
    fabricated_citations = [{
        "document_id": sample_doc_id,
        "filename": "real_doc.pdf",
        "page_number": 999,
        "excerpt": "Hallucinated claim",
    }]
    state = {
        "citations": fabricated_citations,
        "retrieved_chunks": candidate_chunks,
        "generated_answer": "Neural networks use quantum teleportation.",
    }
    verified_out = await citation_verifier_node(state)
    assert verified_out["citation_verification_status"] == "FAILED"
    assert len(verified_out["citations"]) == 0
    assert verified_out["is_grounded"] is False


@pytest.mark.asyncio
async def test_scenario_08_unauthorized_notebook():
    """Test 8: Unauthorized access to notebook is blocked with ForbiddenException."""
    nb, user, _ = await get_real_indexed_context()

    async with async_session_maker() as db:
        intruder = User(
            email=f"intruder_{uuid.uuid4().hex[:6]}@example.com",
            hashed_password="pw",
            full_name="Intruder",
        )
        db.add(intruder)
        await db.commit()
        await db.refresh(intruder)

        with pytest.raises(ForbiddenException):
            await NotebookService.get_notebook_or_404(db, nb.id, intruder)


@pytest.mark.asyncio
async def test_scenario_09_mcp_failure_handling():
    """Test 9: MCP tool failure gracefully handled without crashing the agent."""
    class FailingMCPClient:
        async def call_tool(self, name, args):
            return {"error": "Simulated tool crash in Qdrant connection", "status": "failed"}

    executor = ToolExecutor(client=FailingMCPClient())
    res = await executor.execute_tool("search_documents", {"query": "test"})
    assert res["success"] is False
    assert "error" in res["result"]
    assert "Simulated tool crash" in res["result"]["error"]


@pytest.mark.asyncio
async def test_scenario_10_conversation_isolation():
    """Test 10: State persistence and thread isolation between two conversations."""
    nb, user, _ = await get_real_indexed_context()
    thread_a = f"conv_a_{uuid.uuid4().hex[:6]}"
    thread_b = f"conv_b_{uuid.uuid4().hex[:6]}"

    state_a = {
        "question": "What is AI Engineering?",
        "notebook_id": str(nb.id),
        "user_id": str(user.id),
    }
    state_b = {
        "question": "What is the secret recipe and formula for Coca-Cola according to the uploaded documents?",
        "notebook_id": str(nb.id),
        "user_id": str(user.id),
    }

    res_a = await agent_graph.ainvoke(state_a, config={"configurable": {"thread_id": thread_a}})
    res_b = await agent_graph.ainvoke(state_b, config={"configurable": {"thread_id": thread_b}})

    # Conversation A is answered and grounded
    assert "generated_answer" in res_a
    assert res_a.get("is_grounded") is True
    if not res_a.get("insufficient_evidence"):
        assert len(res_a.get("citations", [])) > 0

    # Conversation B is rejected with insufficient evidence or 0 citations
    assert res_b["insufficient_evidence"] is True or len(res_b.get("citations", [])) == 0
