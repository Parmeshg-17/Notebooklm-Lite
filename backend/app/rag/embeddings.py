"""
Embedding Provider Abstraction.
Supports OpenAI, Gemini, and Local (zero-key fallback) embedding models.
Configured dynamically via environment variables.
"""

from abc import ABC, abstractmethod
import hashlib
import math
from typing import List

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class BaseEmbeddingProvider(ABC):
    """Abstract interface for generating vector embeddings."""

    @abstractmethod
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of text strings into vector representations."""
        pass

    @abstractmethod
    def embed_query(self, query: str) -> List[float]:
        """Embed a single search query."""
        pass


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """OpenAI embeddings using text-embedding-3-small or text-embedding-ada-002."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.model = model or settings.embedding_model
        api_key = api_key or settings.openai_api_key or settings.llm_api_key
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        # OpenAI supports up to 2048 inputs per request
        batch_size = 128
        all_embeddings: List[List[float]] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = self.client.embeddings.create(input=batch, model=self.model)
            all_embeddings.extend([item.embedding for item in response.data])

        return all_embeddings

    def embed_query(self, query: str) -> List[float]:
        response = self.client.embeddings.create(input=query, model=self.model)
        return response.data[0].embedding


class GeminiEmbeddingProvider(BaseEmbeddingProvider):
    """Google Gemini embeddings using gemini-embedding-001 with 1536 output dimensions."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        raw_model = model or settings.embedding_model or "gemini-embedding-001"
        if raw_model.startswith("models/"):
            raw_model = raw_model.replace("models/", "")
        if "text-embedding-004" in raw_model:
            raw_model = "gemini-embedding-001"
        self.model = raw_model
        self.api_key = api_key or settings.gemini_api_key or settings.llm_api_key
        self.dimension = settings.embedding_dimension or 1536

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts or not self.api_key:
            return [[0.0] * self.dimension for _ in texts]

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:batchEmbedContents?key={self.api_key}"
        batch_size = 50
        all_embeddings: List[List[float]] = []

        try:
            with httpx.Client(timeout=30.0) as client:
                for i in range(0, len(texts), batch_size):
                    batch = texts[i : i + batch_size]
                    payload = {
                        "requests": [
                            {
                                "model": f"models/{self.model}",
                                "content": {"parts": [{"text": t}]},
                                "outputDimensionality": self.dimension,
                            }
                            for t in batch
                        ]
                    }
                    resp = client.post(url, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                    for emb_item in data.get("embeddings", []):
                        all_embeddings.append(emb_item.get("values", [0.0] * self.dimension))
            return all_embeddings
        except Exception as e:
            logger.warning("Gemini embed_texts failed, falling back to local deterministic embeddings", error=str(e))
            fallback = LocalDeterministicEmbeddingProvider(self.dimension)
            return fallback.embed_texts(texts)

    def embed_query(self, query: str) -> List[float]:
        res = self.embed_texts([query])
        return res[0] if res else [0.0] * self.dimension


class LocalDeterministicEmbeddingProvider(BaseEmbeddingProvider):
    """
    Offline/Zero-Key Deterministic Embedding Provider.
    Creates 1536-dimensional normalized vectors from token n-grams and hashing.
    Enables instant offline testing and CI/CD without API keys or costs.
    """

    def __init__(self, dimension: int | None = None) -> None:
        self.dimension = dimension or settings.embedding_dimension or 1536

    def _embed_single(self, text: str) -> List[float]:
        vec = [0.0] * self.dimension
        words = text.lower().split()
        if not words:
            return vec

        # Bag of words and character n-grams hashing
        for i, word in enumerate(words):
            h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dimension
            sign = 1.0 if (h >> 1) & 1 else -1.0
            vec[idx] += sign * 1.5

            # Bigrams
            if i < len(words) - 1:
                bigram = f"{word}_{words[i+1]}"
                h_bi = int(hashlib.sha256(bigram.encode("utf-8")).hexdigest(), 16)
                idx_bi = h_bi % self.dimension
                sign_bi = 1.0 if (h_bi >> 1) & 1 else -1.0
                vec[idx_bi] += sign_bi * 2.0

        # Normalize to unit length
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        return vec

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        return [self._embed_single(t) for t in texts]

    def embed_query(self, query: str) -> List[float]:
        return self._embed_single(query)


def get_embedding_provider() -> BaseEmbeddingProvider:
    """Factory creating the configured embedding provider with graceful local fallback."""
    provider = settings.embedding_provider.lower()

    if provider == "openai":
        api_key = settings.openai_api_key or settings.llm_api_key
        if api_key and api_key != "your-openai-key-here" and api_key != "your-api-key-here":
            try:
                return OpenAIEmbeddingProvider(api_key=api_key)
            except Exception as e:
                logger.warning("Failed to initialize OpenAI embeddings, falling back to local", error=str(e))
        else:
            logger.info("No valid OpenAI API key found, using local deterministic embeddings")
            return LocalDeterministicEmbeddingProvider()

    elif provider == "gemini":
        api_key = settings.gemini_api_key or settings.llm_api_key
        if api_key and api_key != "your-gemini-key-here" and api_key != "your-api-key-here":
            try:
                return GeminiEmbeddingProvider(api_key=api_key)
            except Exception as e:
                logger.warning("Failed to initialize Gemini embeddings, falling back to local", error=str(e))
        else:
            logger.info("No valid Gemini API key found, using local deterministic embeddings")
            return LocalDeterministicEmbeddingProvider()

    return LocalDeterministicEmbeddingProvider()
