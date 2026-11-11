import asyncio
import hashlib
import logging
import math
import re
import time
from collections import Counter
from typing import Any, Dict, List, Optional

from langchain_core.embeddings import Embeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.core.config import settings

logger = logging.getLogger("app.rag.embeddings")

VECTOR_DIMENSION = 768

STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but",
    "by", "can", "could", "did", "do", "does", "doing", "down", "during", "each", "few", "for",
    "from", "further", "had", "has", "have", "having", "he", "her", "here", "hers", "herself",
    "him", "himself", "his", "how", "i", "if", "in", "into", "is", "it", "its", "itself", "just",
    "me", "more", "most", "my", "myself", "no", "nor", "not", "now", "of", "off", "on", "once",
    "only", "or", "other", "our", "ours", "ourselves", "out", "over", "own", "same", "she",
    "should", "so", "some", "such", "than", "that", "the", "their", "theirs", "them", "themselves",
    "then", "there", "these", "they", "this", "those", "through", "to", "too", "under", "until",
    "up", "very", "was", "we", "were", "what", "when", "where", "which", "while", "who", "whom",
    "why", "with", "would", "you", "your", "yours", "yourself", "yourselves"
}


class GeminiEmbeddingService(Embeddings):
    """
    Production-grade LangChain-compatible embedding service for Google Gemini embeddings.
    Includes rate-limit handling, automatic retries with exponential backoff, batching,
    dimension validation, and deterministic zero-mean fallback projection.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        dimension: int = VECTOR_DIMENSION,
        batch_size: int = 16,
        max_retries: int = 3,
    ):
        self.api_key = api_key or settings.effective_gemini_api_key
        self.model_name = model_name or settings.GEMINI_EMBEDDING_MODEL or "text-embedding-004"
        self.dimension = dimension
        self.batch_size = batch_size
        self.max_retries = max_retries

        self._quota_exhausted_until = 0.0
        self._total_requests = 0
        self._total_characters = 0
        self._lc_embeddings: Optional[GoogleGenerativeAIEmbeddings] = None

        if self.api_key:
            self._init_langchain_embeddings()

    def _init_langchain_embeddings(self) -> None:
        try:
            self._lc_embeddings = GoogleGenerativeAIEmbeddings(
                model=self.model_name,
                google_api_key=self.api_key,
                output_dimensionality=self.dimension,
            )
        except Exception as e:
            logger.warning(f"Could not initialize LangChain GoogleGenerativeAIEmbeddings: {e}")
            self._lc_embeddings = None

    def _deterministic_fallback(self, text: str) -> List[float]:
        """
        Zero-mean, L2-normalized deterministic pseudo-semantic vector of dimension 768.
        Used when API quota is exhausted or running in offline tests.
        """
        vec = [0.0] * self.dimension
        raw_tokens = re.findall(r"\b[a-zA-Z0-9_\-\.]{2,}\b", text.lower())
        tokens = [t for t in raw_tokens if t not in STOPWORDS]
        if not tokens:
            tokens = raw_tokens if raw_tokens else ["empty"]

        features = list(tokens)
        for i in range(len(tokens) - 1):
            features.append(f"{tokens[i]}_{tokens[i+1]}")

        counts = Counter(features)
        for feat, count in counts.items():
            tf_weight = 1.0 + math.log(count)
            h = int(hashlib.sha256(feat.encode("utf-8")).hexdigest(), 16)
            for offset in (0, 16, 32):
                h_val = h >> offset
                idx = h_val % self.dimension
                sign = 1.0 if ((h_val >> 15) & 1) else -1.0
                vec[idx] += sign * tf_weight

        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 1e-9:
            return [x / norm for x in vec]
        vec[0] = 1.0
        return vec

    async def _embed_batch_with_retry(self, texts: List[str], is_query: bool = False) -> List[List[float]]:
        # Check quota cooldown
        now = time.time()
        if now < self._quota_exhausted_until:
            return [self._deterministic_fallback(t) for t in texts]

        if not self._lc_embeddings or not self.api_key:
            return [self._deterministic_fallback(t) for t in texts]

        for attempt in range(self.max_retries):
            try:
                if is_query and len(texts) == 1:
                    vec = await self._lc_embeddings.aembed_query(texts[0])
                    results = [vec]
                else:
                    results = await self._lc_embeddings.aembed_documents(texts)

                # Validate dimensions
                for v in results:
                    if len(v) != self.dimension:
                        logger.warning(f"Embedding dimension mismatch: expected {self.dimension}, got {len(v)}")

                self._total_requests += 1
                self._total_characters += sum(len(t) for t in texts)

                # Strict L2 unit normalization for cosine similarity
                normalized_results = []
                for v in results:
                    norm = math.sqrt(sum(x * x for x in v))
                    if norm > 1e-9:
                        normalized_results.append([x / norm for x in v])
                    else:
                        normalized_results.append(v)

                return normalized_results

            except Exception as e:
                err_msg = str(e)
                is_rate_limit = "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "quota" in err_msg.lower()

                if is_rate_limit:
                    logger.warning(
                        f"Gemini embedding quota reached. Cooling down remote calls and using zero-mean projection. ({err_msg[:120]})"
                    )
                    self._quota_exhausted_until = time.time() + 1800  # Cooldown 30 minutes
                    return [self._deterministic_fallback(t) for t in texts]

                if attempt < self.max_retries - 1:
                    backoff = 2 ** attempt * 0.5
                    logger.warning(f"Embedding retry {attempt + 1}/{self.max_retries} after {backoff}s due to: {e}")
                    await asyncio.sleep(backoff)
                else:
                    logger.error(f"Embedding batch failed after {self.max_retries} attempts: {e}")
                    return [self._deterministic_fallback(t) for t in texts]

        return [self._deterministic_fallback(t) for t in texts]

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """Async LangChain interface for embedding documents in batches."""
        if not texts:
            return []

        all_embeddings: List[List[float]] = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            # Replace empty strings with placeholder to avoid API errors
            cleaned_batch = [t.strip() if t.strip() else "[empty]" for t in batch]
            batch_embeddings = await self._embed_batch_with_retry(cleaned_batch, is_query=False)
            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    async def aembed_query(self, text: str) -> List[float]:
        """Async LangChain interface for embedding a query."""
        clean_text = text.strip() if text.strip() else "[query]"
        embeddings = await self._embed_batch_with_retry([clean_text], is_query=True)
        return embeddings[0]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Sync LangChain interface."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Running inside existing loop (e.g. FastAPI / asyncio), use run_coroutine_threadsafe or nest
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    return pool.submit(asyncio.run, self.aembed_documents(texts)).result()
            return loop.run_until_complete(self.aembed_documents(texts))
        except RuntimeError:
            return asyncio.run(self.aembed_documents(texts))

    def embed_query(self, text: str) -> List[float]:
        """Sync LangChain interface."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    return pool.submit(asyncio.run, self.aembed_query(text)).result()
            return loop.run_until_complete(self.aembed_query(text))
        except RuntimeError:
            return asyncio.run(self.aembed_query(text))

    def get_telemetry(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "dimension": self.dimension,
            "total_requests": self._total_requests,
            "total_characters": self._total_characters,
            "quota_exhausted": time.time() < self._quota_exhausted_until,
        }


gemini_embeddings = GeminiEmbeddingService()

