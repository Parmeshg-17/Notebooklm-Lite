import asyncio
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings
from app.rag.generation.answer_parser import (
    AnswerParser,
    GroundedCitationItem,
    ParsedGenerationResult,
)
from app.rag.generation.prompts import (
    REFUSAL_MESSAGE,
    STRICT_SYSTEM_PROMPT,
    build_generation_prompt,
)

logger = logging.getLogger("app.rag.gemini_generator")


class GeminiGenerator:
    """
    Production grounded answer generator powered by LangChain ChatGoogleGenerativeAI.
    Strictly grounds claims in context, enforces JSON schema output, and includes
    a high-precision deterministic fallback when quota limits are reached.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        self.api_key = api_key or settings.effective_gemini_api_key
        self.model_name = model_name or settings.effective_gemini_chat_model
        self._llm: Optional[ChatGoogleGenerativeAI] = None
        self._quota_exhausted_until = 0.0

        if self.api_key:
            self._init_llm()

    def _get_llm(self) -> Optional[ChatGoogleGenerativeAI]:
        """Ensure LLM client is bound to the currently running event loop."""
        if not self.api_key:
            return None
        try:
            loop = asyncio.get_running_loop()
            if getattr(self, "_bound_loop", None) != loop or self._llm is None:
                self._llm = ChatGoogleGenerativeAI(
                    model=self.model_name,
                    google_api_key=self.api_key,
                    temperature=0.0,
                    max_retries=0,
                )
                self._bound_loop = loop
        except RuntimeError:
            if self._llm is None:
                self._init_llm()
        return self._llm

    def _init_llm(self) -> None:
        try:
            self._llm = ChatGoogleGenerativeAI(
                model=self.model_name,
                google_api_key=self.api_key,
                temperature=0.0,
                max_retries=0,
            )
            try:
                self._bound_loop = asyncio.get_running_loop()
            except RuntimeError:
                self._bound_loop = None
        except Exception as e:
            logger.warning(f"Could not initialize ChatGoogleGenerativeAI: {e}")
            self._llm = None

    def _deterministic_synthesis(
        self,
        query: str,
        candidate_chunks: List[Dict[str, Any]],
    ) -> ParsedGenerationResult:
        """
        High-precision deterministic grounded synthesis when external LLM is offline or quota-limited.
        Extracts supporting sentences that match query keywords and formats them with source citations.
        """
        if not candidate_chunks:
            return ParsedGenerationResult(
                answer=REFUSAL_MESSAGE,
                insufficient_evidence=True,
            )

        # Extract keywords
        raw_words = re.findall(r"\b[a-zA-Z0-9_\-\.]{2,}\b", query.lower())
        from app.rag.retrieval.hybrid_retriever import STOPWORDS
        kws = set(w for w in raw_words if w not in STOPWORDS) - {
            "company", "documents", "document", "uploaded", "according", "pdf", "main", "concepts", "summarize", "summary", "explain", "describe", "tell"
        }
        if not kws:
            kws = set(raw_words) - {"the", "in", "of", "a", "an", "is", "it", "to", "for"}

        grounded_claims = []
        citations: List[GroundedCitationItem] = []
        min_matches = 2 if len(kws) >= 4 else 1

        for chunk in candidate_chunks:
            if chunk.get("is_boilerplate"):
                continue

            text = chunk.get("chunk_text") or chunk.get("text", "")
            fname = chunk.get("filename", "Document")
            doc_id = str(chunk.get("document_id", ""))
            chunk_id = str(chunk.get("chunk_id", ""))
            page_num = int(chunk.get("page_number", 1))

            sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
            for s in sentences:
                cleaned_s = " ".join(s.split())
                if len(cleaned_s) < 25 or len(cleaned_s) > 350:
                    continue

                s_words = set(re.findall(r"\b[a-zA-Z0-9_\-\.]{2,}\b", cleaned_s.lower()))
                matches = kws.intersection(s_words)
                if len(matches) >= min_matches:
                    grounded_claims.append((cleaned_s, fname, page_num, len(matches), doc_id, chunk_id))

        # If keyword filtering produced no matches but this is an overview/summary request,
        # extract top salient sentences from the retrieved candidate chunks.
        is_overview_request = any(
            w in query.lower()
            for w in ["summarize", "summary", "overview", "main concept", "main concepts", "outline", "what is this book about", "what this book is about"]
        )
        if not grounded_claims and is_overview_request:
            for chunk in candidate_chunks:
                if chunk.get("is_boilerplate"):
                    continue
                text = chunk.get("chunk_text") or chunk.get("text", "")
                fname = chunk.get("filename", "Document")
                doc_id = str(chunk.get("document_id", ""))
                chunk_id = str(chunk.get("chunk_id", ""))
                page_num = int(chunk.get("page_number", 1))

                sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
                for s in sentences:
                    cleaned_s = " ".join(s.split())
                    if 35 <= len(cleaned_s) <= 300:
                        grounded_claims.append((cleaned_s, fname, page_num, 1, doc_id, chunk_id))
                        if len(grounded_claims) >= 6:
                            break
                if len(grounded_claims) >= 6:
                    break

        if not grounded_claims:
            return ParsedGenerationResult(
                answer=REFUSAL_MESSAGE,
                insufficient_evidence=True,
            )

        grounded_claims.sort(key=lambda x: x[3], reverse=True)

        top_doc_name = ""
        for c in candidate_chunks:
            fn = (c.get("filename") or "").strip()
            if fn:
                top_doc_name = fn
                break
        if not top_doc_name:
            top_doc_name = "Uploaded Document"

        output_lines = [f"Based on **{top_doc_name}**:\n"]
        seen_sentences = set()
        supporting_claims_list = []

        for sent, doc, page, _, d_id, c_id in grounded_claims[:6]:
            doc_label = (doc or "").strip() or top_doc_name
            norm_key = sent[:40].lower()
            if norm_key in seen_sentences:
                continue
            seen_sentences.add(norm_key)

            output_lines.append(f"- \"{sent}\" *({doc_label}, page {page})*")
            supporting_claims_list.append(sent)

            citations.append(
                GroundedCitationItem(
                    claim=sent,
                    document_id=d_id,
                    filename=doc_label,
                    page_number=page,
                    chunk_id=c_id,
                    excerpt=sent[:280],
                )
            )

        answer_text = "\n".join(output_lines)
        return ParsedGenerationResult(
            answer=answer_text,
            citations=citations,
            supporting_claims=supporting_claims_list,
            insufficient_evidence=False,
            input_tokens=sum(len(c.get("chunk_text", "").split()) for c in candidate_chunks),
            output_tokens=len(answer_text.split()),
        )

    async def generate_answer(
        self,
        query: str,
        context_text: str,
        candidate_chunks: List[Dict[str, Any]],
        has_sufficient_evidence: bool = True,
    ) -> ParsedGenerationResult:
        if not has_sufficient_evidence or not candidate_chunks or not context_text.strip():
            return ParsedGenerationResult(
                answer=REFUSAL_MESSAGE,
                insufficient_evidence=True,
            )

        # Check quota cooldown
        llm = self._get_llm()
        if time.time() < self._quota_exhausted_until or not llm:
            return self._deterministic_synthesis(query, candidate_chunks)

        prompt = build_generation_prompt(query, context_text)
        max_attempts = 3

        for attempt in range(max_attempts):
            try:
                messages = [
                    SystemMessage(content=STRICT_SYSTEM_PROMPT),
                    HumanMessage(content=prompt),
                ]
                response = await llm.ainvoke(messages)
                content = response.content if hasattr(response, "content") else response
                if isinstance(content, list):
                    raw_text = "".join(
                        part.get("text", "") if isinstance(part, dict) else getattr(part, "text", str(part))
                        for part in content
                    )
                else:
                    raw_text = str(content)

                in_tokens = 0
                out_tokens = 0
                if hasattr(response, "response_metadata") and response.response_metadata:
                    usage = response.response_metadata.get("usage_metadata") or {}
                    in_tokens = usage.get("prompt_token_count", 0)
                    out_tokens = usage.get("candidates_token_count", 0)

                parsed = AnswerParser.parse_raw_response(str(raw_text), candidate_chunks)
                parsed.input_tokens = in_tokens or len(prompt.split())
                parsed.output_tokens = out_tokens or len(parsed.answer.split())
                return parsed

            except Exception as e:
                err_msg = str(e)
                is_rate_limit = "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "quota" in err_msg.lower()

                if attempt < max_attempts - 1:
                    import random
                    jitter = random.uniform(0.1, 0.5)
                    delay = (2 ** attempt * 1.0) + jitter
                    logger.warning(f"Gemini generation attempt {attempt + 1} failed ({err_msg[:80]}), retrying in {delay:.2f}s...")
                    await asyncio.sleep(delay)
                else:
                    if is_rate_limit:
                        logger.warning(f"Gemini generation quota exhausted. Cooling down: {err_msg[:120]}")
                        self._quota_exhausted_until = time.time() + 1800

                    logger.warning(f"Gemini generation failed ({e}), using deterministic grounded synthesis.")
                    return self._deterministic_synthesis(query, candidate_chunks)


gemini_generator = GeminiGenerator()
