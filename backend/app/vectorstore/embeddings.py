import asyncio
import hashlib
import logging
import math
import time
from typing import List
from app.core.config import settings

logger = logging.getLogger("app.vectorstore.embeddings")

VECTOR_DIMENSION = 768


class EmbeddingService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model = settings.GEMINI_EMBEDDING_MODEL or "gemini-embedding-001"
        self._genai_client = None

    def _get_client(self):
        if self._genai_client is None and self.api_key:
            try:
                from google import genai
                self._genai_client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Could not initialize Google GenAI Client: {e}")
        return self._genai_client

    def _fallback_embedding(self, text: str) -> List[float]:
        """
        Deterministic, zero-centered, L2-normalized pseudo-semantic vector of dimension 768.
        Uses sign hashing (Random Projection / Hash Trick) with stopword removal and sublinear TF scaling.
        Expected inner product between unrelated texts is ~0.0 (orthogonal), avoiding the ~0.35 floor.
        """
        import re
        from collections import Counter

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

        vec = [0.0] * VECTOR_DIMENSION
        # Clean and tokenize words
        raw_tokens = re.findall(r"\b[a-zA-Z0-9_\-\.]{2,}\b", text.lower())
        tokens = [t for t in raw_tokens if t not in STOPWORDS]
        if not tokens:
            # If all stopwords, retain raw tokens to prevent degenerate zero vector
            tokens = raw_tokens if raw_tokens else ["empty"]

        # Feature extraction: unigrams + bigrams
        features = list(tokens)
        for i in range(len(tokens) - 1):
            features.append(f"{tokens[i]}_{tokens[i+1]}")

        counts = Counter(features)

        for feat, count in counts.items():
            # Sublinear TF scaling
            tf_weight = 1.0 + math.log(count)

            # Hash into multiple coordinates with signed random projection (+1 or -1)
            h = int(hashlib.sha256(feat.encode("utf-8")).hexdigest(), 16)
            
            for offset in (0, 16, 32):
                h_val = (h >> offset)
                idx = h_val % VECTOR_DIMENSION
                # Sign bit: odd -> +1, even -> -1 (ensures zero mean, orthogonal noise)
                sign = 1.0 if ((h_val >> 15) & 1) else -1.0
                vec[idx] += sign * tf_weight

        # L2 Normalize
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 1e-9:
            vec = [x / norm for x in vec]
        else:
            vec[0] = 1.0
        return vec

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate vector embeddings for a list of texts."""
        if not texts:
            return []

        client = self._get_client()
        if client and self.api_key:
            candidate_models = [self.model or "gemini-embedding-001"]
            alt = "gemini-embedding-001" if ("preview" in candidate_models[0] or "2" in candidate_models[0]) else "gemini-embedding-2-preview"
            if alt not in candidate_models:
                candidate_models.append(alt)

            for cand_model in candidate_models:
                try:
                    from google.genai import types
                    emb_config = types.EmbedContentConfig(output_dimensionality=VECTOR_DIMENSION)
                    sem = asyncio.Semaphore(5)

                    async def embed_single(text: str) -> List[float]:
                        for attempt in range(2):
                            try:
                                async with sem:
                                    res = await client.aio.models.embed_content(
                                        model=cand_model,
                                        contents=text,
                                        config=emb_config,
                                    )
                                if res and res.embeddings and res.embeddings[0].values:
                                    return list(res.embeddings[0].values)
                            except Exception as e:
                                err_str = str(e)
                                if "per day limit exceeded" in err_str or "retryDelay" in err_str:
                                    raise
                                if ("429" in err_str or "RESOURCE_EXHAUSTED" in err_str) and attempt < 1:
                                    await asyncio.sleep(1.5)
                                else:
                                    raise
                        return self._fallback_embedding(text)

                    embeddings = await asyncio.gather(*[embed_single(t) for t in texts])
                    if len(embeddings) == len(texts):
                        self.model = cand_model
                        return embeddings
                except Exception as e:
                    logger.warning(f"Embedding with model {cand_model} failed ({e}). Trying next fallback.")

        # Local fallback
        return [self._fallback_embedding(t) for t in texts]

    async def get_query_embedding(self, query: str) -> List[float]:
        """Generate vector embedding for a single search/chat query."""
        res = await self.get_embeddings([query])
        return res[0]


embedding_service = EmbeddingService()

