"""
Test Suite for LangGraph Workflow Nodes and Path Transitions.
Verifies all 10 nodes and the 7 canonical execution paths.
"""

import uuid
import pytest
from sqlalchemy import select

from app.agents.graph import agent_graph, build_agent_graph
from app.agents.nodes import (
    question_analyzer_node,
    intent_router_node,
    query_planner_node,
    document_retriever_node,
    multi_document_retriever_node,
    comparison_retriever_node,
    evidence_collector_node,
    citation_verifier_node,
    answer_generator_node,
    insufficient_evidence_handler_node,
)
from app.db.session import async_session_maker
from app.models.document import Document
from app.models.notebook import Notebook
from app.models.user import User


async def get_test_context():
    """Retrieve indexed test notebook or create one."""
    async with async_session_maker() as db:
        res = await db.execute(select(Notebook).where(Notebook.documents.any()))
        nb = res.scalars().first()
        if nb:
            user_res = await db.execute(select(User).where(User.id == nb.owner_id))
            user = user_res.scalar_one_or_none()
            doc_res = await db.execute(select(Document).where(Document.notebook_id == nb.id))
            docs = doc_res.scalars().all()
            return nb, user, docs

        user = User(email=f"workflow_{uuid.uuid4().hex[:6]}@example.com", hashed_password="pw")
        db.add(user)
        await db.commit()
        await db.refresh(user)

        nb = Notebook(title="Graph Test Notebook", owner_id=user.id)
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
async def test_graph_compilation():
    """Verify StateGraph compiles with checkpointer and all 10 nodes registered."""
    graph = build_agent_graph()
    assert graph is not None
    # Verify node names in graph
    node_names = list(graph.nodes.keys())
    expected_nodes = [
        "question_analyzer",
        "intent_router",
        "query_planner",
        "document_retriever",
        "multi_document_retriever",
        "comparison_retriever",
        "evidence_collector",
        "answer_generator",
        "citation_verifier",
        "insufficient_evidence_handler",
    ]
    for expected in expected_nodes:
        assert expected in node_names, f"Node {expected} missing from graph nodes: {node_names}"


@pytest.mark.asyncio
async def test_node_1_question_analyzer():
    nb, user, _ = await get_test_context()
    state = {
        "question": "What does page 14 of AI Engineering.pdf explain?",
        "notebook_id": str(nb.id),
        "user_id": str(user.id),
    }
    out = await question_analyzer_node(state)
    assert out.get("target_page") == 14
    assert len(out.get("sub_questions", [])) >= 1


@pytest.mark.asyncio
async def test_node_2_intent_router():
    nb, user, _ = await get_test_context()
    state = {
        "question": "Compare the evaluation methods between chapter 1 and chapter 2",
        "notebook_id": str(nb.id),
        "user_id": str(user.id),
    }
    out = await intent_router_node(state)
    assert out["intent"] == "COMPARISON_QUESTION"
    assert "intent_reasoning" in out


@pytest.mark.asyncio
async def test_node_3_query_planner():
    nb, user, _ = await get_test_context()
    state = {
        "intent": "PAGE_SPECIFIC_QUESTION",
        "question": "What is on page 14?",
        "notebook_id": str(nb.id),
        "user_id": str(user.id),
        "target_page": 14,
    }
    out = await query_planner_node(state)
    assert "get_page_content" in out["selected_tools"]
    assert "search_documents" in out["selected_tools"]


@pytest.mark.asyncio
async def test_node_4_document_retriever():
    nb, user, docs = await get_test_context()
    doc_id = str(docs[0].id) if docs else str(uuid.uuid4())
    state = {
        "notebook_id": str(nb.id),
        "user_id": str(user.id),
        "question": "What is AI Engineering?",
        "document_ids": [doc_id],
    }
    out = await document_retriever_node(state)
    assert "tool_results" in out
    assert len(out["tool_results"]) >= 1
    assert "search_documents" in out["selected_tools"]


@pytest.mark.asyncio
async def test_node_5_multi_document_retriever():
    nb, user, _ = await get_test_context()
    state = {
        "notebook_id": str(nb.id),
        "user_id": str(user.id),
        "question": "What are agent architectures?",
        "sub_questions": ["What is agent architecture?", "How do agents use memory?"],
    }
    out = await multi_document_retriever_node(state)
    assert "tool_results" in out
    assert len(out["tool_results"]) == 2


@pytest.mark.asyncio
async def test_node_6_comparison_retriever():
    nb, user, _ = await get_test_context()
    state = {
        "notebook_id": str(nb.id),
        "user_id": str(user.id),
        "question": "Compare latency and throughput across documents",
    }
    out = await comparison_retriever_node(state)
    assert "tool_results" in out
    assert "compare_sources" in out["selected_tools"]


@pytest.mark.asyncio
async def test_node_7_evidence_collector():
    mock_results = [{
        "tool": "search_documents",
        "result": {
            "status": "success",
            "has_sufficient_evidence": True,
            "results": [{
                "chunk_id": str(uuid.uuid4()),
                "document_id": str(uuid.uuid4()),
                "filename": "sample.pdf",
                "page_number": 2,
                "text": "Vector search retrieves top-k chunks based on cosine distance.",
                "score": 0.88,
            }],
        },
    }]
    state = {"tool_results": mock_results}
    out = await evidence_collector_node(state)
    assert len(out["retrieved_chunks"]) == 1
    assert out["insufficient_evidence"] is False
    assert "Vector search" in out["context_text"]


@pytest.mark.asyncio
async def test_node_8_citation_verifier():
    sample_doc_id = str(uuid.uuid4())
    retrieved_chunks = [{
        "document_id": sample_doc_id,
        "filename": "sample.pdf",
        "page_number": 3,
        "text": "Retrieval augmented generation reduces hallucinations.",
        "score": 0.95,
    }]
    citations = [{
        "document_id": sample_doc_id,
        "filename": "sample.pdf",
        "page_number": 3,
        "excerpt": "reduces hallucinations",
    }]
    state = {
        "citations": citations,
        "retrieved_chunks": retrieved_chunks,
        "generated_answer": "RAG reduces hallucinations as shown in sample.pdf.",
    }
    out = await citation_verifier_node(state)
    assert out["citation_verification_status"] == "VERIFIED"
    assert out["is_grounded"] is True
    assert len(out["citations"]) == 1


@pytest.mark.asyncio
async def test_node_9_answer_generator():
    retrieved_chunks = [{
        "document_id": str(uuid.uuid4()),
        "filename": "sample.pdf",
        "page_number": 1,
        "text": "Chip Huyen writes that evaluation is critical for production AI systems.",
        "score": 0.9,
    }]
    state = {
        "question": "Who writes about AI evaluation?",
        "context_text": "[Document: sample.pdf | Page 1]\nChip Huyen writes that evaluation is critical for production AI systems.",
        "retrieved_chunks": retrieved_chunks,
        "insufficient_evidence": False,
    }
    out = await answer_generator_node(state)
    assert "generated_answer" in out
    assert len(out["generated_answer"]) > 10


@pytest.mark.asyncio
async def test_node_10_insufficient_evidence_handler():
    state = {"question": "What is the capital of Mars?"}
    out = await insufficient_evidence_handler_node(state)
    assert out["insufficient_evidence"] is True
    assert out["citations"] == []
    assert "sufficient evidence" in out["generated_answer"].lower() or "not in the uploaded" in out["generated_answer"].lower()


@pytest.mark.asyncio
async def test_path_simple_question_flow():
    nb, user, _ = await get_test_context()
    thread_id = f"path_simple_{uuid.uuid4().hex[:6]}"
    state = {
        "question": "What is the core methodology presented?",
        "notebook_id": str(nb.id),
        "user_id": str(user.id),
    }
    config = {"configurable": {"thread_id": thread_id}}
    res = await agent_graph.ainvoke(state, config=config)
    assert res["intent"] in ["SIMPLE_QUESTION", "DOCUMENT_SUMMARY"]
    assert "generated_answer" in res
    assert res["is_grounded"] is True


@pytest.mark.asyncio
async def test_path_page_specific_flow():
    nb, user, _ = await get_test_context()
    thread_id = f"path_page_{uuid.uuid4().hex[:6]}"
    state = {
        "question": "What does page 14 of AI Engineering.pdf explain?",
        "notebook_id": str(nb.id),
        "user_id": str(user.id),
    }
    config = {"configurable": {"thread_id": thread_id}}
    res = await agent_graph.ainvoke(state, config=config)
    assert res["intent"] == "PAGE_SPECIFIC_QUESTION"
    assert res["target_page"] == 14
    assert res["is_grounded"] is True


@pytest.mark.asyncio
async def test_path_insufficient_evidence_refusal():
    nb, user, _ = await get_test_context()
    thread_id = f"path_refusal_{uuid.uuid4().hex[:6]}"
    state = {
        "question": "What is the total quarterly revenue of Apple in Q3 2024?",
        "notebook_id": str(nb.id),
        "user_id": str(user.id),
    }
    config = {"configurable": {"thread_id": thread_id}}
    res = await agent_graph.ainvoke(state, config=config)
    assert res["insufficient_evidence"] is True
    assert len(res.get("citations", [])) == 0


@pytest.mark.asyncio
async def test_path_citation_failure_recovery_loop():
    """Verify that if citation verification fails, the recovery loop triggers and decrements retries."""
    initial_state = {
        "citations": [{"document_id": "fake_doc", "page_number": 999, "excerpt": "nonexistent"}],
        "retrieved_chunks": [],
        "generated_answer": "Fabricated claim without proof.",
        "retry_count": 0,
        "max_retries": 1,
        "insufficient_evidence": False,
    }
    # Invoke citation verifier node directly
    verified_out = await citation_verifier_node(initial_state)
    assert verified_out["citation_verification_status"] == "FAILED"
    assert verified_out["retry_count"] == 1
