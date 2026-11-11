import os
import sqlite3
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from langgraph.checkpoint.sqlite import SqliteSaver

from app.core.metrics import metrics_collector
from app.core.security import create_access_token
from app.main import app
from app.models.document import Document
from app.models.notebook import Notebook
from app.models.user import User


@pytest.fixture
def temp_checkpoint_db(tmp_path):
    db_file = tmp_path / "test_checkpoints.db"
    conn = sqlite3.connect(str(db_file), check_same_thread=False)
    saver = SqliteSaver(conn)
    saver.setup()
    yield saver
    conn.close()


def test_persistent_sqlite_checkpointing(temp_checkpoint_db, tmp_path):
    """Test that LangGraph checkpoints are durable and survive across connections."""
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id, "checkpoint_ns": ""}}

    # Write a checkpoint
    checkpoint_data = {
        "v": 1,
        "id": str(uuid.uuid4()),
        "ts": "2026-11-10T00:00:00Z",
        "channel_values": {"generated_answer": "Test grounded answer", "is_grounded": True},
        "channel_versions": {"generated_answer": 1},
        "versions_seen": {},
    }
    temp_checkpoint_db.put(config, checkpoint_data, {}, {})

    # Read back checkpoint from same saver
    retrieved = temp_checkpoint_db.get(config)
    assert retrieved is not None
    assert retrieved["channel_values"]["generated_answer"] == "Test grounded answer"

    # Reopen connection from disk to simulate process restart
    db_file = tmp_path / "test_checkpoints.db"
    conn2 = sqlite3.connect(str(db_file), check_same_thread=False)
    saver2 = SqliteSaver(conn2)
    retrieved2 = saver2.get(config)
    assert retrieved2 is not None
    assert retrieved2["channel_values"]["generated_answer"] == "Test grounded answer"
    conn2.close()


@pytest.mark.asyncio
async def test_health_check_endpoint():
    """Verify detailed multi-component health status."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ["healthy", "degraded"]
        assert "checks" in data
        assert "database" in data["checks"]
        assert "qdrant" in data["checks"]
        assert "llm" in data["checks"]


@pytest.mark.asyncio
async def test_metrics_endpoints():
    """Verify metrics in JSON and Prometheus formats."""
    metrics_collector.record_request(45.5, is_error=False)
    metrics_collector.record_request(120.0, is_error=False)
    metrics_collector.record_tokens(350)
    metrics_collector.record_ingestion()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # JSON format
        resp = await client.get("/api/v1/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert "requests_total" in data
        assert "latency_p50_ms" in data
        assert "latency_p95_ms" in data
        assert "total_tokens_consumed" in data
        assert data["requests_total"] >= 2

        # Prometheus text format
        prom_resp = await client.get("/api/v1/metrics", headers={"Accept": "text/plain"})
        assert prom_resp.status_code == 200
        text_out = prom_resp.text
        assert "http_requests_total" in text_out
        assert "http_latency_p50_ms" in text_out
        assert "rag_tokens_total" in text_out


@pytest.mark.asyncio
async def test_document_status_and_retry_flow():
    """Test document status polling and retry endpoint."""
    from app.db.session import async_session_factory
    from app.services.notebook_service import NotebookService
    from app.schemas.notebook import NotebookCreate

    user_id = uuid.uuid4()
    test_user = User(
        id=user_id,
        email=f"phase5_test_{user_id.hex[:6]}@example.com",
        hashed_password="fakehashedpassword",
        full_name="Phase 5 Tester",
    )

    async with async_session_factory() as db:
        db.add(test_user)
        await db.commit()
        await db.refresh(test_user)

        nb = Notebook(
            id=uuid.uuid4(),
            owner_id=test_user.id,
            title="Phase 5 Test Notebook",
            description="",
            category="General",
        )
        db.add(nb)
        await db.commit()
        await db.refresh(nb)

        # Create test document
        doc = Document(
            notebook_id=nb.id,
            owner_id=test_user.id,
            filename="retry_test.pdf",
            storage_path="/tmp/fake_test.pdf",
            file_type="application/pdf",
            file_size=1024,
            processing_status="FAILED",
            processing_error="Connection timed out",
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
        doc_id = doc.id

    token = create_access_token(str(test_user.id))
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Poll status
        status_resp = await client.get(f"/api/v1/documents/{doc_id}/status", headers=headers)
        assert status_resp.status_code == 200
        status_data = status_resp.json()
        assert status_data["status"] == "failed"
        assert status_data["error"] == "Connection timed out"

        # Retry
        retry_resp = await client.post(f"/api/v1/documents/{doc_id}/retry", headers=headers)
        assert retry_resp.status_code == 200
        retry_data = retry_resp.json()
        assert retry_data["status"] == "uploaded"
        assert retry_data["error"] is None
