"""
LangGraph Nodes for NotebookLM Lite Agent Workflow.
Executes question analysis, MCP tool planning, execution, evidence collection,
answer generation, and citation verification.
"""

import logging
import time
from typing import Any, Dict, List, Optional
import uuid

from app.agents.prompts import (
    COMPARISON_PROMPT,
    REFUSAL_MESSAGE,
    SUMMARY_PROMPT,
    SYSTEM_AGENT_PROMPT,
)
from app.agents.router import IntentRouter
from app.agents.state import AgentState
from app.mcp_client.tool_executor import tool_executor
from app.rag.generation.gemini_generator import gemini_generator
from app.services.citation_verifier import citation_verifier
from app.services.evidence_service import evidence_service

logger = logging.getLogger("app.agents.nodes")


async def question_analyzer_node(state: AgentState) -> Dict[str, Any]:
    """Analyze the user query, determine sub-questions and target pages."""
    question = state.get("question", "")
    route_res = await IntentRouter.route_question(
        question=question,
        has_documents=True,
    )
    return {
        "target_page": route_res.get("target_page"),
        "sub_questions": route_res.get("sub_questions", [question]),
        "retry_count": state.get("retry_count", 0),
        "max_retries": state.get("max_retries", 1),
    }


async def intent_router_node(state: AgentState) -> Dict[str, Any]:
    """Classify the user query intent and record reasoning."""
    question = state.get("question", "")
    route_res = await IntentRouter.route_question(
        question=question,
        has_documents=True,
    )
    return {
        "intent": route_res.get("intent", "SIMPLE_QUESTION"),
        "intent_reasoning": route_res.get("reasoning", ""),
        "target_page": route_res.get("target_page") or state.get("target_page"),
    }


async def analyze_question_node(state: AgentState) -> Dict[str, Any]:
    """Composite question analyzer & intent router node for unified execution."""
    qa = await question_analyzer_node(state)
    ir = await intent_router_node(state)
    return {**qa, **ir}


async def query_planner_node(state: AgentState) -> Dict[str, Any]:
    """Select appropriate MCP tools and construct their argument payloads based on intent."""
    intent = state.get("intent", "SIMPLE_QUESTION")
    question = state.get("question", "")
    notebook_id = state.get("notebook_id", "")
    user_id = state.get("user_id", "")
    document_ids = state.get("document_ids")
    target_page = state.get("target_page")

    tool_calls: List[Dict[str, Any]] = []

    if intent == "PAGE_SPECIFIC_QUESTION" and target_page:
        # Request exact page content
        target_doc = document_ids[0] if document_ids else None
        tool_calls.append({
            "name": "get_page_content",
            "args": {
                "document_id": str(target_doc) if target_doc else None,
                "page_number": target_page,
                "notebook_id": str(notebook_id),
                "user_id": str(user_id) if user_id else None,
            },
        })
        # Also run targeted hybrid search
        tool_calls.append({
            "name": "search_documents",
            "args": {
                "notebook_id": str(notebook_id),
                "query": question,
                "document_ids": [str(d) for d in document_ids] if document_ids else None,
                "user_id": str(user_id) if user_id else None,
                "top_k": 5,
            },
        })

    elif intent == "COMPARISON_QUESTION":
        tool_calls.append({
            "name": "compare_sources",
            "args": {
                "notebook_id": str(notebook_id),
                "question": question,
                "document_ids": [str(d) for d in document_ids] if document_ids else None,
                "user_id": str(user_id) if user_id else None,
            },
        })

    elif intent == "DOCUMENT_SUMMARY":
        target_doc = document_ids[0] if document_ids else None
        tool_calls.append({
            "name": "summarize_document",
            "args": {
                "document_id": str(target_doc) if target_doc else None,
                "notebook_id": str(notebook_id),
                "user_id": str(user_id) if user_id else None,
            },
        })
        tool_calls.append({
            "name": "search_documents",
            "args": {
                "notebook_id": str(notebook_id),
                "query": question,
                "document_ids": [str(target_doc)] if target_doc else None,
                "user_id": str(user_id) if user_id else None,
                "top_k": 5,
            },
        })

    elif intent == "MULTI_DOCUMENT_QUESTION":
        sub_questions = state.get("sub_questions", [question])
        for sq in sub_questions[:2]:
            tool_calls.append({
                "name": "search_documents",
                "args": {
                    "notebook_id": str(notebook_id),
                    "query": sq,
                    "document_ids": [str(d) for d in document_ids] if document_ids else None,
                    "user_id": str(user_id) if user_id else None,
                    "top_k": 5,
                },
            })

    elif intent == "INSUFFICIENT_EVIDENCE":
        # No tools needed
        pass

    else:  # SIMPLE_QUESTION
        tool_calls.append({
            "name": "search_documents",
            "args": {
                "notebook_id": str(notebook_id),
                "query": question,
                "document_ids": [str(d) for d in document_ids] if document_ids else None,
                "user_id": str(user_id) if user_id else None,
                "top_k": 5,
            },
        })

    selected_tools = [c["name"] for c in tool_calls]
    return {
        "tool_calls": tool_calls,
        "selected_tools": selected_tools,
    }


async def execute_tools_node(state: AgentState) -> Dict[str, Any]:
    """Execute the planned MCP tools via tool_executor."""
    tool_calls = state.get("tool_calls", [])
    if not tool_calls:
        return {"tool_results": []}

    results = await tool_executor.execute_batch(tool_calls)
    return {"tool_results": results}


async def document_retriever_node(state: AgentState) -> Dict[str, Any]:
    """Execute document retrieval tools planned for single-document or page-specific queries."""
    tool_calls = state.get("tool_calls")
    if not tool_calls:
        tool_calls = [{
            "name": "search_documents",
            "args": {
                "notebook_id": str(state.get("notebook_id", "")),
                "query": state.get("question", ""),
                "document_ids": [str(d) for d in state.get("document_ids", [])] if state.get("document_ids") else None,
                "user_id": str(state.get("user_id", "")) if state.get("user_id") else None,
                "top_k": 5,
            },
        }]
    results = await tool_executor.execute_batch(tool_calls)
    return {
        "tool_results": results,
        "selected_tools": [c["name"] for c in tool_calls],
    }


async def multi_document_retriever_node(state: AgentState) -> Dict[str, Any]:
    """Execute multi-document retrieval tools across planned sub-questions."""
    tool_calls = state.get("tool_calls")
    if not tool_calls:
        sub_questions = state.get("sub_questions", [state.get("question", "")])
        tool_calls = [
            {
                "name": "search_documents",
                "args": {
                    "notebook_id": str(state.get("notebook_id", "")),
                    "query": sq,
                    "document_ids": [str(d) for d in state.get("document_ids", [])] if state.get("document_ids") else None,
                    "user_id": str(state.get("user_id", "")) if state.get("user_id") else None,
                    "top_k": 5,
                },
            }
            for sq in sub_questions[:2]
        ]
    results = await tool_executor.execute_batch(tool_calls)
    return {
        "tool_results": results,
        "selected_tools": [c["name"] for c in tool_calls],
    }


async def comparison_retriever_node(state: AgentState) -> Dict[str, Any]:
    """Execute cross-source comparison tools."""
    tool_calls = state.get("tool_calls")
    if not tool_calls:
        tool_calls = [{
            "name": "compare_sources",
            "args": {
                "notebook_id": str(state.get("notebook_id", "")),
                "question": state.get("question", ""),
                "document_ids": [str(d) for d in state.get("document_ids", [])] if state.get("document_ids") else None,
                "user_id": str(state.get("user_id", "")) if state.get("user_id") else None,
            },
        }]
    results = await tool_executor.execute_batch(tool_calls)
    return {
        "tool_results": results,
        "selected_tools": [c["name"] for c in tool_calls],
    }


async def collect_evidence_node(state: AgentState) -> Dict[str, Any]:
    """Aggregate, deduplicate, and structure evidence retrieved by tools."""
    tool_results = state.get("tool_results", [])
    unique_chunks, evidence_matrix, context_text, has_sufficient = evidence_service.aggregate_evidence(tool_results)

    return {
        "retrieved_chunks": unique_chunks,
        "evidence": evidence_matrix,
        "context_text": context_text,
        "insufficient_evidence": not has_sufficient,
    }


async def generate_answer_node(state: AgentState) -> Dict[str, Any]:
    """Generate answer strictly grounded in retrieved evidence."""
    question = state.get("question", "")
    context_text = state.get("context_text", "")
    candidate_chunks = state.get("retrieved_chunks", [])
    insufficient = state.get("insufficient_evidence", False)

    if insufficient or not candidate_chunks:
        return {
            "generated_answer": REFUSAL_MESSAGE,
            "citations": [],
            "insufficient_evidence": True,
            "is_grounded": True,
        }

    # Generate answer with Gemini generator
    gen_result = await gemini_generator.generate_answer(
        query=question,
        context_text=context_text,
        candidate_chunks=candidate_chunks,
        has_sufficient_evidence=not insufficient,
    )

    if gen_result.insufficient_evidence:
        return {
            "generated_answer": gen_result.answer or REFUSAL_MESSAGE,
            "citations": [],
            "insufficient_evidence": True,
            "is_grounded": True,
        }

    formatted_citations = []
    for c in gen_result.citations:
        doc_id = str(getattr(c, "document_id", getattr(c, "documentId", "")))
        doc_name = getattr(c, "filename", getattr(c, "documentName", "Document"))
        page_num = getattr(c, "page_number", getattr(c, "pageNumber", 1))
        excerpt = getattr(c, "excerpt", "")
        rel_score = getattr(c, "relevanceScore", 1.0)
        formatted_citations.append({
            "document_id": doc_id,
            "document_name": doc_name,
            "filename": doc_name,
            "page_number": page_num,
            "excerpt": excerpt,
            "relevance_score": rel_score,
        })

    return {
        "generated_answer": gen_result.answer,
        "citations": formatted_citations,
        "insufficient_evidence": False,
    }


async def verify_citations_node(state: AgentState) -> Dict[str, Any]:
    """Verify generated citations against real document chunks and check grounding."""
    if state.get("insufficient_evidence", False):
        return {
            "citations": [],
            "is_grounded": True,
            "citation_verification_status": "VERIFIED",
            "retry_count": state.get("retry_count", 0),
        }

    citations = state.get("citations", [])
    chunks = state.get("retrieved_chunks", [])
    answer = state.get("generated_answer", "")

    verified, is_grounded, status = citation_verifier.verify_citations(
        citations=citations,
        retrieved_chunks=chunks,
        answer_text=answer,
    )

    current_retries = state.get("retry_count", 0)
    # If citations failed and we have retries left, increment retry count
    if status == "FAILED" and not state.get("insufficient_evidence", False):
        new_retries = current_retries + 1
    else:
        new_retries = current_retries

    return {
        "citations": verified,
        "is_grounded": is_grounded,
        "citation_verification_status": status,
        "retry_count": new_retries,
    }


async def insufficient_evidence_node(state: AgentState) -> Dict[str, Any]:
    """Direct handler for off-topic queries or insufficient evidence."""
    return {
        "generated_answer": REFUSAL_MESSAGE,
        "citations": [],
        "is_grounded": True,
        "insufficient_evidence": True,
        "citation_verification_status": "VERIFIED",
    }


# Aliases aligning with standard testing taxonomy
evidence_collector_node = collect_evidence_node
citation_verifier_node = verify_citations_node
answer_generator_node = generate_answer_node
insufficient_evidence_handler_node = insufficient_evidence_node

