import json
import sys
import uuid
sys.path.insert(0, ".")
from qdrant_client import QdrantClient, models
from app.core.config import settings

client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)
doc_id = str(uuid.UUID("8a9f5eb58f4d47e6a1d5dc32f5146cc9"))

queries_to_probe = [
    ("AlexNet", "alexnet"),
    ("Ilya Sutskever", "sutskever"),
    ("KV cache", "kv cache"),
    ("LoRA", "lora"),
    ("speculative decoding", "speculative"),
    ("quantization", "quantization"),
    ("evaluations", "evaluations"),
    ("hallucination", "hallucination"),
    ("vector database", "vector database"),
    ("chunking", "chunking"),
    ("flashattention", "flashattention"),
    ("fine-tuning", "fine-tuning"),
    ("data leakage", "leakage"),
    ("RAG", "retrieval augmented"),
    ("temperature", "temperature"),
]

results = {}
for label, term in queries_to_probe:
    points, _ = client.scroll(
        collection_name="notebooklm_documents",
        scroll_filter=models.Filter(must=[
            models.FieldCondition(key="document_id", match=models.MatchValue(value=doc_id)),
        ]),
        limit=1000,
        with_payload=True,
    )
    for p in points:
        txt = p.payload.get("text", "")
        if term in txt.lower():
            pg = p.payload.get("page_number")
            results[label] = {
                "page": pg,
                "text_snippet": txt[:300].replace("\n", " "),
            }
            break

with open("backend/tests/probe_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"Probed {len(results)} topics successfully.")
