"""
End-to-End Test Suite for LangGraph + MCP Agent Workflows in NotebookLM Lite.
Tests all 12 key scenarios:
1. Simple Question
2. Multi-Document Question
3. Comparison Question
4. Document Summary
5. Page-Specific Question
6. Insufficient Evidence (Off-topic refusal)
7. Multi-Tenant Isolation
8. Citation Verification Enforcement
9. State Persistence & Checkpointing
10. Strict Grounding Refusal ("NO SOURCE, NO SENTENCE")
11. Tool Execution Telemetry
12. FastAPI RAG Service Integration
"""

import uuid
import pytest
from sqlalchemy import select

from app.agents.graph import agent_graph
from app.agents.prompts import REFUSAL_MESSAGE
from app.db.session import async_session_maker
from app.models.conversation import Conversation
from app.models.document import Document
from app.models.notebook import Notebook
from app.models.user import User
from app.rag.schemas.rag import RAGChatRequest
from app.rag.services.rag_service import rag_service


async def get_test_context():
    """Retrieve existing user and notebook with documents."""
    async with async_session_maker() as db:
        res = await db.execute(select(Notebook).where(Notebook.documents.any()))
        nb = res.scalars().first()
        if nb:
            user_res = await db.execute(select(User).where(User.id == nb.owner_id))
            user = user_res.scalar_one_or_none()
            doc_res = await db.execute(select(Document).where(Document.notebook_id == nb.id))
            docs = doc_res.scalars().all()
            return nb, user, docs

        # Fallback create
        user = User(email=f"workflow_{uuid.uuid4().hex[:6]}@example.com", hashed_password="pw")
        db.add(user)
        await db.commit()
        await db.refresh(user)

        nb = Notebook(title="Workflow Notebook", owner_id=user.id)
        db.add(nb)
        await db.commit()
        await db.refresh(nb)

        doc = Document(
            notebook_id=nb.id,
            owner_id=user.id,
            filename="sample_paper.pdf",
            storage_path="sample.pdf",
            page_count=5,
            total_chunks=10,
            processing_status="INDEXED",
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)

        return nb, user, [doc]


@pytest.mark.asyncio
async def test_scenario_1_simple_question():
    nb, user, _ = await get_test_context()
    state = {
        "question": "What is the key architecture discussed?",
        "notebook_id": str(nb.id),
        "user_id": str(user.id),
    }
    config = {"configurable": {"thread_id": f"s1_{uuid.uuid4().hex[:6]}"}}
    res = await agent_graph.ainvoke(state, config=config)

    assert res["intent"] in ["SIMPLE_QUESTION", "DOCUMENT_SUMMARY"]
    assert "generated_answer" in res
    assert len(res["generated_answer"]) > 10
    assert res.get("is_grounded") is True


@pytest.mark.asyncio
async def test_scenario_2_multi_document_question():
    nb, user, _ = await get_test_context()
    state = {
        "question": "What are the common findings across all documents in this notebook?",
        "notebook_id": str(nb.id),
        "user_id": str(user.id),
    }
    config = {"configurable": {"thread_id": f"s2_{uuid.uuid4().hex[:6]}"}}
    res = await agent_graph.ainvoke(state, config=config)

    assert res["intent"] in ["MULTI_DOCUMENT_QUESTION", "COMPARISON_QUESTION"]
    assert "selected_tools" in res


@pytest.mark.asyncio
async def test_scenario_3_comparison_question():
    nb, user, _ = await get_test_context()
    state = {
        "question": "Compare the performance versus earlier architectures",
        "notebook_id": str(nb.id),
        "user_id": str(user.id),
    }
    config = {"configurable": {"thread_id": f"s3_{uuid.uuid4().hex[:6]}"}}
    res = await agent_graph.ainvoke(state, config=config)

    assert res["intent"] == "COMPARISON_QUESTION"
    assert "compare_sources" in res.get("selected_tools", [])


@pytest.mark.asyncio
async def test_scenario_4_document_summary():
    nb, user, _ = await get_test_context()
    state = {
        "question": "Summarize the key findings in this document",
        "notebook_id": str(nb.id),
        "user_id": str(user.id),
    }
    config = {"configurable": {"thread_id": f"s4_{uuid.uuid4().hex[:6]}"}}
    res = await agent_graph.ainvoke(state, config=config)

    assert res["intent"] == "DOCUMENT_SUMMARY"
    assert len(res.get("generated_answer", "")) > 15


@pytest.mark.asyncio
async def test_scenario_5_page_specific_question():
    nb, user, _ = await get_test_context()
    state = {
        "question": "What is discussed on page 4 of the document?",
        "notebook_id": str(nb.id),
        "user_id": str(user.id),
    }
    config = {"configurable": {"thread_id": f"s5_{uuid.uuid4().hex[:6]}"}}
    res = await agent_graph.ainvoke(state, config=config)

    assert res["intent"] == "PAGE_SPECIFIC_QUESTION"
    assert res["target_page"] == 4
    assert "get_page_content" in res.get("selected_tools", [])


@pytest.mark.asyncio
async def test_scenario_6_insufficient_evidence_off_topic():
    nb, user, _ = await get_test_context()
    state = {
        "question": "What is the weather in Tokyo tomorrow?",
        "notebook_id": str(nb.id),
        "user_id": str(user.id),
    }
    config = {"configurable": {"thread_id": f"s6_{uuid.uuid4().hex[:6]}"}}
    res = await agent_graph.ainvoke(state, config=config)

    assert res["intent"] == "INSUFFICIENT_EVIDENCE"
    assert res["insufficient_evidence"] is True
    assert REFUSAL_MESSAGE in res["generated_answer"]
    assert len(res.get("citations", [])) == 0


@pytest.mark.asyncio
async def test_scenario_7_multitenant_isolation():
    nb, _, _ = await get_test_context()
    fake_user_id = str(uuid.uuid4())
    state = {
        "question": "What are the core findings?",
        "notebook_id": str(nb.id),
        "user_id": fake_user_id,
    }
    config = {"configurable": {"thread_id": f"s7_{uuid.uuid4().hex[:6]}"}}
    res = await agent_graph.ainvoke(state, config=config)

    # Unauthorized access must result in refusal without data leakage
    assert res["insufficient_evidence"] is True
    assert len(res.get("citations", [])) == 0


@pytest.mark.asyncio
async def test_scenario_8_citation_verification_enforcement():
    nb, user, _ = await get_test_context()
    state = {
        "question": "Explain attention mechanism speedup",
        "notebook_id": str(nb.id),
        "user_id": str(user.id),
    }
    config = {"configurable": {"thread_id": f"s8_{uuid.uuid4().hex[:6]}"}}
    res = await agent_graph.ainvoke(state, config=config)

    assert res.get("citation_verification_status") in ["VERIFIED", "PARTIAL"]
    for cit in res.get("citations", []):
        assert "document_id" in cit
        assert "page_number" in cit
        assert int(cit["page_number"]) >= 1


@pytest.mark.asyncio
async def test_scenario_9_state_persistence_checkpointer():
    nb, user, _ = await get_test_context()
    thread_id = f"checkpointer_test_{uuid.uuid4().hex[:6]}"
    config = {"configurable": {"thread_id": thread_id}}

    state1 = {
        "question": "What is the FLOPS formula?",
        "notebook_id": str(nb.id),
        "user_id": str(user.id),
    }
    res1 = await agent_graph.ainvoke(state1, config=config)
    assert res1 is not None

    # Retrieve state from checkpointer
    saved_state = await agent_graph.aget_state(config)
    assert saved_state is not None
    assert saved_state.values.get("question") == "What is the FLOPS formula?"


@pytest.mark.asyncio
async def test_scenario_10_strict_refusal_when_no_evidence():
    """Verify core principle: NO SOURCE, NO SENTENCE."""
    state = {
        "question": "Recipe for chocolate chip cookies",
        "notebook_id": str(uuid.uuid4()),
        "user_id": str(uuid.uuid4()),
    }
    config = {"configurable": {"thread_id": f"s10_{uuid.uuid4().hex[:6]}"}}
    res = await agent_graph.ainvoke(state, config=config)

    assert res["insufficient_evidence"] is True
    assert res["citations"] == []
    assert REFUSAL_MESSAGE in res["generated_answer"]


@pytest.mark.asyncio
async def test_scenario_11_mcp_tool_execution_telemetry():
    nb, user, _ = await get_test_context()
    state = {
        "question": "What is discussed on page 1?",
        "notebook_id": str(nb.id),
        "user_id": str(user.id),
    }
    config = {"configurable": {"thread_id": f"s11_{uuid.uuid4().hex[:6]}"}}
    res = await agent_graph.ainvoke(state, config=config)

    assert "selected_tools" in res
    assert len(res["selected_tools"]) > 0


@pytest.mark.asyncio
async def test_scenario_12_fastapi_rag_service_e2e_integration():
    nb, user, _ = await get_test_context()
    chat_req = RAGChatRequest(question="What are the key findings in this document?")

    async with async_session_maker() as db:
        res = await rag_service.process_chat(
            db=db,
            notebook_id=nb.id,
            chat_req=chat_req,
            user=user,
        )

        assert res.id is not None
        assert res.answer is not None
        assert res.grounded is True
        assert res.role == "assistant"
        assert res.intent is not None

        # Verify conversation and message saved in database
        conv_res = await db.execute(
            select(Conversation).where(Conversation.id == res.conversation_id)
        )
        conv = conv_res.scalar_one_or_none()
        assert conv is not None

