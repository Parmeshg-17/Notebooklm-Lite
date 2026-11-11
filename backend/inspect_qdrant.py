import asyncio
import sys
sys.path.insert(0, "backend")

from app.rag.retrieval.qdrant_store import qdrant_store
from app.db.session import async_session_maker
from app.models.user import User
from app.models.notebook import Notebook
from app.models.document import Document
from sqlalchemy import select
import uuid

async def inspect():
    async with async_session_maker() as db:
        users = (await db.execute(select(User))).scalars().all()
        for u in users:
            print("USER:", u.id, u.email, u.full_name)
        
        nbs = (await db.execute(select(Notebook).where(Notebook.id == uuid.UUID("438c1105-030b-42ed-84ff-5fd4ea7284ba")))).scalars().all()
        for nb in nbs:
            print("NOTEBOOK:", nb.id, nb.title, "owner:", nb.owner_id)
            
        docs = (await db.execute(select(Document).where(Document.notebook_id == uuid.UUID("438c1105-030b-42ed-84ff-5fd4ea7284ba")))).scalars().all()
        for d in docs:
            print("DOC:", d.id, d.filename, d.processing_status, d.total_chunks, "owner:", d.owner_id)

    print("\nChecking Qdrant...")
    points = await qdrant_store.client.scroll(
        collection_name=qdrant_store.collection_name,
        limit=5,
        with_payload=True,
    )
    print("Qdrant total sampled points:", len(points[0]))
    for p in points[0]:
        print("POINT payload:", {k: p.payload.get(k) for k in ["document_id", "notebook_id", "user_id", "filename", "page_number"]})

if __name__ == "__main__":
    asyncio.run(inspect())

