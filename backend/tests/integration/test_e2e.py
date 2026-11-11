import io
import uuid
import pymupdf
import pytest
from fastapi.testclient import TestClient


def test_complete_e2e_flow(client: TestClient):
    # 1. Login demo user
    res_login = client.post(
        "/api/v1/auth/login",
        json={"email": "elena.vance@blackmesa.gov", "password": "enterprise-research-2026"},
    )
    assert res_login.status_code == 200, res_login.text
    token = res_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get profile
    res_me = client.get("/api/v1/auth/me", headers=headers)
    assert res_me.status_code == 200
    assert res_me.json()["email"] == "elena.vance@blackmesa.gov"

    # 3. Create notebook
    res_nb = client.post(
        "/api/v1/notebooks",
        json={
            "title": "Quantum Photonics Synthesis",
            "description": "Exploration of single-photon sources",
            "category": "Quantum Computing",
        },
        headers=headers,
    )
    assert res_nb.status_code == 201
    nb = res_nb.json()
    nb_id = nb["id"]

    # 4. Generate real PDF in-memory
    pdf_doc = pymupdf.open()
    page1 = pdf_doc.new_page()
    page1.insert_text((50, 50), "Single-photon emitters operate at cryogenic temperatures with 99.4 percent purity.")
    page2 = pdf_doc.new_page()
    page2.insert_text((50, 50), "Interferometric Hong-Ou-Mandel visibility exceeds 95 percent in topological waveguides.")
    pdf_bytes = pdf_doc.tobytes()
    pdf_doc.close()

    # 5. Upload PDF
    files = {"file": ("photonics_whitepaper.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    res_upload = client.post(
        f"/api/v1/notebooks/{nb_id}/documents",
        files=files,
        headers=headers,
    )
    assert res_upload.status_code == 201
    doc = res_upload.json()
    doc_id = doc["id"]

    # 6. Check document status
    res_status = client.get(f"/api/v1/documents/{doc_id}/status", headers=headers)
    assert res_status.status_code == 200

    # 7. Ask chat question grounded in the document
    res_chat = client.post(
        f"/api/v1/notebooks/{nb_id}/chat",
        json={"message": "What is the purity of single-photon emitters at cryogenic temperatures?"},
        headers=headers,
    )
    assert res_chat.status_code == 200
    chat_data = res_chat.json()
    assert chat_data["role"] == "assistant"
    assert len(chat_data["content"]) > 0

    # 8. Check conversation history
    res_history = client.get(f"/api/v1/notebooks/{nb_id}/chat/history", headers=headers)
    assert res_history.status_code == 200
    history = res_history.json()
    assert len(history) >= 2  # user message and assistant message

    # 9. Verify user statistics
    res_stats = client.get("/api/v1/users/me/stats", headers=headers)
    assert res_stats.status_code == 200
    stats = res_stats.json()
    assert stats["total_notebooks"] >= 1
    assert stats["total_documents"] >= 1

    # 10. Verify search
    res_search = client.get("/api/v1/search?q=photonics", headers=headers)
    assert res_search.status_code == 200
    results = res_search.json()
    assert len(results) >= 1

    # 11. Strict Isolation Check: New user cannot access this notebook
    res_u2 = client.post(
        "/api/v1/auth/register",
        json={"email": f"user_{uuid.uuid4().hex[:6]}@example.com", "password": "SecurePassword1!", "full_name": "Isolated User"},
    )
    token2 = res_u2.json()["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}"}

    # Attempt to access user 1's notebook
    res_iso_nb = client.get(f"/api/v1/notebooks/{nb_id}", headers=headers2)
    assert res_iso_nb.status_code in (403, 404)

    # Attempt to access user 1's document
    res_iso_doc = client.get(f"/api/v1/documents/{doc_id}", headers=headers2)
    assert res_iso_doc.status_code in (403, 404)

    # 12. Cleanup notebook to avoid test duplicate pollution
    client.delete(f"/api/v1/notebooks/{nb_id}", headers=headers)
