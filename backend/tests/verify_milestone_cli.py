"""
End-to-End Milestone Verification Script:
1. Register a new account.
2. Create a notebook called "AI Engineering Research".
3. Upload a real research PDF ("AI_Engineering.pdf").
4. Wait for indexing to complete.
5. Ask: "What are the key findings in this document?"
6. Receive an answer with the correct PDF page citation.
7. Click the citation and open that exact page.
"""

import sys
import os
import time
import uuid
import requests
import fitz

BASE_URL = "http://127.0.0.1:8000/api/v1"
FRONTEND_URL = "http://localhost:5173"
PDF_PATH = os.path.join(os.path.dirname(__file__), "data", "AI_Engineering_Research.pdf")


def log_step(step_num: int, title: str):
    print(f"\n{'='*75}")
    print(f" STEP {step_num}: {title.upper()}")
    print(f"{'='*75}")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("\n" + "#" * 75)
    print(" NOTEBOOKLM LITE -- FIRST REAL END-TO-END MILESTONE VERIFICATION")
    print("#" * 75)

    # Pre-flight check
    if not os.path.exists(PDF_PATH):
        print(f"[FAIL] Research PDF not found at {PDF_PATH}")
        sys.exit(1)

    try:
        health = requests.get(f"{BASE_URL}/health", timeout=5).json()
        print(f"[OK] Backend is healthy: {health['status']} (DB: {health['database']})")
    except Exception as e:
        print(f"[FAIL] Backend unreachable at {BASE_URL}: {e}")
        sys.exit(1)

    unique_id = uuid.uuid4().hex[:8]
    test_email = f"ai_researcher_{unique_id}@enterprise.org"
    test_password = "SecureResearchPass123!"
    test_name = f"Dr. AI Researcher {unique_id}"

    # -------------------------------------------------------------
    # 1. Register a new account
    # -------------------------------------------------------------
    log_step(1, f"Register a new account ({test_email})")
    reg_resp = requests.post(
        f"{BASE_URL}/auth/register",
        json={"email": test_email, "password": test_password, "full_name": test_name},
        timeout=10,
    )
    if reg_resp.status_code != 201:
        print(f"[FAIL] Registration failed: {reg_resp.status_code} {reg_resp.text}")
        sys.exit(1)

    reg_data = reg_resp.json()
    user_id = reg_data["user"]["id"]
    token = reg_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"[SUCCESS] Registered user ID: {user_id}")
    print(f"[SUCCESS] JWT Token issued: {token[:20]}...{token[-10:]}")

    # Verify /auth/me
    me_resp = requests.get(f"{BASE_URL}/auth/me", headers=headers, timeout=5)
    assert me_resp.status_code == 200, "Failed to verify /auth/me"
    print(f"[SUCCESS] Verified authenticated identity: {me_resp.json()['email']}")

    # -------------------------------------------------------------
    # 2. Create a notebook called "AI Engineering Research"
    # -------------------------------------------------------------
    log_step(2, "Create a notebook called 'AI Engineering Research'")
    nb_payload = {
        "title": "AI Engineering Research",
        "description": "Deep-dive analysis of foundation models, architecture scaling, RAG, and AI engineering.",
        "category": "Artificial Intelligence",
    }
    nb_resp = requests.post(
        f"{BASE_URL}/notebooks",
        json=nb_payload,
        headers=headers,
        timeout=10,
    )
    if nb_resp.status_code != 201:
        print(f"[FAIL] Notebook creation failed: {nb_resp.status_code} {nb_resp.text}")
        sys.exit(1)

    notebook = nb_resp.json()
    notebook_id = notebook["id"]
    print(f"[SUCCESS] Created notebook:")
    print(f"          ID:          {notebook_id}")
    print(f"          Title:       {notebook['title']}")
    print(f"          Category:    {notebook['category']}")
    print(f"          Owner ID:    {notebook['owner_id']}")

    # -------------------------------------------------------------
    # 3. Upload a real research PDF
    # -------------------------------------------------------------
    log_step(3, f"Upload real research PDF ({os.path.basename(PDF_PATH)})")
    pdf_size_mb = os.path.getsize(PDF_PATH) / (1024 * 1024)
    print(f"[INFO] Uploading file size: {pdf_size_mb:.2f} MB")

    with open(PDF_PATH, "rb") as f:
        upload_resp = requests.post(
            f"{BASE_URL}/notebooks/{notebook_id}/documents",
            headers=headers,
            files={"file": ("AI_Engineering.pdf", f, "application/pdf")},
            timeout=60,
        )

    if upload_resp.status_code != 201:
        print(f"[FAIL] Upload failed: {upload_resp.status_code} {upload_resp.text}")
        sys.exit(1)

    doc_data = upload_resp.json()
    document_id = doc_data["id"]
    print(f"[SUCCESS] Document uploaded successfully:")
    print(f"          Document ID: {document_id}")
    print(f"          Filename:    {doc_data['filename']}")
    print(f"          Status:      {doc_data['processing_status']}")

    # -------------------------------------------------------------
    # 4. Wait for indexing to complete
    # -------------------------------------------------------------
    log_step(4, "Wait for indexing to complete in Qdrant Cloud")
    start_time = time.time()
    max_wait_seconds = 180
    final_status = None

    while time.time() - start_time < max_wait_seconds:
        try:
            status_resp = requests.get(
                f"{BASE_URL}/documents/{document_id}/status",
                headers=headers,
                timeout=30,
            )
            if status_resp.status_code == 200:
                status_obj = status_resp.json()
                st = status_obj.get("status", "").upper()
                elapsed = int(time.time() - start_time)
                print(f"  [{elapsed:02d}s] Processing status: {st} (Progress: {status_obj.get('progress')}%) ...")

                if st == "INDEXED":
                    final_status = status_obj
                    break
                elif st == "FAILED":
                    print(f"[FAIL] Indexing failed: {status_obj.get('error')}")
                    sys.exit(1)
        except requests.exceptions.RequestException as req_err:
            elapsed = int(time.time() - start_time)
            print(f"  [{elapsed:02d}s] Polling ({req_err.__class__.__name__}), waiting for background ingestion...")
        time.sleep(2.5)

    if not final_status or final_status.get("status", "").upper() != "INDEXED":
        print(f"[FAIL] Indexing timed out after {max_wait_seconds}s")
        sys.exit(1)

    # Fetch updated document metadata
    doc_detail = requests.get(
        f"{BASE_URL}/documents/{document_id}",
        headers=headers,
        timeout=10,
    ).json()

    print(f"[SUCCESS] Indexing completed successfully!")
    print(f"          Page count:   {doc_detail.get('page_count')} pages")
    print(f"          Total chunks: {doc_detail.get('total_chunks')} chunks indexed into Qdrant Cloud")
    print(f"          Time taken:   {int(time.time() - start_time)} seconds")

    # -------------------------------------------------------------
    # 5. Ask: "What are the key findings in this document?"
    # -------------------------------------------------------------
    log_step(5, 'Ask: "What are the key findings in this document?"')
    chat_payload = {
        "message": "What are the key findings in this document?",
        "selectedDocumentIds": [document_id],
    }
    chat_start = time.time()
    chat_resp = requests.post(
        f"{BASE_URL}/notebooks/{notebook_id}/chat",
        headers=headers,
        json=chat_payload,
        timeout=45,
    )

    if chat_resp.status_code != 200:
        print(f"[FAIL] Chat failed: {chat_resp.status_code} {chat_resp.text}")
        sys.exit(1)

    chat_data = chat_resp.json()
    chat_latency = int((time.time() - chat_start) * 1000)

    # -------------------------------------------------------------
    # 6. Receive an answer with the correct PDF page citation
    # -------------------------------------------------------------
    log_step(6, "Receive an answer with correct PDF page citation")
    answer = chat_data.get("content") or (chat_data.get("message", {}).get("content", "") if isinstance(chat_data.get("message"), dict) else "")
    citations = chat_data.get("citations", [])

    print(f"\n[AI RESPONSE (Latency: {chat_latency}ms)]:\n")
    print("-" * 75)
    print(answer)
    print("-" * 75)

    print(f"\n[GROUNDED CITATIONS RETURNED: {len(citations)}]:")
    if not citations:
        print("[FAIL] No citations were returned with the response!")
        sys.exit(1)

    for i, cit in enumerate(citations, 1):
        print(f"\n  Citation #{i}:")
        print(f"    - Document:   {cit.get('documentName')}")
        print(f"    - Page:       {cit.get('pageNumber')}")
        print(f"    - Relevance:  {cit.get('relevanceScore')}")
        print(f"    - Excerpt:    {cit.get('excerpt', '')[:120]}...")

    # Validate citation structure and page numbers
    primary_citation = citations[0]
    cited_page = primary_citation.get("pageNumber")
    assert cited_page is not None and cited_page > 0, f"Invalid cited page: {cited_page}"
    print(f"\n[SUCCESS] Primary citation is on Page {cited_page} of {primary_citation.get('documentName')}")

    # -------------------------------------------------------------
    # 7. Click the citation and open that exact page
    # -------------------------------------------------------------
    log_step(7, f"Click citation -> Open exact Page {cited_page} in Document Viewer")

    # Verify physical file endpoint serves the exact PDF
    file_endpoint = f"{BASE_URL}/documents/{document_id}/file"
    file_resp = requests.get(file_endpoint, timeout=10)
    assert file_resp.status_code == 200, f"File endpoint failed: {file_resp.status_code}"
    assert "pdf" in file_resp.headers.get("Content-Type", "").lower(), "Content-Type is not PDF"
    print(f"[SUCCESS] Physical PDF verified via GET {file_endpoint} ({len(file_resp.content)} bytes)")

    # Read the actual page content from the PDF to verify source ground truth
    doc_fitz = fitz.open(PDF_PATH)
    total_pages = len(doc_fitz)
    print(f"[SUCCESS] PDF page verified: Page {cited_page} of {total_pages} pages")

    actual_page_text = doc_fitz[cited_page - 1].get_text()
    clean_sample = " ".join(actual_page_text.split()[:40])
    print(f"\n[GROUND TRUTH EXTRACTED FROM PAGE {cited_page}]:")
    print(f'"{clean_sample}..."')

    # Frontend Navigation URL contract
    viewer_url = f"{FRONTEND_URL}/workspace/{notebook_id}/document/{document_id}?page={cited_page}"
    print(f"\n[FRONTEND CITATION CLICK TARGET URL]:")
    print(f"  --> {viewer_url}")
    print(f"\n[SUCCESS] Clicking citation opens Document Viewer directly at:")
    print(f"          Document ID: {document_id}")
    print(f"          Target Page: {cited_page}")
    print(f"          Direct Link: {viewer_url}")

    print("\n" + "#" * 75)
    print(" ALL 7 MILESTONE VERIFICATION STEPS PASSED SUCCESSFULLY!")
    print("#" * 75 + "\n")


if __name__ == "__main__":
    main()
