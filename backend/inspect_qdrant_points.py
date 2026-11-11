import asyncio
import sys
sys.path.insert(0, "backend")

from app.rag.retrieval.qdrant_store import qdrant_store

async def inspect():
    client = qdrant_store.get_client()
    points, _ = client.scroll(
        collection_name=qdrant_store.collection_name,
        limit=10,
        with_payload=True,
    )
    print(f"Total points returned: {len(points)}")
    for p in points:
        payload = p.payload or {}
        print("Point:", p.id)
        for k in ["user_id", "owner_id", "notebook_id", "document_id", "filename", "page_number", "chunk_index"]:
            print(f"  {k}: {payload.get(k)}")
        text = payload.get("chunk_text") or payload.get("text") or ""
        print(f"  text: {text[:100]}...")

if __name__ == "__main__":
    asyncio.run(inspect())

