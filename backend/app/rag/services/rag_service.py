import logging
import time
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.agents.graph import agent_graph
from app.agents.prompts import REFUSAL_MESSAGE
from app.rag.citations.citation_validator import CitationValidator
from app.rag.generation.gemini_generator import gemini_generator
from app.rag.retrieval.retriever import modular_retriever
from app.rag.schemas.rag import (
    PerformanceMetrics,
    RAGChatRequest,
    RAGChatResponse,
    RAGCitation,
    RetrievalMetadata,
    UsageMetrics,
)
from app.services.notebook_service import NotebookService

logger = logging.getLogger("app.rag.service")


class RAGService:
    @staticmethod
    async def get_or_create_conversation(
        db: AsyncSession,
        notebook_id: uuid.UUID,
        user: User,
        conversation_id: Optional[uuid.UUID] = None,
    ) -> Conversation:
        if conversation_id:
            stmt = select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user.id,
                Conversation.notebook_id == notebook_id,
            )
            res = await db.execute(stmt)
            conv = res.scalar_one_or_none()
            if conv:
                return conv

        # Find most recent conversation
        stmt = (
            select(Conversation)
            .where(Conversation.notebook_id == notebook_id, Conversation.user_id == user.id)
            .order_by(Conversation.created_at.desc())
        )
        res = await db.execute(stmt)
        conv = res.scalar_one_or_none()
        if conv:
            return conv

        new_conv = Conversation(
            notebook_id=notebook_id,
            user_id=user.id,
            title="Research Chat",
        )
        db.add(new_conv)
        await db.commit()
        await db.refresh(new_conv)
        return new_conv

    @staticmethod
    async def process_chat(
        db: AsyncSession,
        notebook_id: uuid.UUID,
        chat_req: RAGChatRequest,
        user: User,
    ) -> RAGChatResponse:
        t_start = time.perf_counter()
        request_id = str(uuid.uuid4())

        # 1. Verify notebook ownership
        await NotebookService.get_notebook_or_404(db, notebook_id, user)

        # 2. Get/create conversation
        conv = await RAGService.get_or_create_conversation(
            db, notebook_id, user, chat_req.get_conversation_id()
        )

        question = chat_req.get_question()

        # 3. Save user message
        user_msg = Message(
            conversation_id=conv.id,
            role="user",
            content=question,
        )
        db.add(user_msg)
        await db.commit()

        # 4. Invoke LangGraph Agent Workflow with MCP Tool Integration
        t_agent_0 = time.perf_counter()
        source_ids = chat_req.get_source_ids()
        str_source_ids = [str(s) for s in source_ids] if source_ids else None

        initial_state = {
            "question": question,
            "original_query": question,
            "notebook_id": str(notebook_id),
            "user_id": str(user.id),
            "document_ids": str_source_ids,
            "conversation_id": str(conv.id),
        }
        config = {"configurable": {"thread_id": str(conv.id)}}
        agent_result = await agent_graph.ainvoke(initial_state, config=config)
        agent_latency_ms = int((time.perf_counter() - t_agent_0) * 1000)

        answer_text = agent_result.get("generated_answer") or REFUSAL_MESSAGE
        insufficient = agent_result.get("insufficient_evidence", False)
        is_grounded = agent_result.get("is_grounded", True)
        intent = agent_result.get("intent", "SIMPLE_QUESTION")
        selected_tools = agent_result.get("selected_tools", [])
        verified_citation_dicts = agent_result.get("citations", [])
        selected_chunks = agent_result.get("retrieved_chunks", [])

        rag_citations: List[RAGCitation] = []
        for c in verified_citation_dicts:
            rag_citations.append(
                RAGCitation(
                    document_id=str(c.get("document_id", "")),
                    filename=c.get("filename") or c.get("document_name") or "Document",
                    page_number=int(c.get("page_number", 1)),
                    chunk_id=str(c.get("chunk_id", uuid.uuid4())),
                    excerpt=c.get("excerpt", ""),
                    claim=c.get("claim", ""),
                    relevanceScore=float(c.get("relevance_score", 1.0)),
                )
            )

        total_latency_ms = int((time.perf_counter() - t_start) * 1000)

        # 5. Persist assistant response in DB
        assistant_msg = Message(
            conversation_id=conv.id,
            role="assistant",
            content=answer_text,
            token_usage=len(answer_text.split()),
            latency_ms=total_latency_ms,
            citations=verified_citation_dicts,
        )
        db.add(assistant_msg)
        await db.commit()
        await db.refresh(assistant_msg)

        # 6. Observability Structured Log
        selected_pages = [c.get("page_number") for c in selected_chunks]
        logger.info(
            f"[AGENT RAG OBSERVABILITY] req_id={request_id} | user_id={user.id} | nb_id={notebook_id} | "
            f"query='{question[:40]}' | intent={intent} | tools={selected_tools} | total_ms={total_latency_ms} | "
            f"pages={selected_pages} | grounded={is_grounded} | insufficient={insufficient}"
        )

        return RAGChatResponse(
            id=assistant_msg.id,
            answer=answer_text,
            content=answer_text,
            conversation_id=conv.id,
            citations=rag_citations,
            grounded=is_grounded,
            insufficient_evidence=insufficient,
            intent=intent,
            tools_used=selected_tools,
            retrieval_metadata=RetrievalMetadata(
                retrieved_chunks=len(selected_chunks),
                selected_chunks=len(selected_chunks),
            ),
            performance=PerformanceMetrics(
                retrieval_latency_ms=agent_latency_ms,
                generation_latency_ms=agent_latency_ms,
                total_latency_ms=total_latency_ms,
            ),
            usage=UsageMetrics(
                input_tokens=len(question.split()),
                output_tokens=len(answer_text.split()),
            ),
            role="assistant",
            created_at=assistant_msg.created_at,
            token_usage=len(answer_text.split()),
            latency_ms=total_latency_ms,
        )

    @staticmethod
    async def get_history(
        db: AsyncSession,
        notebook_id: uuid.UUID,
        user: User,
    ) -> List[RAGChatResponse]:
        await NotebookService.get_notebook_or_404(db, notebook_id, user)

        stmt = (
            select(Conversation)
            .where(Conversation.notebook_id == notebook_id, Conversation.user_id == user.id)
            .order_by(Conversation.created_at.desc())
            .options(selectinload(Conversation.messages))
        )
        res = await db.execute(stmt)
        conv = res.scalar_one_or_none()
        if not conv or not conv.messages:
            return []

        history: List[RAGChatResponse] = []
        for msg in conv.messages:
            cits = []
            if msg.citations:
                for c in msg.citations:
                    if isinstance(c, dict):
                        doc_id = str(c.get("document_id") or c.get("documentId") or "")
                        fname = c.get("filename") or c.get("document_name") or c.get("documentName") or "Document"
                        p_num = int(c.get("page_number") or c.get("pageNumber") or 1)
                        ch_id = str(c.get("chunk_id") or c.get("id") or uuid.uuid4())
                        exc = c.get("excerpt") or ""
                        clm = c.get("claim") or ""
                        rel = float(c.get("relevance_score") or c.get("relevanceScore") or 1.0)
                        cits.append(
                            RAGCitation(
                                document_id=doc_id,
                                filename=fname,
                                page_number=p_num,
                                chunk_id=ch_id,
                                excerpt=exc,
                                claim=clm,
                                relevanceScore=rel,
                            )
                        )

            history.append(
                RAGChatResponse(
                    id=msg.id,
                    answer=msg.content,
                    content=msg.content,
                    conversation_id=conv.id,
                    citations=cits,
                    grounded=len(cits) > 0,
                    insufficient_evidence=REFUSAL_MESSAGE in msg.content,
                    role=msg.role,
                    created_at=msg.created_at,
                    token_usage=msg.token_usage or 0,
                )
            )

        return history


rag_service = RAGService()
