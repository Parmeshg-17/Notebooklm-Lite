"""
LangGraph StateGraph assembly for NotebookLM Lite Agent Workflow.
Orchestrates:
- Question Analysis & Intent Routing
- MCP Tool Planning & Execution
- Evidence Collection & Grounding
- Answer Generation with Strict Citations
- Citation Verification with Recovery Loops
- Memory Checkpointing
"""

import logging
from typing import Any, Dict, Optional
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.agents.nodes import (
    analyze_question_node,
    answer_generator_node,
    citation_verifier_node,
    collect_evidence_node,
    comparison_retriever_node,
    document_retriever_node,
    evidence_collector_node,
    execute_tools_node,
    generate_answer_node,
    insufficient_evidence_handler_node,
    insufficient_evidence_node,
    intent_router_node,
    multi_document_retriever_node,
    query_planner_node,
    question_analyzer_node,
    verify_citations_node,
)
from app.agents.state import AgentState

logger = logging.getLogger("app.agents.graph")


def route_after_intent(state: AgentState) -> str:
    """Route to insufficient evidence handler or query planner based on detected intent."""
    if state.get("intent") == "INSUFFICIENT_EVIDENCE":
        return "insufficient_evidence_handler"
    return "query_planner"


def route_after_planner(state: AgentState) -> str:
    """Route to specialized retriever node based on intent."""
    intent = state.get("intent", "SIMPLE_QUESTION")
    if intent == "COMPARISON_QUESTION":
        return "comparison_retriever"
    elif intent == "MULTI_DOCUMENT_QUESTION":
        return "multi_document_retriever"
    return "document_retriever"


def route_after_evidence(state: AgentState) -> str:
    """Route to insufficient evidence if evidence is empty or below threshold."""
    if state.get("insufficient_evidence", False):
        return "insufficient_evidence_handler"
    return "answer_generator"


def route_after_verification(state: AgentState) -> str:
    """Route to retry or end based on citation verification status."""
    status = state.get("citation_verification_status")
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 1)

    if status == "FAILED":
        if retry_count < max_retries:
            logger.info(f"[GRAPH RECOVERY] Verification failed. Retrying (attempt {retry_count + 1}/{max_retries})")
            return "query_planner"
        logger.warning("[GRAPH RECOVERY] Max retries exhausted. Routing to insufficient evidence.")
        return "insufficient_evidence_handler"
    return END


# Backwards compatibility alias
route_after_analysis = route_after_intent


def build_agent_graph():
    """Assemble and compile the stateful LangGraph agent workflow with all 10 core nodes."""
    builder = StateGraph(AgentState)

    # 1. Add all 10 core nodes
    builder.add_node("question_analyzer", question_analyzer_node)
    builder.add_node("intent_router", intent_router_node)
    builder.add_node("query_planner", query_planner_node)
    builder.add_node("document_retriever", document_retriever_node)
    builder.add_node("multi_document_retriever", multi_document_retriever_node)
    builder.add_node("comparison_retriever", comparison_retriever_node)
    builder.add_node("evidence_collector", evidence_collector_node)
    builder.add_node("answer_generator", answer_generator_node)
    builder.add_node("citation_verifier", citation_verifier_node)
    builder.add_node("insufficient_evidence_handler", insufficient_evidence_handler_node)

    # 2. Add edges & conditional transitions
    builder.add_edge(START, "question_analyzer")
    builder.add_edge("question_analyzer", "intent_router")

    builder.add_conditional_edges(
        "intent_router",
        route_after_intent,
        {
            "query_planner": "query_planner",
            "insufficient_evidence_handler": "insufficient_evidence_handler",
        },
    )

    builder.add_conditional_edges(
        "query_planner",
        route_after_planner,
        {
            "document_retriever": "document_retriever",
            "multi_document_retriever": "multi_document_retriever",
            "comparison_retriever": "comparison_retriever",
        },
    )

    builder.add_edge("document_retriever", "evidence_collector")
    builder.add_edge("multi_document_retriever", "evidence_collector")
    builder.add_edge("comparison_retriever", "evidence_collector")

    builder.add_conditional_edges(
        "evidence_collector",
        route_after_evidence,
        {
            "answer_generator": "answer_generator",
            "insufficient_evidence_handler": "insufficient_evidence_handler",
        },
    )

    builder.add_edge("answer_generator", "citation_verifier")

    builder.add_conditional_edges(
        "citation_verifier",
        route_after_verification,
        {
            "query_planner": "query_planner",
            "insufficient_evidence_handler": "insufficient_evidence_handler",
            END: END,
        },
    )

    builder.add_edge("insufficient_evidence_handler", END)

    # 3. Add durable checkpointer preserving conversation state across restarts
    # In production (ECS Fargate with RDS PostgreSQL), use shared Postgres checkpointer.
    # In local development and testing, fall back to SQLite or MemorySaver.
    checkpointer = None
    from app.core.config import settings

    if settings.DATABASE_URL and ("postgres" in settings.DATABASE_URL.lower()):
        try:
            from psycopg_pool import ConnectionPool
            from langgraph.checkpoint.postgres import PostgresSaver

            pg_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
            pg_pool = ConnectionPool(
                conninfo=pg_url,
                max_size=settings.DB_POOL_SIZE or 10,
                kwargs={"autocommit": True},
            )
            checkpointer = PostgresSaver(conn=pg_pool)
            checkpointer.setup()
            logger.info("[GRAPH] Initialized durable PostgreSQL checkpointer for distributed multi-task ECS execution")
        except Exception as e:
            logger.warning(f"[GRAPH] PostgreSQL checkpointer init failed ({e}), falling back to SQLite")

    if checkpointer is None:
        try:
            from pathlib import Path
            import sqlite3
            from langgraph.checkpoint.sqlite import SqliteSaver

            class AsyncCompatibleSqliteSaver(SqliteSaver):
                """SqliteSaver compatible with both sync (invoke) and async (ainvoke) execution."""

                async def aget_tuple(self, config: Any) -> Any:
                    return self.get_tuple(config)

                async def alist(
                    self,
                    config: Any = None,
                    *,
                    filter: Any = None,
                    before: Any = None,
                    limit: Any = None,
                ) -> Any:
                    for item in self.list(config, filter=filter, before=before, limit=limit):
                        yield item

                async def aput(
                    self,
                    config: Any,
                    checkpoint: Any,
                    metadata: Any,
                    new_versions: Any,
                ) -> Any:
                    return self.put(config, checkpoint, metadata, new_versions)

                async def aput_writes(
                    self,
                    config: Any,
                    writes: Any,
                    task_id: str,
                    task_path: str = "",
                ) -> Any:
                    return self.put_writes(config, writes, task_id, task_path)

            backend_dir = Path(__file__).resolve().parent.parent.parent
            db_path = backend_dir / "checkpoints.db"
            conn = sqlite3.connect(str(db_path), check_same_thread=False)
            checkpointer = AsyncCompatibleSqliteSaver(conn)
            checkpointer.setup()
            logger.info(f"[GRAPH] Initialized durable AsyncCompatibleSqliteSaver at {db_path}")
        except Exception as e:
            logger.warning(f"[GRAPH] SqliteSaver init failed ({e}), falling back to MemorySaver")
            checkpointer = MemorySaver()

    return builder.compile(checkpointer=checkpointer)


# Singleton compiled agent graph
agent_graph = build_agent_graph()

