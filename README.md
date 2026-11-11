# NotebookLM Lite — Complete Full-Stack Implementation

An enterprise-grade, document-grounded AI knowledge management and research platform built with a high-fidelity React + TypeScript frontend and a FastAPI + SQLAlchemy 2.0 + Qdrant + Google Gemini backend.

---

## 🏛️ System Architecture

```mermaid
flowchart TD
    subgraph Frontend ["Frontend (Vite + React 19 + TypeScript)"]
        UI["Tailwind CSS v4 & Lucide UI"]
        Store["Zustand State & Auth Store"]
        APIClient["Typed API Client & Token Interceptor"]
        UI --> Store
        Store --> APIClient
    end

    subgraph LangGraphAgent ["Phase 4: LangGraph Stateful Agent Workflow"]
        Analyzer["Question Analyzer / Intent Router"]
        Planner["Query Planner & Tool Selector"]
        Executor["MCP Tool Executor"]
        EvidenceAgg["Evidence Collector (Deduplication & Grouping)"]
        Synthesizer["Gemini Generator (Strict Grounding)"]
        Verifier["Citation Verifier (NO SOURCE, NO SENTENCE)"]
        RefusalHandler["Refusal Handler (Insufficient Evidence)"]
        Checkpointer[("MemorySaver Checkpointer")]

        Analyzer -->|6 Question Intents| Planner
        Planner --> Executor
        Executor --> EvidenceAgg
        EvidenceAgg -->|Sufficient| Synthesizer
        EvidenceAgg -->|Insufficient / Off-Topic| RefusalHandler
        Synthesizer --> Verifier
        Verifier -->|Verified / Partial| OutputNode[Final RAG Response]
        Verifier -->|Failed & Retries Left| Planner
        Verifier -->|Failed & Max Retries| RefusalHandler
    end

    subgraph MCPServer ["Model Context Protocol (MCP 2.x) Server"]
        T1["search_documents"]
        T2["get_document"]
        T3["get_page_content"]
        T4["search_citations"]
        T5["compare_sources"]
        T6["summarize_document"]
        T7["get_notebook_sources"]
        Executor -->|Call Tool| MCPServer
    end

    subgraph Storage ["Data & Storage Layer"]
        DB[("PostgreSQL / Async SQLite")]
        Qdrant[("Qdrant Vector DB (768-dim)")]
        Disk[("Uploads Directory (PDF storage)")]
        Gemini["Google Gemini API (Flash 2.5)"]
    end

    APIClient -->|POST /notebooks/{id}/chat| Analyzer
    MCPServer --> Qdrant
    MCPServer --> DB
    Synthesizer --> Gemini
```

---

## 🚀 Quick Start

### 1. Prerequisites
- **Python 3.12+**
- **Node.js 18+** & npm
- *(Optional for Containerized Mode)* **Docker & Docker Compose**

---

### 2. Backend Setup (Local)

```powershell
cd backend

# Activate the pre-configured virtual environment
.\.venv\Scripts\Activate.ps1

# (Optional: install/verify dependencies)
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start the FastAPI server
uvicorn app.main:app --reload --port 8000
```
- API Documentation (Swagger): [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Check: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

---

### 3. Frontend Setup (Local)

```powershell
cd notebooklm-lite

# Install dependencies (already prepared)
npm install

# Start the Vite development server
npm run dev
```
- Application UI: [http://localhost:5173](http://localhost:5173)

---

### 4. Running with Docker Compose (Production Stack)

To run the complete production stack (FastAPI Backend + PostgreSQL 16 + Qdrant Vector Engine):

```bash
docker compose up --build
```

---

## 🔑 Demo Account Credentials

A pre-configured enterprise demo account is seeded automatically upon first login:

- **Email:** `elena.vance@blackmesa.gov`
- **Password:** `enterprise-research-2026`
- **Role:** Lead Research Scientist

---

## 🧪 Automated Testing & Evaluation Benchmarks

### Backend Test Suites (31 Phase 4 Tests + 36 Unit/Integration Tests):
```powershell
$env:PYTHONPATH="backend"
backend\.venv\Scripts\pytest.exe backend\tests\test_agent_routing.py backend\tests\test_mcp_tools.py backend\tests\test_citation_verification.py backend\tests\test_agent_workflow.py -v
```
Test coverage includes:
- **`test_agent_routing.py` (7 tests):** Evaluates heuristic and LLM query classification across all 6 intents (`SIMPLE_QUESTION`, `MULTI_DOCUMENT_QUESTION`, `COMPARISON_QUESTION`, `DOCUMENT_SUMMARY`, `PAGE_SPECIFIC_QUESTION`, `INSUFFICIENT_EVIDENCE`).
- **`test_mcp_tools.py` (8 tests):** Validates all 7 standardized MCP tools, MCPClient execution, and multi-tenant unauthorized rejection.
- **`test_citation_verification.py` (4 tests):** Validates strict factual grounding, hallucination stripping, page boundary enforcement, and refusal validity.
- **`test_agent_workflow.py` (12 tests):** Covers all 12 key scenarios from single-doc to multi-source comparisons, recovery loops, and MemorySaver checkpointing.

### Phase 4 Evaluation Benchmark:
```powershell
$env:PYTHONPATH="backend"
backend\.venv\Scripts\python.exe backend\evaluate_phase4.py
```
**Results:**
- **Intent Routing Accuracy:** **100.0%** (16/16)
- **MCP Tool Selection Accuracy:** **100.0%** (16/16)
- **Groundedness & Precision:** **100.0%** (16/16)
- **P50 Latency:** **724.2ms**
- **P95 Latency:** **4879.3ms**
- Exported Reports: [`backend/evaluation_phase4.json`](file:///C:/Users/parmesh/Desktop/NOTEBOOKLM%20LITE/backend/evaluation_phase4.json) & [`backend/evaluation_phase4.csv`](file:///C:/Users/parmesh/Desktop/NOTEBOOKLM%20LITE/backend/evaluation_phase4.csv)

### Frontend Build & Lint Verification:
```powershell
cd notebooklm-lite
npm run build     # 0 TypeScript / bundling errors
npx oxlint        # 0 warnings, 0 errors across 38 files
```

---

## 🔒 Security & Data Isolation Guarantees

1. **Strict Multi-Tenant Isolation:** Every database query and vector similarity filter strictly requires matching `owner_id`. A user cannot read, search, modify, or delete another user's notebook, document, or conversation.
2. **Safe File Handling:** Uploaded files undergo filename sanitization (directory traversal protection `../`), path isolation by user UUID, and size limits (50MB).
3. **Password Security:** Salted Bcrypt hashing with 12 rounds. Plaintext passwords are never logged or stored.
4. **Verifiable Citations:** AI chat responses map directly to verified document IDs, filenames, page numbers, and exact text excerpts.

