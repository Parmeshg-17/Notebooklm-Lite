"""
Chat and Streaming Question-Answering Endpoints (SSE).
Implements POST /notebooks/{id}/ask and POST /api/v1/notebooks/{id}/ask.
Follows strict citation-first workflow:
Rewrite -> Retrieve (Vector + Keyword RRF) -> Generate -> Validate (NO SOURCE, NO SENTENCE) -> Stream SSE.
"""

import asyncio
import json
from typing import AsyncGenerator, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import get_db
from app.models.models import Citation, Conversation, Message, Notebook
from app.rag.citations import CitationValidator
from app.rag.generator import AnswerGenerator
from app.rag.retrieval import HybridRetriever

logger = get_logger(__name__)
router = APIRouter(tags=["Chat"])


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000, description="The user's question about the notebook")
    conversation_id: Optional[UUID] = Field(None, description="Optional conversation ID for continuing a chat")


@router.post(
    "/notebooks/{notebook_id}/ask",
    summary="Ask a question about a notebook (Server-Sent Events streaming)",
)
async def ask_question_stream(
    notebook_id: UUID,
    payload: AskRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Answers questions strictly grounded in notebook documents.
    Streams progress steps, answer tokens, and verified citations over SSE.
    """
    # 1. Verify notebook exists
    notebook = await db.get(Notebook, notebook_id)
    if notebook is None:
        raise HTTPException(status_code=404, detail="Notebook not found")

    # 2. Get or create conversation
    conv_id = payload.conversation_id
    if conv_id:
        conversation = await db.get(Conversation, conv_id)
        if conversation is None or conversation.notebook_id != notebook_id:
            conv_id = None

    if conv_id is None:
        conversation = Conversation(id=uuid4(), notebook_id=notebook_id, title=payload.question[:50])
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        conv_id = conversation.id

    # 3. Retrieve prior conversation history for follow-up context
    history_stmt = (
        select(Message)
        .where(Message.conversation_id == conv_id)
        .order_by(Message.created_at.desc())
        .limit(6)
    )
    history_res = await db.execute(history_stmt)
    history_messages = list(reversed(history_res.scalars().all()))
    history_dicts = [{"role": m.role, "content": m.content} for m in history_messages]

    # Save user message
    user_msg = Message(
        id=uuid4(),
        conversation_id=conv_id,
        role="user",
        content=payload.question,
    )
    db.add(user_msg)
    await db.commit()

    # 4. Stream response generator
    async def sse_event_stream() -> AsyncGenerator[dict, None]:
        generator = AnswerGenerator()
        retriever = HybridRetriever(db)

        # Step 1: Query rewriting
        yield {
            "event": "step",
            "data": json.dumps({"step": "rewriting_query", "message": "Analyzing question..."}),
        }
        standalone_query = await generator.rewrite_query_if_needed(payload.question, history_dicts)

        # Step 2: Hybrid Retrieval
        yield {
            "event": "step",
            "data": json.dumps({"step": "retrieving", "message": "Searching documents (vector + keyword)..."}),
        }
        retrieved_chunks = await retriever.retrieve(notebook_id=notebook_id, query=standalone_query, top_k=5)

        # Emit sources preview
        sources_payload = [
            {
                "source_id": c.source_id,
                "chunk_id": str(c.chunk_id),
                "document_id": str(c.document_id),
                "filename": c.filename,
                "page_start": c.page_start,
                "page_end": c.page_end,
                "snippet": c.text[:200] + "...",
            }
            for c in retrieved_chunks
        ]
        yield {
            "event": "sources",
            "data": json.dumps({"sources": sources_payload}),
        }

        # Step 3: Generation
        yield {
            "event": "step",
            "data": json.dumps({"step": "generating", "message": "Synthesizing citation-first answer..."}),
        }

        raw_answer = await generator.generate_answer(query=standalone_query, sources=retrieved_chunks)

        # Step 4: Citation Validation (Strict 'NO SOURCE, NO SENTENCE')
        yield {
            "event": "step",
            "data": json.dumps({"step": "validating", "message": "Validating citations..."}),
        }

        assistant_msg_id = uuid4()
        validator = CitationValidator(retrieved_chunks)
        validation_result = validator.validate(raw_answer, message_id=assistant_msg_id)

        # Stream answer tokens for responsive UI typing effect
        full_text = validation_result.clean_answer_text
        words = full_text.split(" ")
        for i, word in enumerate(words):
            chunk_word = word + (" " if i < len(words) - 1 else "")
            yield {
                "event": "token",
                "data": json.dumps({"token": chunk_word}),
            }
            await asyncio.sleep(0.015)  # Smooth typing pacing

        # Step 5: Persist assistant message and citations in database
        assistant_msg = Message(
            id=assistant_msg_id,
            conversation_id=conv_id,
            role="assistant",
            content=full_text,
            not_found=validation_result.not_found,
        )
        db.add(assistant_msg)

        for cit in validation_result.citation_records:
            cit_obj = Citation(
                id=uuid4(),
                message_id=assistant_msg_id,
                chunk_id=cit["chunk_id"],
                marker=cit["marker"],
                quote=cit["quote"],
                page=cit["page"],
            )
            db.add(cit_obj)

        await db.commit()

        # Step 6: Done event
        yield {
            "event": "done",
            "data": json.dumps({
                "message_id": str(assistant_msg_id),
                "conversation_id": str(conv_id),
                "answer": full_text,
                "not_found": validation_result.not_found,
                "citations": [
                    {
                        "marker": c["marker"],
                        "chunk_id": str(c["chunk_id"]),
                        "page": c["page"],
                        "quote": c["quote"],
                    }
                    for c in validation_result.citation_records
                ],
            }),
        }

    return EventSourceResponse(sse_event_stream())
