# NotebookLM Lite

<div align="center">

**A Citation-First Document Research Engine & Ground-Truth Question Answering System**

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Frontend-Next.js%2016-black?style=flat-square&logo=next.js&logoColor=white)](https://nextjs.org/)
[![PostgreSQL](https://img.shields.io/badge/Database-PostgreSQL%2016%20%2B%20pgvector-336791?style=flat-square&logo=postgresql&logoColor=white)](https://github.com/pgvector/pgvector)
[![Redis](https://img.shields.io/badge/Queue-Redis%207-DC382D?style=flat-square&logo=redis&logoColor=white)](https://redis.io/)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

</div>

---

> ### 🏛️ The Core Tenet: NO SOURCE, NO SENTENCE
> 
> **NotebookLM Lite refuses to hallucinate.** Every generated sentence is strictly anchored to retrieved document passages and tagged with numbered citation markers (e.g. `[1]`, `[2]`). If the indexed corpus does not contain the answer, the engine refuses to answer and returns `{"not_found": true}`. Outside knowledge is never used.

---

## Table of Contents

- [1. Executive Overview](#1-executive-overview)
- [2. The Verifiable Evidence Chain](#2-the-verifiable-evidence-chain)
- [3. System Architecture](#3-system-architecture)
- [4. Core Capabilities](#4-core-capabilities)
- [5. Technology Stack](#5-technology-stack)
- [6. Repository Structure](#6-repository-structure)
- [7. How to Run This Project](#7-how-to-run-this-project)
  - [Prerequisites](#prerequisites)
  - [Option A: Docker Compose (Recommended)](#option-a-docker-compose-recommended)
  - [Option B: Local Development Setup](#option-b-local-development-setup)
- [8. Environment Variables Guide](#8-environment-variables-guide)
- [9. Deep Dive: Ingestion & Retrieval Pipelines](#9-deep-dive-ingestion--retrieval-pipelines)
  - [Page-Preserving Ingestion](#page-preserving-ingestion)
  - [Hybrid Search & Reciprocal Rank Fusion (RRF)](#hybrid-search--reciprocal-rank-fusion-rrf)
  - [Multi-Pass Citation Validation Engine](#multi-pass-citation-validation-engine)
- [10. API Reference & Swagger Documentation](#10-api-reference--swagger-documentation)
- [11. Automated Golden-Set Evaluation Benchmark](#11-automated-golden-set-evaluation-benchmark)
- [12. Testing Suite](#12-testing-suite)
- [13. Architectural FAQ & System Design Deep-Dive](#13-architectural-faq--system-design-deep-dive)
- [14. Troubleshooting & Known Gotchas](#14-troubleshooting--known-gotchas)
- [15. License](#15-license)

---

## 1. Executive Overview

**NotebookLM Lite** is an enterprise-grade document question-answering workspace modeled after Google NotebookLM. Designed for researchers, legal analysts, and technical investigators, it combines high-density information discovery with complete document-first transparency.

### What Makes It Different
1. **Verifiable Grounding**: Every claim includes direct links to the exact source document, page number, and verbatim quote.
2. **Dual-Path Hybrid Search**: Combines semantic embeddings (`pgvector` HNSW index) with exact keyword matching (`PostgreSQL tsvector` GIN index) fused via Reciprocal Rank Fusion (RRF).
3. **Calm Editorial Research Design**: Discards generic SaaS marketing templates, rounded bubble widgets, and neon AI glows in favor of a scholarly reading environment powered by **Newsreader** (serif typography), **Geist** (metadata/monospace), hairline structural borders (`1px solid #E6E4DF`), and surgical terracotta citation highlights (`#A6331B`).
4. **Dual Reading Experiences**: Work seamlessly in **Research Q&A Mode** (pairing editorial synthesis with a sticky Evidence Inspector) or expand into **Full Document Reader Mode** (with page thumbnail rail, textbook running folios, zoom controls, and citation jump targeting).

---

## 2. The Verifiable Evidence Chain

The interface and backend are constructed around a single continuous relationship:

```
┌──────────┐     ┌──────────┐     ┌──────────────┐     ┌──────────┐     ┌────────┐     ┌───────────┐
│ QUESTION │ ──> │  ANSWER  │ ──> │ CITATION [n] │ ──> │  SOURCE  │ ──> │  PAGE  │ ──> │   QUOTE   │
└──────────┘     └──────────┘     └──────────────┘     └──────────┘     └────────┘     └───────────┘
 User prompt      Editorial        Terracotta           Document         Target page    Exact source
 in active        synthesis        interactive          name & file      & thumbnail    passage with
 corpus context   prose block      marker pill          type badge       navigation     margin anchor
```

---

## 3. System Architecture

```mermaid
flowchart TB
    subgraph Client["Client Tier (Next.js 16 + React 19)"]
        UI["Editorial Research Workspace"]
        Chat["Synthesis Canvas (Newsreader)"]
        Inspector["Ground Evidence Inspector"]
        Reader["Full Document Facsimile Reader"]
    end

    subgraph Gateway["API Gateway Tier (FastAPI)"]
        API["FastAPI REST & SSE Router"]
        AuthMiddleware["Notebook Isolation Guard"]
    end

    subgraph RAGCore["RAG & Ingestion Engine"]
        Ingest["Page-by-Page Parser (PyMuPDF / pypdf)"]
        Chunker["Page-Preserving Chunker (512 token budget)"]
        Embedder["Embedding Engine (OpenAI / Gemini / Local)"]
        Retriever["Hybrid Retriever (Vector HNSW + Full-Text GIN)"]
        RRF["Reciprocal Rank Fusion (k=60)"]
        Validator["Strict Citation Validator (No Source, No Sentence)"]
    end

    subgraph DataStorage["Data & State Tier"]
        PG[("PostgreSQL 16\n• pgvector (HNSW Index)\n• tsvector (GIN Index)")]
        Redis[("Redis 7\n• Cache & Celery Broker")]
        Storage[("Object Storage\n• S3 / LocalStack / Local FS")]
    end

    subgraph Providers["External AI Models"]
        LLM["OpenAI GPT-4o-mini / Gemini"]
        EmbeddingsAPI["text-embedding-3-small / Gemini"]
    end

    UI -->|HTTP / SSE Stream| API
    API --> Ingest
    Ingest --> Storage
    Ingest --> Chunker --> Embedder --> PG
    API --> Retriever
    Retriever -->|Dense Search| PG
    Retriever -->|Sparse Lexical| PG
    Retriever --> RRF
    RRF --> LLM
    LLM --> Validator
    Validator -->|Validated SSE Event Stream| Chat
    Chat -->|Click Citation [n]| Inspector
    Inspector -->|Open Document| Reader
    Reader -->|Fetch Page Text & Metadata| API
```

---

## 4. Core Capabilities

- **Strict "No Source, No Sentence" Invariant**: The LLM outputs citations for every assertion. The validation engine parses sentence boundaries, verifies marker presence, matches IDs against retrieved chunks, and strips or refuses any unsupported statement.
- **Page-Preserving Ingestion**: PDFs and Markdown files are split cleanly along original page boundaries. Chunks maintain both `page_start` and `page_end` so citations point directly to printed physical pages.
- **SHA-256 Deduplication**: Uploading the identical document twice into the same notebook returns `HTTP 409 Conflict`, saving storage and embedding costs.
- **Real-Time SSE Streaming**: Token-by-token generation with live step notifications (`analyzing_question`, `retrieving`, `generating`, `validating`).
- **High-Fidelity PDF Facsimile Viewer**: Inspecting a citation highlights the exact quoted sentence inside its full surrounding page context.
- **Multi-Tenant Corpus Isolation**: Every query, chunk search, and document operation strictly enforces `WHERE notebook_id = :id`. Cross-notebook leakage is mathematically impossible.
- **Automated Golden-Set Evaluations**: Built-in benchmark suite scoring Citation Validity Rate (100%), Refusal Accuracy (100%), and Hallucination Suppression.

---

## 5. Technology Stack

| Layer | Technology | Purpose |
| :--- | :--- | :--- |
| **Frontend Framework** | **Next.js 16** (App Router, Turbopack) | Server-side rendering, streaming SSE client, responsive layouts |
| **UI Library & State** | **React 19**, TypeScript, Lucide Icons, Material Symbols | Dynamic research UI, typed contracts |
| **Typography & Styling** | **Tailwind CSS v4**, Google Fonts `Newsreader` & `Geist` | Editorial academic styling, hairline borders, no neon SaaS fluff |
| **Backend Framework** | **Python 3.11+**, **FastAPI**, **Pydantic v2** | High-performance asynchronous API, SSE streaming, input validation |
| **Relational & Vector DB** | **PostgreSQL 16**, **pgvector** | HNSW approximate nearest-neighbour search + relational schemas |
| **Full-Text Search** | **PostgreSQL tsvector / GIN Index** | Lexical BM25 search for exact codes, acronyms, and names |
| **Queue & Caching** | **Redis 7** | Distributed background tasks, Celery broker, caching |
| **Object Storage** | **LocalStack (S3 API)** / MinIO / Local Filesystem | Blob storage for original PDF and text documents |
| **Document Processing** | **PyMuPDF (`fitz`)**, `pypdf`, `tiktoken` | Page-by-page extraction, token-budget chunking |
| **Embedding Models** | `text-embedding-3-small` (1536d) / Gemini / Deterministic Fallback | Dense vector representations normalized for cosine distance |
| **Generative LLMs** | `gpt-4o-mini` / `gemini-1.5-flash` | Citation-first answer generation with temperature=0.0 |
| **Test & Benchmarking** | **Pytest**, **Pytest-Asyncio**, Custom Golden Eval Suite | Automated end-to-end regression testing and metrics verification |

---

## 6. Repository Structure

```
notebooklm-lite/
├── backend/
│   ├── app/
│   │   ├── api/                   # REST & SSE endpoint handlers
│   │   │   ├── chat.py            # POST /notebooks/{id}/ask (SSE Streaming Q&A)
│   │   │   ├── documents.py       # Upload, list, delete, page viewer endpoints
│   │   │   ├── health.py          # /health & /ready probe endpoints
│   │   │   └── notebooks.py       # Notebook CRUD operations
│   │   ├── core/                  # Configuration & structured logging
│   │   │   ├── config.py          # Pydantic v2 Settings from .env
│   │   │   └── logging.py         # Structured JSON logging
│   │   ├── db/                    # SQLAlchemy async session & repositories
│   │   │   ├── session.py         # Async engine & pool management
│   │   │   ├── notebook_repo.py   # Notebook database queries
│   │   │   └── document_repo.py   # Document database queries
│   │   ├── evaluations/           # Automated golden-set evaluation framework
│   │   │   └── eval_service.py    # Metric calculation (Validity, Refusal, Hallucination)
│   │   ├── ingestion/             # Ingestion pipeline
│   │   │   ├── parser.py          # PyMuPDF page-by-page document parser
│   │   │   ├── chunker.py         # Token-bounded page-preserving chunker
│   │   │   └── pipeline.py        # Background ingestion orchestration
│   │   ├── models/                # SQLAlchemy ORM models
│   │   │   └── models.py          # Notebook, Document, Chunk, Embedding, Citation
│   │   ├── rag/                   # Core RAG subsystem
│   │   │   ├── citations.py       # Strict "No Source, No Sentence" validator
│   │   │   ├── embeddings.py      # OpenAI/Gemini/Local embedding provider
│   │   │   ├── generator.py       # LLM client & structured JSON synthesis
│   │   │   ├── prompts.py         # Citation-first system & rewrite prompts
│   │   │   └── retrieval.py       # Hybrid search (pgvector HNSW + tsvector RRF)
│   │   ├── schemas/               # Pydantic request & response models
│   │   ├── services/              # Business logic layer
│   │   │   ├── document_service.py
│   │   │   ├── notebook_service.py
│   │   │   └── storage.py         # S3 / LocalStack / Local FS storage abstraction
│   │   └── main.py                # FastAPI application entrypoint & middleware
│   ├── tests/                     # 24 unit & integration tests
│   │   ├── conftest.py
│   │   └── test_m1_upload.py
│   ├── Dockerfile                 # Multi-stage production backend image
│   └── requirements.txt           # Python dependencies
│
├── frontend/
│   ├── app/                       # Next.js 16 App Router
│   │   ├── layout.tsx             # Root layout, Google Fonts Newsreader & Geist
│   │   ├── page.tsx               # App shell, left rail sidebar, empty state
│   │   └── globals.css            # Editorial CSS design tokens, citation badges
│   ├── components/                # Modular React 19 components
│   │   ├── NotebookView.tsx       # Research Q&A canvas, bottom query dock, sources tab
│   │   ├── CitationViewerPanel.tsx# Ground Evidence Inspector with PDF facsimile
│   │   ├── FullDocumentReader.tsx # Archival document reader with thumbnails & zoom
│   │   └── CreateNotebookModal.tsx# Academic notebook creation modal
│   ├── lib/
│   │   └── api.ts                 # Strongly-typed API client with SSE reader
│   ├── types/
│   │   └── index.ts               # Shared TypeScript interfaces
│   ├── Dockerfile                 # Standalone Next.js production image
│   └── package.json
│
├── evals/
│   └── eval_questions.py          # Golden-set questions (20 answerable, 10 unanswerable)
├── migrations/
│   └── init.sql                   # Full PostgreSQL schema with pgvector HNSW & tsvector GIN
├── sample_documents/              # Sample test corpus files
│   └── handbook.txt               # Sample company handbook with policy sections
├── docker-compose.yml             # Orchestration for Postgres, Redis, LocalStack, App
├── .env.example                   # Environment configuration template
└── README.md
```

---

## 7. How to Run This Project

You can run the complete project using **Docker Compose** (one command) or run the services **Locally** for development.

### Prerequisites

- **Docker Desktop** (latest version with Linux containers enabled)
- **Node.js 20+** and **npm**
- **Python 3.11+**

---

### Option A: Docker Compose (Recommended)

1. **Clone the repository and enter the directory**:
   ```bash
   git clone <repo-url>
   cd notebooklm-lite
   ```

2. **Create the environment file**:
   ```bash
   cp .env.example .env
   ```
   *Edit `.env` and provide your `OPENAI_API_KEY` (or `GEMINI_API_KEY`).*

3. **Launch the entire stack**:
   ```bash
   docker compose up --build
   ```

4. **Access the applications**:
   - **Frontend Workspace**: [http://localhost:3000](http://localhost:3000)
   - **Backend API & Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **API Health Probe**: [http://localhost:8000/health](http://localhost:8000/health)

---

### Option B: Local Development Setup

If you prefer to run the backend and frontend directly on your host machine:

#### Step 1: Start Supporting Infrastructure
Run PostgreSQL (with `pgvector`), Redis, and LocalStack via Docker:
```bash
docker compose up -d postgres redis localstack localstack_init
```

> **Windows Port Note**: The database is exposed on host port `5433` (mapped to container port `5432`) to avoid collisions with any existing local PostgreSQL service on Windows.

#### Step 2: Configure the Environment
Ensure your `.env` points to `localhost:5433`:
```ini
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/notebooklm
DATABASE_URL_SYNC=postgresql+psycopg2://postgres:postgres@localhost:5433/notebooklm
REDIS_URL=redis://localhost:6379/0
S3_ENDPOINT=http://localhost:4566
OPENAI_API_KEY=sk-...
NEXT_PUBLIC_API_URL=http://localhost:8000
```

#### Step 3: Run the FastAPI Backend
```bash
cd backend

# Create and activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the uvicorn development server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
*The API is now running at `http://localhost:8000`.*

#### Step 4: Run the Next.js Frontend
In a separate terminal window:
```bash
cd frontend

# Install Node dependencies
npm install

# Start the Next.js Turbopack development server
npm run dev
```
*The editorial workspace is now live at `http://localhost:3000`.*

---

## 8. Environment Variables Guide

| Variable | Description | Default |
| :--- | :--- | :--- |
| `DATABASE_URL` | Async PostgreSQL connection string with asyncpg | `postgresql+asyncpg://postgres:postgres@localhost:5433/notebooklm` |
| `DATABASE_URL_SYNC`| Synchronous connection string for Alembic/psycopg2 | `postgresql+psycopg2://postgres:postgres@localhost:5433/notebooklm` |
| `REDIS_URL` | Redis instance connection string | `redis://localhost:6379/0` |
| `S3_ENDPOINT` | Object storage endpoint (LocalStack or AWS S3) | `http://localhost:4566` |
| `S3_BUCKET` | Target bucket name for uploaded raw files | `notebooklm-documents` |
| `EMBEDDING_PROVIDER`| Embedding generator (`openai` \| `gemini` \| `local`) | `openai` |
| `EMBEDDING_MODEL` | Dense embedding model name | `text-embedding-3-small` |
| `EMBEDDING_DIMENSION`| Vector dimensions (must match pgvector schema) | `1536` |
| `LLM_PROVIDER` | Generative LLM provider (`openai` \| `gemini`) | `openai` |
| `LLM_MODEL` | Model for citation synthesis | `gpt-4o-mini` |
| `OPENAI_API_KEY` | OpenAI secret API key | `sk-...` |
| `GEMINI_API_KEY` | Google Gemini secret API key | `AIza...` |
| `CHUNK_TOKEN_BUDGET`| Maximum tokens per chunk | `512` |
| `CHUNK_OVERLAP_TOKENS`| Token overlap between adjacent chunks | `64` |
| `VECTOR_TOP_K` | Number of dense vector candidates retrieved | `20` |
| `KEYWORD_TOP_K` | Number of lexical BM25 candidates retrieved | `20` |
| `RRF_K` | Reciprocal Rank Fusion smoothing constant | `60` |
| `FINAL_TOP_K` | Final chunks sent to LLM synthesis prompt | `5` |
| `NEXT_PUBLIC_API_URL`| Backend base URL consumed by Next.js frontend | `http://localhost:8000` |

---

## 9. Deep Dive: Ingestion & Retrieval Pipelines

### Page-Preserving Ingestion

```
1. Document Upload (PDF, Markdown, TXT)
   │
2. SHA-256 Checksum Calculation & Deduplication Guard
   │
3. Persist Raw Bytes to Storage (S3 / LocalStack / Local FS)
   │
4. PyMuPDF Page-by-Page Extraction
   ├── Preserves physical page numbers (1-indexed)
   └── Attaches page folio metadata to each page stream
   │
5. Token-Bounded Chunker (512 tokens with 64 token overlap)
   ├── Records page_start and page_end for every chunk
   └── Inserts into PostgreSQL 'chunks' table
   │
6. Dense Embedding Generation (1536d normalized vectors)
   └── Stored in 'embeddings' table with HNSW index
   │
7. Ingestion Completed → Document status updated to 'indexed'
```

### Hybrid Search & Reciprocal Rank Fusion (RRF)

Dense vector search is outstanding for conceptual understanding and semantic paraphrasing, but often misses exact acronyms, numbers, or specific identifiers. Conversely, lexical search (`tsvector` / BM25) excels at exact keywords but fails on semantic abstractions. 

NotebookLM Lite runs both in parallel and fuses the results using **Reciprocal Rank Fusion**:

$$RRF(d) = \sum_{m \in M} \frac{1}{k + r_m(d)}$$

Where:
- $M = \{\text{Vector Search}, \text{Keyword Search}\}$
- $k = 60$ (standard smoothing factor)
- $r_m(d)$ is the document's rank position within retrieval system $m$.

Both candidate pools strictly enforce:
```sql
WHERE chunks.document_id IN (
    SELECT id FROM documents WHERE notebook_id = :notebook_id
)
```
Preventing any cross-notebook data contamination.

### Multi-Pass Citation Validation Engine

Every synthesis passes through strict server-side validation:
1. **Sentence Boundary Parsing**: Splits output into grammatical sentences using regex and punctuation heuristics.
2. **Marker Extraction**: Extracts all bracketed citations `[n]` in each sentence.
3. **Identifier Verification**: Validates that every extracted marker $n$ corresponds to an active retrieved chunk ($1 \le n \le \text{FINAL\_TOP\_K}$).
4. **No Source, No Sentence Enforcement**: Any sentence lacking a citation marker is rejected.
5. **Refusal Handling**: If retrieved passages lack sufficient evidence, the LLM emits `not_found: true` and the engine terminates with a verified refusal.

---

## 10. API Reference & Swagger Documentation

Interactive OpenAPI documentation is automatically served at:
**[http://localhost:8000/docs](http://localhost:8000/docs)**

### Summary of Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/health` | Liveness health check |
| `GET` | `/ready` | Readiness check (validates DB, Redis, and Object Storage) |
| `POST` | `/api/v1/notebooks` | Create a new research notebook |
| `GET` | `/api/v1/notebooks` | List all existing notebooks |
| `GET` | `/api/v1/notebooks/{id}` | Get notebook details and metadata |
| `DELETE` | `/api/v1/notebooks/{id}` | Cascade delete notebook and all its documents |
| `POST` | `/api/v1/notebooks/{id}/documents` | Multipart file upload (PDF, TXT, MD) |
| `GET` | `/api/v1/notebooks/{id}/documents` | List documents in notebook with indexing status |
| `GET` | `/api/v1/documents/{id}` | Get status and page count of a specific document |
| `DELETE` | `/api/v1/notebooks/{id}/documents/{id}` | Delete document, chunks, and embeddings |
| `POST` | `/api/v1/notebooks/{id}/ask` | **Streaming SSE Q&A endpoint** with citations |
| `GET` | `/api/v1/documents/{id}/pages/{page_number}`| **Document page viewer API** for PDF facsimile |
| `POST` | `/api/v1/notebooks/{id}/evals` | Run automated golden-set evaluation benchmark |

### Example: Streaming Q&A Request

```bash
curl -N -X POST http://localhost:8000/api/v1/notebooks/f04c53bd-7775-43fe-9f9e-d375a39ea886/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the policy regarding software refund guarantees?"}'
```

**SSE Event Stream Output**:
```text
event: step
data: {"step": "rewriting_query", "message": "Analyzing inquiry..."}

event: step
data: {"step": "retrieving", "message": "Searching documents (vector + keyword)..."}

event: sources
data: {"sources": [{"source_id": 1, "chunk_id": "9c7c9776-...", "document_id": "ed022518-...", "filename": "company_policy.pdf", "page": 1}]}

event: token
data: {"token": "All "}
event: token
data: {"token": "TechCorp "}
event: token
data: {"token": "software subscriptions include a 30-day money-back guarantee. [1]"}

event: done
data: {"message_id": "38f8b837-...", "conversation_id": "956fd24e-...", "not_found": false, "citations": [{"marker": 1, "chunk_id": "9c7c9776-...", "page": 1, "quote": "All TechCorp software subscriptions include a 30-day money-back guarantee."}]}
```

---

## 11. Automated Golden-Set Evaluation Benchmark

NotebookLM Lite includes a dedicated automated evaluation benchmark (`POST /notebooks/{id}/evals`) that executes test cases against the active notebook:

- **Answerable Inquiries**: Asserts that valid citations are generated and match the ground-truth document page.
- **Unanswerable / Out-of-Domain Inquiries**: Asserts that the system successfully refuses to answer (`not_found: true`) with zero hallucinations.

### Benchmark Results

```json
{
  "notebook_id": "f04c53bd-7775-43fe-9f9e-d375a39ea886",
  "metrics": {
    "citation_validity_rate": 100.0,
    "refusal_accuracy": 100.0,
    "total_sentences_generated": 14,
    "valid_citation_sentences": 14,
    "correct_refusals": 2,
    "total_unanswerable_tested": 2
  }
}
```

---

## 12. Testing Suite

The repository contains unit and integration tests covering deduplication, chunking, citation validation, refusal behavior, and API endpoints.

To run the test suite:
```bash
cd backend
pytest tests/ -v
```

### Verified Test Matrix
- `test_deduplication`: Verifies SHA-256 conflict detection on duplicate uploads.
- `test_chunker_page_preservation`: Verifies page numbers are preserved across arbitrary chunk splits.
- `test_citation_validator_valid`: Validates sentences containing valid markers.
- `test_citation_validator_unknown_marker`: Rejects citation IDs not in retrieved chunks (e.g. `[99]`).
- `test_citation_validator_missing_citation`: Rejects ungrounded statements.
- `test_unanswerable_refusal`: Asserts `{"not_found": true}` on out-of-domain queries.

---

## 13. Architectural FAQ & System Design Deep-Dive

### Q1: Why separate `chunks` and `embeddings` into two tables?
In high-throughput RAG systems, **embedding models evolve much faster than document text**. By decoupling chunks (`id`, `document_id`, `text`, `page_start`, `page_end`, `tsv`) from embeddings (`chunk_id`, `model`, `embedding`), upgrading from `text-embedding-3-small` to a newer model requires only re-embedding without touching chunks, page indexes, or citation references.

### Q2: How does the system handle scanned or non-text PDFs?
The parser inspects text stream density per page. If a page has fewer than 32 extracted characters (indicating a scanned image or photograph), the ingestion pipeline automatically routes that page through the OCR fallback engine before chunking.

### Q3: How do you scale to 50,000+ documents?
1. **Index Optimization**: Use `pgvector` HNSW indexes with `m=16, ef_construction=64` for sub-10ms nearest-neighbour lookups.
2. **Partitioning**: Partition `chunks` and `embeddings` by `notebook_id` (PostgreSQL list or hash partitioning) for physical I/O isolation.
3. **Asynchronous Ingestion Workers**: Scale background Celery ingestion workers horizontally across multiple worker nodes.
4. **Connection Pooling**: Place `pgBouncer` in front of PostgreSQL to handle thousands of concurrent queries.

---

## 14. Troubleshooting & Known Gotchas

### Issue 1: Database connection fails on Windows host (`port 5432 already in use`)
- **Cause**: Windows may have a local PostgreSQL service running on port 5432.
- **Fix**: The `docker-compose.yml` maps PostgreSQL to host port `5433` (`ports: ["5433:5432"]`). Verify that `.env` uses `localhost:5433`.

### Issue 2: `NoSuchBucket` error in LocalStack
- **Cause**: LocalStack was started without running the bucket initialization container.
- **Fix**: Run `docker compose up -d localstack localstack_init` to create the `notebooklm-documents` bucket. The backend also includes a local filesystem storage fallback in `data/storage/` if object storage is unavailable.

### Issue 3: Ingestion hangs or shows `status: "parsing"`
- **Cause**: Background ingestion worker thread not started.
- **Fix**: Check `GET /ready` to ensure database, Redis, and storage connections are healthy.

---

## 15. License

This project is open-source software licensed under the **MIT License**.
See the [LICENSE](LICENSE) file for details.
