"""
Citation-First Answer Generator.
Implements:
1. Follow-up query rewriting (standalone query synthesis)
2. Citation-first prompt formatting with numbered source contexts
3. Structured JSON generation enforcing 'NO SOURCE, NO SENTENCE'
4. Multi-provider support (OpenAI, Gemini, and Local Extractive Fallback)
"""

import json
import re
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.rag.retrieval import RetrievedChunk

logger = get_logger(__name__)
settings = get_settings()

SYSTEM_CITATION_PROMPT = """You are a citation-first factual question-answering assistant.

CORE RULES:
1. Answer ONLY using the numbered sources provided below.
2. Never use outside knowledge or make assumptions not directly supported by the sources.
3. NO SOURCE, NO SENTENCE: Every single statement you make MUST end with the bracketed source ID(s) backing it, e.g. [1] or [1][2].
4. If the provided sources do NOT contain enough information to answer the question, you MUST return:
   {"sentences": [], "not_found": true}
5. You must output strictly valid JSON matching this schema:
{
  "sentences": [
    {
      "text": "Statement text without trailing brackets.",
      "source_ids": [1]
    }
  ],
  "not_found": false
}
"""


class AnswerGenerator:
    """Manages question rewriting and citation-first structured generation."""

    def __init__(self) -> None:
        self.provider = settings.llm_provider.lower()

    async def rewrite_query_if_needed(
        self,
        query: str,
        conversation_history: List[Dict[str, str]],
    ) -> str:
        """
        Rewrites conversational follow-up questions (e.g. 'And what is the deadline?')
        into a self-contained standalone search query using conversation context.
        """
        if not conversation_history:
            return query

        # If question is already long and self-contained, keep as is
        if len(query.split()) > 10 and not any(w in query.lower() for w in ["it", "they", "that", "this", "also", "and", "then"]):
            return query

        recent_history = conversation_history[-4:]
        history_summary = " ".join([m.get("content", "") for m in recent_history])

        # If Gemini is configured
        gemini_key = settings.gemini_api_key or (settings.llm_api_key if self.provider == "gemini" else "")
        if self.provider == "gemini" and gemini_key and not gemini_key.startswith("your-"):
            try:
                model_name = settings.llm_model if settings.llm_model and not settings.llm_model.startswith("gpt-") else "gemini-3.5-flash-lite"
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={gemini_key}"
                prompt = f"Given this conversation context:\n{history_summary}\n\nRewrite this follow-up into a standalone search query: '{query}'\nReturn ONLY the rewritten query."
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.0},
                }
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(url, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    rewritten = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    logger.info("Rewrote follow-up query with Gemini", original=query, rewritten=rewritten)
                    return rewritten
            except Exception as e:
                logger.warning("Gemini query rewrite failed, using original", error=str(e))

        # If OpenAI is configured
        api_key = settings.openai_api_key or settings.llm_api_key
        if self.provider == "openai" and api_key and not api_key.startswith("your-"):
            try:
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=api_key)
                prompt = f"Given this conversation context:\n{history_summary}\n\nRewrite this follow-up into a standalone search query: '{query}'\nReturn ONLY the rewritten query."
                resp = await client.chat.completions.create(
                    model=settings.llm_model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=60,
                    temperature=0.0,
                )
                rewritten = resp.choices[0].message.content.strip()
                logger.info("Rewrote follow-up query", original=query, rewritten=rewritten)
                return rewritten
            except Exception as e:
                logger.warning("Query rewrite failed, using original", error=str(e))

        # Local heuristic synthesis
        last_user_msg = next((m["content"] for m in reversed(recent_history) if m.get("role") == "user"), "")
        if last_user_msg:
            return f"{query} regarding {last_user_msg}"
        return query

    def format_sources_context(self, chunks: List[RetrievedChunk]) -> str:
        """Format retrieved chunks as numbered source entries for the prompt."""
        formatted = []
        for c in chunks:
            pages = f"p.{c.page_start}" if c.page_start == c.page_end else f"pp.{c.page_start}-{c.page_end}"
            formatted.append(f"[{c.source_id}] {c.filename} {pages}\n\"{c.text}\"\n")
        return "\n".join(formatted)

    async def generate_answer(
        self,
        query: str,
        sources: List[RetrievedChunk],
    ) -> Dict[str, Any]:
        """Generate structured answer with strict citations from sources."""
        if not sources:
            return {"sentences": [], "not_found": True}

        sources_context = self.format_sources_context(sources)
        user_message = f"SOURCES:\n{sources_context}\n\nQUESTION: {query}\n\nProvide your JSON answer following all rules."

        # 1. Gemini Generation
        gemini_key = settings.gemini_api_key or (settings.llm_api_key if self.provider == "gemini" else "")
        if self.provider == "gemini" and gemini_key and not gemini_key.startswith("your-"):
            try:
                model_name = settings.llm_model if settings.llm_model and not settings.llm_model.startswith("gpt-") else "gemini-3.5-flash-lite"
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={gemini_key}"
                payload = {
                    "contents": [{"parts": [{"text": SYSTEM_CITATION_PROMPT + "\n\n" + user_message}]}],
                    "generationConfig": {
                        "responseMimeType": "application/json",
                        "temperature": 0.1,
                    },
                }
                async with httpx.AsyncClient(timeout=25.0) as client:
                    resp = await client.post(url, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    raw_json = data["candidates"][0]["content"]["parts"][0]["text"]
                    return json.loads(raw_json)
            except Exception as e:
                logger.warning("Gemini answer generation failed, falling back to local synthesis", error=str(e))

        # 2. OpenAI Generation
        api_key = settings.openai_api_key or settings.llm_api_key
        has_openai = self.provider == "openai" and api_key and not api_key.startswith("your-")

        if has_openai:
            try:
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=api_key)
                resp = await client.chat.completions.create(
                    model=settings.llm_model,
                    messages=[
                        {"role": "system", "content": SYSTEM_CITATION_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                )
                raw_json = resp.choices[0].message.content
                return json.loads(raw_json)
            except Exception as e:
                logger.warning("OpenAI generation failed, using local synthesis", error=str(e))

        # Extractive Local Synthesizer (Zero-Key High-Precision Fallback)
        return self._local_extractive_answer(query, sources)

    def _local_extractive_answer(
        self,
        query: str,
        sources: List[RetrievedChunk],
    ) -> Dict[str, Any]:
        """
        Extractive answer synthesizer for local development without external API keys.
        Scans retrieved chunks, selects highest-overlap supporting sentences,
        and attaches valid source IDs.
        """
        STOP_WORDS = {
            "what", "who", "when", "where", "why", "how", "is", "are", "the", "a", "an",
            "and", "or", "in", "on", "of", "to", "for", "with", "as", "by", "at", "from",
            "it", "its", "that", "this", "be", "was", "were", "will", "would", "can", "could",
            "should", "do", "does", "did", "have", "has", "had", "which", "there", "their",
            "they", "them", "about", "me", "my", "you", "your", "any", "some", "all", "not"
        }
        query_words = set(re.findall(r"\w+", query.lower())) - STOP_WORDS
        if not query_words:
            return {"sentences": [], "not_found": True}

        candidates: List[tuple[float, str, int]] = []

        for chunk in sources:
            sentences = re.split(r"(?<=[.!?])\s+", chunk.text)
            for i, s in enumerate(sentences):
                s_clean = s.strip()
                if len(s_clean) < 15:
                    continue
                s_words = set(re.findall(r"\w+", s_clean.lower())) - STOP_WORDS
                matched = query_words & s_words
                overlap = len(matched)

                min_required = 1 if len(query_words) <= 2 else 2
                if overlap >= min_required:
                    score = overlap / len(query_words)
                    # If this sentence looks like a question or section heading and is followed by an answer, grab the answer
                    if (s_clean.endswith("?") or re.match(r"^Q\d+[\.:]", s_clean)) and i + 1 < len(sentences):
                        next_sentence = sentences[i + 1].strip()
                        if len(next_sentence) >= 15:
                            cleaned_ans = re.sub(r"^(?:Answer|A)\s*:\s*", "", next_sentence, flags=re.IGNORECASE)
                            candidates.append((score + 0.1, cleaned_ans, chunk.source_id))
                            continue
                    candidates.append((score, s_clean, chunk.source_id))

        if not candidates:
            return {"sentences": [], "not_found": True}

        # Sort by relevance descending
        candidates.sort(key=lambda x: x[0], reverse=True)
        top_candidates = [c for c in candidates if c[0] >= 0.25][:3]
        if not top_candidates:
            return {"sentences": [], "not_found": True}

        sentences_out = []
        for _, text_val, sid in top_candidates:
            sentences_out.append({
                "text": text_val,
                "source_ids": [sid],
            })

        return {"sentences": sentences_out, "not_found": False}
