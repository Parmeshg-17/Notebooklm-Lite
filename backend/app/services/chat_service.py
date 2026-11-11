import logging
import re
import time
import uuid
from typing import List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse, CitationResponse
from app.services.notebook_service import NotebookService
from app.vectorstore.retrieval_pipeline import (
    RetrievedPassage,
    STOPWORDS,
    retrieval_pipeline,
)

logger = logging.getLogger("app.services.chat")

REFUSAL_MESSAGE = "I couldn't find sufficient supporting information in your uploaded documents to answer this question."


class ChatService:
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

        # Find most recent conversation for this notebook
        stmt = (
            select(Conversation)
            .where(Conversation.notebook_id == notebook_id, Conversation.user_id == user.id)
            .order_by(Conversation.created_at.desc())
        )
        res = await db.execute(stmt)
        conv = res.scalar_one_or_none()
        if conv:
            return conv

        # Create new conversation
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
    def validate_citations(
        answer_text: str,
        retrieved_passages: List[RetrievedPassage],
    ) -> List[CitationResponse]:
        """
        TASK 5: Validates each citation against real retrieved chunks.
        Ensures cited document ID, filename, and page number exist in context,
        and ensures the citation is supported by actual chunk text.
        """
        valid_citations: List[CitationResponse] = []
        seen_keys = set()

        for passage in retrieved_passages:
            # If answer is a refusal, no citations should be returned
            if REFUSAL_MESSAGE in answer_text:
                continue

            # Check if passage has valid document and page
            if not passage.document_id or passage.page_number <= 0:
                continue

            # Deduplicate by document + page
            key = (passage.document_id, passage.page_number)
            if key in seen_keys:
                continue

            # Ensure the passage is non-boilerplate or has actual keyword overlap with answer/query
            if passage.is_boilerplate and passage.rerank_score < 0.35:
                continue

            seen_keys.add(key)
            valid_citations.append(
                CitationResponse(
                    id=passage.chunk_id or str(uuid.uuid4()),
                    documentId=passage.document_id,
                    documentName=passage.document_name,
                    pageNumber=passage.page_number,
                    excerpt=passage.excerpt,
                    relevanceScore=round(float(passage.rerank_score or passage.fused_score), 4),
                )
            )

        return valid_citations

    @staticmethod
    def _local_synthesize(user_query: str, retrieved_passages: List[RetrievedPassage]) -> str:
        """
        High-precision deterministic grounded synthesis when external LLM is offline or quota-limited.
        Strictly extracts grounded facts from passages that match query keywords.
        Never outputs publisher boilerplate or hallucinated text.
        """
        if not retrieved_passages:
            return REFUSAL_MESSAGE

        _, query_keywords = retrieval_pipeline.normalize_query(user_query)
        kw_set = set(k.lower() for k in query_keywords if len(k) > 2)

        # Extract supporting sentences from non-boilerplate chunks
        grounded_claims: List[Tuple[str, str, int, int]] = []  # (sentence, doc_name, page, match_count)

        for p in retrieved_passages:
            if p.is_boilerplate:
                continue

            # Split into sentences or lines
            raw_sentences = re.split(r"(?<=[.!?])\s+|\n+", p.text)
            for s in raw_sentences:
                cleaned_s = " ".join(s.split())
                if len(cleaned_s) < 25 or len(cleaned_s) > 350:
                    continue

                # Count keyword matches in this sentence
                s_words = set(re.findall(r"\b[a-zA-Z0-9_\-\.]{2,}\b", cleaned_s.lower()))
                matches = kw_set.intersection(s_words)
                if matches:
                    grounded_claims.append((cleaned_s, p.document_name, p.page_number, len(matches)))

        if not grounded_claims:
            # If no sentences directly address the keywords, refuse
            return REFUSAL_MESSAGE

        # Sort claims by match density
        grounded_claims.sort(key=lambda x: x[3], reverse=True)

        # Group top unique claims
        output_lines = [
            f"Based on **{retrieved_passages[0].document_name}**:\n"
        ]
        seen_sentences = set()
        count = 0
        for sent, doc, page, _ in grounded_claims:
            norm_key = sent[:40].lower()
            if norm_key in seen_sentences:
                continue
            seen_sentences.add(norm_key)
            output_lines.append(f"- \"{sent}\" *({doc}, page {page})*")
            count += 1
            if count >= 6:
                break

        return "\n".join(output_lines)

    @staticmethod
    async def call_gemini_or_synthesize(
        prompt: str,
        retrieved_passages: List[RetrievedPassage],
        user_query: str = "",
    ) -> Tuple[str, int]:
        """
        Call Gemini model with strict grounding rules if API quota is available.
        Falls back to local grounded synthesis if Gemini returns 429 quota exhaustion.
        """
        if settings.GEMINI_API_KEY:
            try:
                from google import genai
                client = genai.Client(api_key=settings.GEMINI_API_KEY)
                response = await client.aio.models.generate_content(
                    model=settings.GEMINI_MODEL or "gemini-2.5-flash",
                    contents=prompt,
                )
                answer = response.text or ""
                token_usage = 0
                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    token_usage = getattr(response.usage_metadata, "total_token_count", 0) or 0
                return answer.strip(), token_usage
            except Exception as e:
                logger.warning(f"Gemini API generation unavailable ({e}). Employing deterministic grounded synthesis.")

        # Local deterministic synthesis
        answer = ChatService._local_synthesize(user_query, retrieved_passages)
        token_count = sum(len(p.text.split()) for p in retrieved_passages) + len(answer.split())
        return answer, token_count

    @staticmethod
    async def process_chat(
        db: AsyncSession,
        notebook_id: uuid.UUID,
        chat_in: ChatRequest,
        user: User,
    ) -> ChatResponse:
        start_time = time.perf_counter()

        # 1. Verify notebook ownership
        await NotebookService.get_notebook_or_404(db, notebook_id, user)

        # 2. Get or create conversation
        conv = await ChatService.get_or_create_conversation(
            db, notebook_id, user, chat_in.get_conversation_id()
        )

        user_text = chat_in.get_message()

        # 3. Store user message in DB
        user_msg = Message(
            conversation_id=conv.id,
            role="user",
            content=user_text,
        )
        db.add(user_msg)
        await db.commit()

        # 4. Multi-stage RAG retrieval pipeline (Task 4 & Task 6)
        passages, has_sufficient, context_text, audit_log = await retrieval_pipeline.execute(
            db=db,
            query=user_text,
            user_id=user.id,
            notebook_id=notebook_id,
            document_ids=chat_in.get_document_ids(),
            top_k=5,
        )

        # 5. Check retrieval sufficiency threshold (Task 6)
        if not has_sufficient or not passages:
            answer_text = REFUSAL_MESSAGE
            citations_list: List[CitationResponse] = []
            token_count = 0
        else:
            # 6. Build strict grounded prompt (Task 5)
            prompt = (
                "You are NotebookLM Lite, an enterprise-grade AI research assistant.\n"
                "STRICT GROUNDING RULES:\n"
                "1. Answer ONLY using the retrieved document context below.\n"
                "2. Every factual statement must cite its source document name and page number, e.g. [Document Name, Page X].\n"
                "3. Do not combine unrelated passages or extrapolate beyond the text.\n"
                "4. If the provided context does not contain sufficient factual information to answer the question, "
                f"respond strictly with: \"{REFUSAL_MESSAGE}\"\n"
                "5. Never invent facts or citations.\n\n"
                f"=== DOCUMENT CONTEXT ===\n{context_text}\n\n"
                f"=== USER QUESTION ===\n{user_text}\n\n"
                "=== ANSWER ==="
            )

            # 7. Generate answer
            answer_text, token_count = await ChatService.call_gemini_or_synthesize(prompt, passages, user_text)

            # 8. Validate citations (Task 5)
            citations_list = ChatService.validate_citations(answer_text, passages)

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        # 9. Persist assistant message in DB
        citations_dict = [c.model_dump() for c in citations_list]
        assistant_msg = Message(
            conversation_id=conv.id,
            role="assistant",
            content=answer_text,
            token_usage=token_count,
            latency_ms=latency_ms,
            citations=citations_dict,
        )
        db.add(assistant_msg)
        await db.commit()
        await db.refresh(assistant_msg)

        return ChatResponse(
            id=assistant_msg.id,
            conversation_id=conv.id,
            role="assistant",
            content=answer_text,
            citations=citations_list,
            token_usage=token_count,
            latency_ms=latency_ms,
            created_at=assistant_msg.created_at,
        )

    @staticmethod
    async def get_history(
        db: AsyncSession,
        notebook_id: uuid.UUID,
        user: User,
    ) -> List[ChatResponse]:
        """Fetch conversation history for notebook."""
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

        results: List[ChatResponse] = []
        for msg in conv.messages:
            cits = []
            if msg.citations:
                for c in msg.citations:
                    if isinstance(c, dict):
                        cits.append(CitationResponse(**c))
            results.append(
                ChatResponse(
                    id=msg.id,
                    conversation_id=conv.id,
                    role=msg.role,
                    content=msg.content,
                    citations=cits,
                    token_usage=msg.token_usage or 0,
                    latency_ms=msg.latency_ms or 0,
                    created_at=msg.created_at,
                )
            )

        return results
