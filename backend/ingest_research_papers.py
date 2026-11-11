import asyncio
import os
import shutil
import sys
import uuid
from pathlib import Path

sys.path.insert(0, "backend")

from app.core.config import settings
from app.db.session import async_session_factory
from app.models.document import Document
from app.rag.ingestion.ingestion_pipeline import ingestion_pipeline

USER_ID = uuid.UUID("c5ee3cf6-441c-4d30-87a7-24954a0397a8")  # Dr. Elena Vance
NOTEBOOK_ID = uuid.UUID("438c1105-030b-42ed-84ff-5fd4ea7284ba")  # AI Engineering Research

PAPERS = [
    {
        "source": r"C:\Users\parmesh\.gemini\antigravity\brain\9b417798-ef38-417e-99c2-fd41d83db872\.user_uploaded\media_1794299267193_2784ec02.pdf",
        "filename": "Artificial-Intelligence-in-Engineering.pdf",
    },
    {
        "source": r"C:\Users\parmesh\.gemini\antigravity\brain\9b417798-ef38-417e-99c2-fd41d83db872\.user_uploaded\media_1794299283589_8432eab2.pdf",
        "filename": "Engineering-AI-Systems-A-Research-Agenda.pdf",
    },
    {
        "source": r"C:\Users\parmesh\.gemini\antigravity\brain\9b417798-ef38-417e-99c2-fd41d83db872\.user_uploaded\media_1794299294711_457c593c.pdf",
        "filename": "Retrieval-Augmented-Generation-Survey.pdf",
    },
]

async def ingest_papers():
    user_upload_dir = Path("backend") / "uploads" / str(USER_ID)
    user_upload_dir.mkdir(parents=True, exist_ok=True)

    for paper in PAPERS:
        src = paper["source"]
        fname = paper["filename"]
        if not os.path.exists(src):
            print(f"File not found: {src}")
            continue

        size = os.path.getsize(src)
        unique_prefix = uuid.uuid4().hex[:12]
        dest_filename = f"{unique_prefix}_{fname}"
        dest_path = user_upload_dir / dest_filename
        shutil.copyfile(src, dest_path)
        print(f"Copied {fname} to {dest_path} ({size} bytes)")

        # Create Document in DB
        async with async_session_factory() as db:
            doc = Document(
                notebook_id=NOTEBOOK_ID,
                owner_id=USER_ID,
                filename=fname,
                storage_path=str(dest_path),
                file_type="application/pdf",
                file_size=size,
                page_count=0,
                total_chunks=0,
                processing_status="UPLOADED",
            )
            db.add(doc)
            await db.commit()
            await db.refresh(doc)
            doc_id = doc.id
            print(f"Created Document record: id={doc_id}, filename={fname}")

        # Run ingestion pipeline
        print(f"Starting ingestion pipeline for {fname}...")
        await ingestion_pipeline.process_document(doc_id)
        print(f"Finished ingestion pipeline for {fname}!\n")

if __name__ == "__main__":
    asyncio.run(ingest_papers())

