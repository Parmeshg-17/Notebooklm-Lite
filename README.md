<div align="center">

# 🧠 NotebookLM Lite

### **Enterprise-Grade, Document-Grounded AI Research & Knowledge Intelligence Platform**

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI%200.115-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React 19](https://img.shields.io/badge/Frontend-React%2019%20%2B%20TypeScript-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![Google Gemini](https://img.shields.io/badge/LLM-Google%20Gemini%20Flash-4285F4?style=flat-square&logo=google&logoColor=white)](https://ai.google.dev)
[![Qdrant](https://img.shields.io/badge/Vector%20DB-Qdrant%20Vector%20Engine-DC382D?style=flat-square&logo=qdrant&logoColor=white)](https://qdrant.tech)
[![LangGraph](https://img.shields.io/badge/Agent-LangGraph%20Stateful%20Workflow-FF6F00?style=flat-square)](https://langchain-ai.github.io/langgraph)
[![Model Context Protocol](https://img.shields.io/badge/Tools-MCP%202.x%20Standard-4A154B?style=flat-square)](https://modelcontextprotocol.io)
[![Terraform](https://img.shields.io/badge/IaC-Terraform%201.10-844FBA?style=flat-square&logo=terraform&logoColor=white)](https://www.terraform.io)
[![AWS Production](https://img.shields.io/badge/Cloud-AWS%20ECS%20Fargate%20%2B%20CloudFront-232F3E?style=flat-square&logo=amazon-aws&logoColor=white)](https://aws.amazon.com)
[![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-2088FF?style=flat-square&logo=github-actions&logoColor=white)](https://github.com/Parmeshg-17/Notebooklm-Lite/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)

[**Live Production Application**](https://dizur7rpcdjgr.cloudfront.net) • [**Interactive API Docs (Swagger)**](https://dizur7rpcdjgr.cloudfront.net/docs) • [**Architecture Diagram**](#-system-architecture) • [**Quick Start**](#-quick-start) • [**Evaluation Benchmarks**](#-evaluation-benchmarks)

</div>

---

## 📖 Executive Summary

**NotebookLM Lite** is an enterprise-grade AI research assistant engineered for verifiable, document-grounded question answering, comparative synthesis, and literature analysis. Inspired by Google's NotebookLM, it replaces traditional "black box" RAG with an autonomous **LangGraph stateful agent** operating over standardized **Model Context Protocol (MCP 2.x)** tools and a strict **"NO SOURCE, NO SENTENCE"** citation verification algorithm.

Every statement produced by the engine is mapped to exact document page boundaries, similarity metrics, and textual evidence. The application is packaged with production **Terraform Infrastructure as Code (IaC)** deployed to **Amazon Web Services (AWS ap-southeast-2)** with automated zero-downtime **GitHub Actions CI/CD pipelines**.

---

## 🏛️ System Architecture

```mermaid
flowchart TD
    subgraph Client ["Client Layer (Desktop & Mobile Responsive)"]
        SPA["Vite + React 19 SPA\n(Tailwind CSS v4 & Zustand Stores)"]
        MobileDrawer["Slide-Over Mobile Navigation & Tab Switcher"]
        DocViewer["Interactive PDF Document Viewer\n(Page Navigation, Highlighting, Zoom)"]
        SPA --- MobileDrawer
        SPA --- DocViewer
    end

    subgraph CDN ["Edge & CDN Layer (AWS CloudFront Global Network)"]
        CF["CloudFront CDN Distribution\n(HTTPS, Compression, Edge Cache)"]
        OAC["Origin Access Control (OAC)"]
        S3Front[("Amazon S3 Static Bucket\n(Immutable Cached Assets)")]
        CF -->|Static Assets| OAC --> S3Front
    end

    subgraph Gateway ["Gateway & Load Balancer Layer"]
        ALB["Application Load Balancer (ALB)\n(Path Routing: /api/* to ECS)"]
        CF -->|/api/* Traffic| ALB
    end

    subgraph Compute ["Containerized Backend (AWS ECS Fargate)"]
        FastAPI["FastAPI 0.115 Async Engine\n(Python 3.12, Uvicorn, Middlewares)"]
        ALB --> FastAPI

        subgraph AgentEngine ["LangGraph Stateful Agent Workflow"]
            Router["1. Query Intent Classifier\n(6 Deterministic & LLM Intents)"]
            Planner["2. Query Planner & Tool Selector"]
            MCPExec["3. MCP 2.x Tool Executor"]
            Aggregator["4. Evidence Aggregator & Deduplicator"]
            Generator["5. Gemini Flash Synthesis\n(Document Grounding Prompt)"]
            Verifier["6. Citation Verifier\n(NO SOURCE, NO SENTENCE)"]
            Refusal["7. Refusal & Fallback Handler"]

            Router --> Planner --> MCPExec --> Aggregator
            Aggregator -->|Evidence Sufficient| Generator --> Verifier
            Aggregator -->|Insufficient Evidence| Refusal
            Verifier -->|Verified Grounding| Output["Final Verified RAG Response"]
            Verifier -->|Unverified Assertions Stripped| Output
            Verifier -->|Total Failure & Retries Left| Planner
        end

        FastAPI --> AgentEngine
    end

    subgraph MCPTools ["Model Context Protocol (MCP 2.x) Standard Tools"]
        T1["search_documents"]
        T2["get_document"]
        T3["get_page_content"]
        T4["search_citations"]
        T5["compare_sources"]
        T6["summarize_document"]
        T7["get_notebook_sources"]
        MCPExec --> MCPTools
    end

    subgraph DataStorage ["Data, Vector & Storage Layer"]
        RDS[("Amazon RDS PostgreSQL 16.9\n(Multi-Tenant Users, Notebooks, Sessions)")]
        Qdrant[("Qdrant Vector Engine\n(768-dim Gemini Embeddings, HNSW)")]
        S3Docs[("Amazon S3 Encrypted Storage\n(AES-256 PDF Document Vault)")]
        GeminiAPI["Google Gemini 2.5 Flash &\nEmbedding API (gemini-embedding-001)"]

        MCPTools --> Qdrant
        MCPTools --> RDS
        FastAPI --> S3Docs
        Generator --> GeminiAPI
    end
```

---

## ✨ Key Features & Capabilities

### 1. 🔍 Strict Grounding & Citation Verification
* **"NO SOURCE, NO SENTENCE" Policy:** Any sentence generated by the model lacking a verifiable primary source citation is automatically pruned or routed to the refusal handler.
* **Exact Page Boundary Tracking:** Citations pin down the exact source document ID, filename, page number, and similarity score.
* **Citation Inspector UI:** Interactive side panel allows users to click citations in real time to inspect excerpt highlights and jump directly to relevant pages in the built-in PDF viewer.

### 2. 🤖 LangGraph Stateful Agent & MCP 2.x Tools
* **Autonomous Intent Routing:** Dynamic query classification across 6 specialized question intents:
  1. `SIMPLE_QUESTION`: Direct factual lookups across active documents.
  2. `MULTI_DOCUMENT_QUESTION`: Complex queries requiring multi-source synthesis.
  3. `COMPARISON_QUESTION`: Structured comparative matrix generation between papers or reports.
  4. `DOCUMENT_SUMMARY`: Comprehensive executive summary generation.
  5. `PAGE_SPECIFIC_QUESTION`: Targeted deep-dive into specific document pages.
  6. `INSUFFICIENT_EVIDENCE`: Graceful refusal when documents lack sufficient information.
* **Standardized MCP 2.x Integration:** 7 discrete tools compliant with the open Model Context Protocol standard.
* **MemorySaver Checkpointing:** Full conversation state and tool traces persisted across turns.

### 3. 🎨 High-Fidelity Enterprise User Experience
* **3-Column Research Workspace:**
  * **Left Column:** Source panel with token budget counter, active source toggle checkboxes, and multi-file drag-and-drop uploader.
  * **Center Column:** Real-time conversational interface with streaming responses, formatted Markdown, LaTeX KaTeX formulas, and feedback controls.
  * **Right Column:** Citation Inspector with grounded relevance cards and intelligent follow-up suggestions.
* **Mobile-Responsive First-Class Layout:**
  * Slide-over navigation drawer with backdrop tap-to-dismiss on iOS/Android.
  * Top navigation bar with hamburger menu toggle.
  * Segmented mobile tab bar (`[Sources] | [Chat] | [Citations]`) enabling 100% full-width readability on small devices.
* **Export Hub:** One-click export to formatted **Markdown (.md)**, **BibTeX (.bib)** for academic publishing, or styled **PDF**.

### 4. 🛡️ Enterprise Security & Multi-Tenancy
* **Multi-Tenant Isolation:** Strict `owner_id` boundary enforcement across relational tables and Qdrant vector filters.
* **Sanitized Upload Pipeline:** Directory traversal protection (`../`), MIME-type validation, and user UUID isolation.
* **Bcrypt Password Security:** 12-round salted hashing; stateless JWT Bearer token authentication.
* **Infrastructure Security:** Private VPC subnets for RDS PostgreSQL, AWS Secrets Manager for encrypted credentials, and CloudFront Origin Access Control (OAC).

---

## 🧰 Technology Stack

| Domain | Technology | Description |
| :--- | :--- | :--- |
| **Frontend Framework** | **React 19 & TypeScript** | Component-driven SPA with strict typing |
| **Styling & Design** | **Tailwind CSS v4 & Lucide** | Modern design token system, dark/light themes |
| **State Management** | **Zustand** | Lightweight, reactive stores for auth, documents, and UI |
| **Backend Framework** | **FastAPI (Python 3.12)** | Asynchronous REST API with automatic OpenAPI generation |
| **ORM & Database** | **SQLAlchemy 2.0 & PostgreSQL 16** | Async connection pooling with Alembic migrations |
| **Vector Engine** | **Qdrant Vector DB** | 768-dimensional vector index with cosine similarity filters |
| **Embeddings & LLM** | **Google Gemini Flash 2.5** | High-speed inference and `gemini-embedding-001` embeddings |
| **Agent Framework** | **LangGraph & MCP 2.x** | Stateful multi-turn reasoning graph with tool execution |
| **PDF Ingestion** | **PyMuPDF (fitz)** | High-accuracy text extraction with page numbering metadata |
| **Infrastructure as Code** | **Terraform 1.10** | Declarative AWS cloud resource management |
| **Cloud Hosting** | **AWS ECS Fargate & CloudFront** | Serverless container orchestration and global edge CDN |
| **CI/CD Automation** | **GitHub Actions** | Automated linting, testing, Docker builds, and deployments |

---

## 📁 Repository Structure

```
NOTEBOOKLM-LITE/
├── .github/
│   └── workflows/
│       ├── deploy-backend.yml      # CI/CD: Docker ECR build & ECS Fargate deployment
│       └── deploy-frontend.yml     # CI/CD: React build, S3 sync & CloudFront invalidation
├── backend/
│   ├── app/
│   │   ├── agent/                  # LangGraph agent workflow & state machine
│   │   │   ├── graph.py            # Graph definition, nodes, and conditional edges
│   │   │   ├── router.py           # 6-intent query classification engine
│   │   │   ├── verifier.py         # Citation verification & sentence-stripping algorithm
│   │   │   └── state.py            # Agent state schemas and TypedDict models
│   │   ├── api/v1/                 # FastAPI REST route controllers
│   │   │   ├── auth.py             # Login, registration, JWT issuance
│   │   │   ├── notebooks.py        # Workspace CRUD & access controls
│   │   │   ├── documents.py        # File upload, parsing & download endpoints
│   │   │   ├── chat.py             # RAG conversational endpoint with agent dispatch
│   │   │   ├── search.py           # Global cross-document search
│   │   │   └── health.py           # Deep liveness & readiness probes
│   │   ├── core/                   # Security, settings, and logging configuration
│   │   ├── db/                     # SQLAlchemy async engine, models, and session maker
│   │   ├── ingestion/              # PDF extraction, semantic chunking & token counting
│   │   ├── mcp/                    # Model Context Protocol (MCP 2.x) tools server
│   │   └── services/               # Vector service, document store & chat service
│   ├── migrations/                 # Alembic database schema migration scripts
│   ├── tests/                      # Automated Pytest suite (67 unit & integration tests)
│   ├── Dockerfile                  # Production container definition for FastAPI
│   └── evaluate_phase4.py          # Automated RAG evaluation benchmark harness
├── infrastructure/
│   └── terraform/                  # Production AWS Infrastructure as Code (IaC)
│       ├── networking.tf           # VPC, Public/Private Subnets, NAT Gateways
│       ├── ecs.tf                  # ECS Cluster, Task Definition & Fargate Service
│       ├── rds.tf                  # Amazon RDS PostgreSQL 16.9 Database
│       ├── s3.tf                   # S3 Buckets for Frontend SPA & Document Vault
│       ├── cloudfront.tf           # Global CDN Distribution with OAC policies
│       ├── security_groups.tf      # Granular ingress/egress network firewall rules
│       ├── iam.tf                  # Least-privilege IAM Roles & Policies
│       └── outputs.tf              # Cloud resource endpoints & identifiers
├── notebooklm-lite/                # Frontend SPA (React 19 + TypeScript + Vite)
│   ├── src/
│   │   ├── components/
│   │   │   ├── layout/             # AppLayout, TopBar, and responsive Sidebar
│   │   │   ├── chat/               # ChatMessage, ChatInput, CitationCard
│   │   │   ├── documents/          # DocumentRow, UploadModal, PDFViewer
│   │   │   └── notebook/           # NotebookCard, CreateNotebookModal
│   │   ├── pages/                  # Dashboard, Workspace, Notebooks, Analytics
│   │   ├── services/               # Axios API client and data service layers
│   │   └── store/                  # Zustand global state slices
│   ├── Dockerfile                  # Multi-stage production Nginx container
│   └── vite.config.ts              # Vite bundling & build configuration
├── docker-compose.yml              # Local production-mirror stack orchestration
└── README.md                       # Master project documentation
```

---

## 🚀 Quick Start Guide

### Option A: Complete Docker Compose Stack (Recommended)

Run the complete full-stack environment (FastAPI Backend, React Frontend, PostgreSQL 16, and Qdrant Vector Engine) with a single command:

```bash
# 1. Clone repository
git clone https://github.com/Parmeshg-17/Notebooklm-Lite.git
cd Notebooklm-Lite

# 2. Configure environment variables
cp backend/.env.example backend/.env
# Open backend/.env and insert your Google Gemini API key:
# GEMINI_API_KEY=your_gemini_api_key_here

# 3. Launch all services
docker compose up --build
```

Access the application endpoints:
* **Frontend Web Application:** [http://localhost:5173](http://localhost:5173) or [http://localhost](http://localhost)
* **Backend API Documentation (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)
* **API Healthcheck Probe:** [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)
* **Qdrant Vector Engine Web UI:** [http://localhost:6333/dashboard](http://localhost:6333/dashboard)

---

### Option B: Local Development Setup

#### 1. Prerequisites
* **Python 3.12+**
* **Node.js 20+** & **npm**
* **Qdrant Vector Database** (Local binary or standalone Docker container: `docker run -p 6333:6333 qdrant/qdrant`)

#### 2. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv

# On Linux/macOS:
source .venv/bin/activate
# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start FastAPI server with live reload
uvicorn app.main:app --reload --port 8000
```

#### 3. Frontend Setup

```bash
cd notebooklm-lite

# Install Node modules
npm install

# Start Vite local development server
npm run dev
```

The application will be available at [http://localhost:5173](http://localhost:5173).

---

## 🔑 Demo Account Credentials

A pre-configured enterprise researcher account is automatically seeded into the database for immediate testing:

| Attribute | Value |
| :--- | :--- |
| **Email** | `elena.vance@blackmesa.gov` |
| **Password** | `Password123!` *(or `enterprise-research-2026`)* |
| **Display Name** | Dr. Elena Vance |
| **Role & Plan** | Lead Research Scientist (Enterprise Pro) |

---

## 🧪 Evaluation Benchmarks & Automated Tests

The engine includes a rigorous testing harness evaluating query classification accuracy, tool invocation precision, groundedness, and response latency.

### 1. Benchmark Results

```
================================================================================
                    RAG & AGENT EVALUATION BENCHMARK RESULTS                    
================================================================================
Metric                               Result       Target       Status
--------------------------------------------------------------------------------
Intent Routing Accuracy              100.0%       > 95.0%      [PASSED]
MCP Tool Selection Accuracy          100.0%       > 95.0%      [PASSED]
Citation Groundedness & Precision    100.0%       > 98.0%      [PASSED]
Hallucination Stripping Rate         100.0%       100.0%       [PASSED]
Median Response Latency (P50)        724.2 ms     < 1500 ms    [PASSED]
95th Percentile Latency (P95)        4879.3 ms    < 6000 ms    [PASSED]
Total Evaluation Test Cases          16 / 16      100.0%       [PASSED]
================================================================================
```

### 2. Running Automated Tests

```bash
# Execute full backend test suite (67 unit and integration tests)
cd backend
pytest tests/ -v

# Run targeted agent routing and verification suites
pytest tests/test_agent_routing.py \
       tests/test_mcp_tools.py \
       tests/test_citation_verification.py \
       tests/test_agent_workflow.py -v

# Run automated evaluation benchmark
python evaluate_phase4.py
```

### 3. Frontend Verification
```bash
cd notebooklm-lite

# Verify TypeScript compilation and production bundling
npm run build

# Run static linter
npx oxlint
```

---

## ☁️ AWS Cloud Architecture & Infrastructure as Code

The entire cloud infrastructure is defined using **Terraform** in [`infrastructure/terraform/`](file:///c:/Users/parmesh/Desktop/NOTEBOOKLM%20LITE/infrastructure/terraform):

```
infrastructure/terraform/
├── networking.tf           # VPC (10.0.0.0/16) across 2 AZs with Public/Private subnets
├── ecs.tf                  # ECS Fargate Cluster, Task Definition, & Target Groups
├── rds.tf                  # Amazon RDS PostgreSQL 16.9 (db.t4g.micro in private subnets)
├── s3.tf                   # S3 Frontend Bucket & S3 Document Vault with KMS Encryption
├── cloudfront.tf           # Global CloudFront CDN with TLS 1.3 and OAC
├── security_groups.tf      # Strict least-privilege ingress/egress firewalls
├── iam.tf                  # Execution & Task roles with KMS & Secrets Manager access
└── outputs.tf              # Exported endpoints (ALB, CloudFront, S3, RDS)
```

### Cloud Cost Optimization ($28 – $30 / month)
1. **Single-AZ NAT Gateway / Public IP Tasks:** Optimizes data transfer and network overhead.
2. **Amazon RDS `db.t4g.micro`:** Cost-efficient Graviton instance providing 2 vCPUs and 1GB RAM.
3. **ECS Fargate Provisioning:** 0.25 vCPU and 0.5 GB RAM container sizing with automatic task scaling.
4. **CloudFront Caching:** Static JavaScript, CSS, and media assets cached at edge locations with `max-age=31536000, immutable`, drastically reducing origin egress traffic.

### Provisioning Instructions

```bash
cd infrastructure/terraform

# Initialize Terraform providers
terraform init

# Plan infrastructure changes
terraform plan -out=tfplan

# Apply configuration to AWS
terraform apply tfplan
```

---

## 🔄 CI/CD Pipelines (GitHub Actions)

Continuous integration and continuous deployment are managed through two dedicated GitHub Actions workflows:

### 1. Backend Pipeline (`deploy-backend.yml`)
* **Trigger:** Pushes to `main` modifying `backend/**` or manual `workflow_dispatch`.
* **Actions:**
  1. Authenticates securely with AWS credentials from GitHub repository secrets.
  2. Builds and tags optimized Docker container image using multi-stage caching.
  3. Pushes image to Amazon Elastic Container Registry (ECR).
  4. Updates ECS Task Definition with new container digest.
  5. Performs zero-downtime rolling deployment to Amazon ECS Fargate.
  6. Automatically probes ALB `/api/v1/health` until HTTP 200 OK is verified.

### 2. Frontend Pipeline (`deploy-frontend.yml`)
* **Trigger:** Pushes to `main` modifying `notebooklm-lite/**` or manual `workflow_dispatch`.
* **Actions:**
  1. Sets up Node.js 20 environment with npm caching.
  2. Compiles production assets via `npm run build`.
  3. Syncs static bundle to Amazon S3 with immutable cache headers.
  4. Uploads `index.html` with `no-cache, must-revalidate` policy.
  5. Triggers global cache invalidation on CloudFront Distribution (`/*`).

---

## 🔒 Security & Data Governance

1. **Zero-Trust Multi-Tenant Isolation:** Database records and vector similarity filters mandate an exact match on `owner_id`. No cross-tenant data leakage is architecturally possible.
2. **Deterministic Citation Verification:** Ensures generative models cannot invent assertions, papers, or facts not present in indexed source materials.
3. **Encrypted at Rest & in Transit:** All network traffic enforced via HTTPS / TLS 1.3; S3 buckets encrypted with AES-256 / AWS KMS; database storage encrypted at rest.
4. **Secrets Governance:** Zero hardcoded credentials. Database credentials and API keys are dynamically retrieved from AWS Secrets Manager and environment variables.

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for complete details.

---

<div align="center">
  <b>Built for enterprise research intelligence with Google DeepMind & Antigravity principles.</b>
</div>
