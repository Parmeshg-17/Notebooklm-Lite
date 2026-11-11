# NOTEBOOKLM LITE — PHASE 6 IMPLEMENTATION REPORT
## AWS Deployment, Security Hardening, Scalability & CI/CD

> **Role**: Senior AWS Cloud Architect, DevSecOps Engineer, Site Reliability Engineer, and Backend Infrastructure Engineer  
> **Target Region**: `ap-south-1` (Mumbai)  
> **Core Principle**: **NO SOURCE, NO SENTENCE.**  
> **Status**: Ready for Provisioning Review (AWS Live Deployment: `NOT TESTED` awaiting explicit user provisioning approval)

---

## A. Executive Summary

Phase 6 hardens the **NotebookLM Lite** platform for enterprise-grade AWS cloud deployment, transitioning the system from a single-machine development container into a horizontally scalable, observable, and defense-in-depth architecture.

Key achievements in this phase include:
1. **Security Hardening**: Implemented strict HTTP security headers (HSTS, CSP, X-Frame-Options: DENY, X-Content-Type-Options: nosniff), sliding-window rate limiting per IP/JWT, multi-tenant IDOR protection, magic-byte PDF verification (`%PDF-`), and prompt injection isolation boundaries in the LangGraph agent prompt.
2. **PostgreSQL Shared State Migration**: Configured production connection pooling (`asyncpg`, `pool_size=10`, `max_overflow=20`, `pool_recycle=1800`) and integrated official dual-mode PostgreSQL/SQLite LangGraph checkpointing via `langgraph-checkpoint-postgres` and `psycopg_pool.ConnectionPool`.
3. **Private S3 Document Storage**: Replaced container-local storage with Amazon S3 SSE-S3 (`AES256`) encryption, presigned PUT/GET workflows with strict TTLs, and automated PyMuPDF temporary file lifecycle management.
4. **ECS Fargate Container Hardening**: Refactored `backend/Dockerfile` to execute as a non-root user (`appuser` UID 10001), configured graceful SIGTERM termination (`timeout-graceful-shutdown=30`), and container health probes on `/api/v1/health`.
5. **Frontend S3 + CloudFront Delivery**: Optimized React/Vite SPA for CloudFront CDN distribution with Origin Access Control (OAC), client-side SPA fallback routing (`/index.html`), and path-pattern routing (`/api/*` to ALB).
6. **Zero-Key CI/CD via GitHub Actions**: Created automated workflows (`ci.yml`, `deploy-backend.yml`, `deploy-frontend.yml`) utilizing AWS IAM OpenID Connect (OIDC) federation, eliminating static AWS access keys.
7. **Infrastructure as Code (Terraform)**: Created modular, production-grade Terraform specifications in `infrastructure/terraform/` covering VPC, subnets across multiple AZs, Security Groups, IAM roles, RDS PostgreSQL 16, ECS Fargate, ALB, CloudFront, S3, and CloudWatch alarms.
8. **Scalability & Reliability**: Added bounded ingestion concurrency (`asyncio.Semaphore(5)`), exponential backoff with jitter on Gemini API calls, and automated horizontal autoscaling policies (70% CPU / 80% Memory).

---

## B. Existing Architecture Assessment

| Component | Phase 5 Status | Phase 6 Enhancement |
| :--- | :--- | :--- |
| **State Persistence** | SQLite checkpointer (`checkpoints.db`) | Dual-mode PostgreSQL (`langgraph-checkpoint-postgres` + `psycopg_pool`) for multi-task ECS tasks, preserving SQLite for local dev |
| **PDF Storage** | Container filesystem (`uploads/`) | Amazon S3 private bucket with SSE-S3 AES256, presigned PUT/GET URLs, and multi-tenant path prefixes |
| **Authentication** | Demo user fallback | Hardened `get_current_user`: rejects missing/expired tokens in production (`ALLOW_DEMO_FALLBACK=false`) |
| **Container User** | Root user in container | Dedicated unprivileged user (`appuser` UID 10001) |
| **Rate Limiting** | None | Sliding-window memory limiter (20/min auth, 45/min chat, 25/min upload) |
| **Security Headers** | Basic CORS | HSTS, CSP, X-Frame-Options: DENY, X-Content-Type-Options: nosniff, Server header stripping |
| **Vector DB** | Qdrant Cloud (`us-west-1`) | Preserved existing collection; zero unnecessary migration or re-embedding |
| **CI/CD** | Manual test execution | GitHub Actions CI + OIDC automated deployment to ECR, ECS, S3, and CloudFront |
| **IaC** | Docker Compose only | Full Terraform infrastructure suite in `infrastructure/terraform/` |

---

## C. Final AWS Architecture Diagram

```
                              Internet Users
                                     │
                                     ▼ HTTPS (443)
                 ┌───────────────────────────────────────┐
                 │        Amazon CloudFront (CDN)        │
                 │      (Origin Access Control - OAC)    │
                 └───────────┬───────────────┬───────────┘
                             │               │
        Static SPA Assets    │               │  /api/* (Dynamic API)
        (/*)                 ▼               ▼
                 ┌───────────────────┐   ┌───────────────────────────┐
                 │  Amazon S3 Bucket │   │ Application Load Balancer │
                 │ (Frontend Build)  │   │     (Public Subnets)      │
                 └───────────────────┘   └─────────────┬─────────────┘
                                                       │ Port 8000
                                                       ▼
                                         ┌───────────────────────────┐
                                         │     AWS Fargate (ECS)     │
                                         │     (Private Subnets)     │
                                         │  ┌─────────────────────┐  │
                                         │  │  FastAPI Backend    │  │
                                         │  │  (Non-root UID 10001│  │
                                         │  │  LangGraph + MCP)   │  │
                                         │  └──────────┬──────────┘  │
                                         └─────────────┼─────────────┘
                        ┌──────────────────────────────┼──────────────────────────────┐
                        ▼                              ▼                              ▼
             ┌─────────────────────┐        ┌─────────────────────┐        ┌─────────────────────┐
             │ Amazon RDS Postgres │        │  Amazon S3 Bucket   │        │    Qdrant Cloud     │
             │   (v16, Private)    │        │  (Private Documents)│        │    (Vector DB)      │
             │  • App Data         │        │  • AES256 SSE       │        │  • 768-dim Vectors  │
             │  • LangGraph State  │        │  • Presigned URLs   │        │  • Dense + Sparse   │
             │  • Connection Pool  │        │  • Temp Cleanup     │        │  • Zero-Re-embed    │
             └─────────────────────┘        └─────────────────────┘        └─────────────────────┘
```

---

## D. Security Changes & Hardening

### 1. Security Headers (`app.middleware.security_headers`)
Registered `SecurityHeadersMiddleware` enforcing:
- `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`
- `X-Frame-Options: DENY` (clickjacking defense)
- `X-Content-Type-Options: nosniff` (MIME sniffing defense)
- `Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';`
- `X-XSS-Protection: 1; mode=block`
- Stripping of revealing `Server` and `X-Powered-By` headers.

### 2. Sliding-Window Rate Limiting (`app.middleware.rate_limit`)
Enforces differentiated endpoint rate limits per client IP / JWT subject:
- **Authentication (`/login`, `/register`)**: 20 requests/minute
- **Chat & Generation (`/chat`)**: 45 requests/minute
- **Document Uploads (`/documents`)**: 25 requests/minute
- **General APIs**: 200 requests/minute
- Rejections emit HTTP 429 with `Retry-After` and `X-RateLimit-*` headers.

### 3. File Security & Magic-Byte Validation
- Enforces `%PDF-` magic-byte signature check in `StorageService.validate_pdf_bytes`.
- Strips path traversal sequences (`../`, `..\\`) using regex sanitization.
- Restricts files to 500 pages maximum (`MAX_FILE_PAGE_LIMIT = 500`).

### 4. Prompt Injection Defense
Updated `SYSTEM_AGENT_PROMPT` in `app/agents/prompts.py` to enforce strict boundary encapsulation:
- Instructs Gemini that text between `<DOCUMENT_EXCERPT>` tags is untrusted static data.
- Forbids executing embedded commands or altering core instructions.

---

## E. Database and S3 Migration

### 1. PostgreSQL Connection Pooling (`app.db.session`)
Configured production pooling parameters for `asyncpg`:
```python
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,         # Default: 10 connections
    max_overflow=settings.DB_MAX_OVERFLOW,   # Default: 20 overflow connections
    pool_timeout=settings.DB_POOL_TIMEOUT,   # Default: 30 seconds
    pool_recycle=settings.DB_POOL_RECYCLE,   # Default: 1800s (prevents stale RDS drops)
    pool_pre_ping=True,                      # Active health validation
)
```

### 2. Shared LangGraph State Checkpointing (`app.agents.graph`)
When running on ECS with `DATABASE_URL` configured for RDS PostgreSQL, `build_agent_graph()` initializes `langgraph.checkpoint.postgres.PostgresSaver` backed by `psycopg_pool.ConnectionPool`. In local environments, it falls back seamlessly to `AsyncCompatibleSqliteSaver`.

### 3. S3 Document Management Lifecycle
```
User Upload Request -> Presigned S3 PUT URL (TTL 900s) -> Frontend Direct S3 Upload
                                                                  │
PostgreSQL Status: INDEXED <- Embedding & Qdrant Upsert <- Background Ingestion Task
```
PyMuPDF requires seekable byte-streams. `StorageService.resolve_to_local_path` streams S3 objects to managed `tempfile.NamedTemporaryFile` locations, and `IngestionPipeline` guarantees removal in a `finally:` block.

---

## F. ECS Deployment Configuration

### 1. Container Hardening (`backend/Dockerfile`)
- Base Image: `python:3.12-slim`
- User: `appuser` (UID: `10001`, GID: `10001`)
- Health Check: `curl -f http://localhost:8000/api/v1/health || exit 1`
- ASGI Execution: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --timeout-graceful-shutdown 30`

### 2. Auto Scaling Policies
Configured in `infrastructure/terraform/ecs.tf`:
- **Scale Out**: Average CPU > 70% or Average Memory > 80% (60s cooldown).
- **Scale In**: Average CPU < 70% and Memory < 80% (300s cooldown).
- **Task Boundaries**: Min 1, Desired 2, Max 4.

---

## G. Frontend Deployment Configuration

- **Static Asset Delivery**: Amazon S3 + CloudFront Distribution with Origin Access Control (OAC).
- **Cache Strategy**:
  - `dist/index.html`: `Cache-Control: no-cache, no-store, must-revalidate`
  - `dist/assets/*`: `Cache-Control: public, max-age=31536000, immutable`
- **SPA Client-Side Routing**: CloudFront custom error response maps HTTP 403 & 404 to `/index.html` with HTTP 200, preserving client routes like `/workspace/:id`.
- **API Proxying**: CloudFront behavior forwards `/api/*` directly to the Application Load Balancer with zero caching and full header preservation (`Authorization`, `Host`, `Origin`).

---

## H. GitHub Actions CI/CD Workflows

### 1. Continuous Integration (`.github/workflows/ci.yml`)
- Triggers on PRs and pushes to `main`.
- Runs `ruff` linting, `pip-audit` security vulnerability scans, and `pytest tests/ -v`.
- Builds the React frontend SPA (`npm run build`).
- Builds and validates both backend and frontend Docker container images.

### 2. Automated Backend Deployment (`.github/workflows/deploy-backend.yml`)
- Authenticates to AWS using GitHub IAM OIDC (`aws-actions/configure-aws-credentials`).
- Builds and tags backend container with git commit SHA.
- Pushes image to Amazon ECR (`notebooklm-backend`).
- Updates task definition and triggers ECS service rolling update.
- Probes `/api/v1/health` on ALB to verify successful deployment.

### 3. Automated Frontend Deployment (`.github/workflows/deploy-frontend.yml`)
- Builds React production bundle with relative API proxying.
- Synchronizes assets to S3 with distinct cache headers for HTML vs static chunks.
- Triggers CloudFront cache invalidation on `/*`.

---

## I. Terraform Infrastructure as Code

All files reside in `infrastructure/terraform/`:
- [`providers.tf`](file:///c:/Users/parmesh/Desktop/NOTEBOOKLM%20LITE/infrastructure/terraform/providers.tf): AWS Provider (`ap-south-1`), S3 remote state configuration.
- [`variables.tf`](file:///c:/Users/parmesh/Desktop/NOTEBOOKLM%20LITE/infrastructure/terraform/variables.tf): Parameterized environments, subnet CIDRs, compute tiers.
- [`networking.tf`](file:///c:/Users/parmesh/Desktop/NOTEBOOKLM%20LITE/infrastructure/terraform/networking.tf): Custom VPC, 2 public subnets, 2 private subnets, IGW, NAT Gateway.
- [`security_groups.tf`](file:///c:/Users/parmesh/Desktop/NOTEBOOKLM%20LITE/infrastructure/terraform/security_groups.tf): Strict isolation between ALB, ECS Fargate, and RDS.
- [`iam.tf`](file:///c:/Users/parmesh/Desktop/NOTEBOOKLM%20LITE/infrastructure/terraform/iam.tf): ECS Task Execution Role, Task Runtime Role, and GitHub OIDC Role.
- [`s3.tf`](file:///c:/Users/parmesh/Desktop/NOTEBOOKLM%20LITE/infrastructure/terraform/s3.tf): Private documents bucket (SSE-S3 AES256, versioning, lifecycle) & frontend bucket.
- [`cloudfront.tf`](file:///c:/Users/parmesh/Desktop/NOTEBOOKLM%20LITE/infrastructure/terraform/cloudfront.tf): CloudFront CDN distribution with OAC and SPA error routing.
- [`rds.tf`](file:///c:/Users/parmesh/Desktop/NOTEBOOKLM%20LITE/infrastructure/terraform/rds.tf): Amazon RDS PostgreSQL 16 (gp3 encrypted storage, automated backups, private subnet group).
- [`ecs.tf`](file:///c:/Users/parmesh/Desktop/NOTEBOOKLM%20LITE/infrastructure/terraform/ecs.tf): ECS Cluster, Fargate task definition, ALB, Target Group, Autoscaling.
- [`monitoring.tf`](file:///c:/Users/parmesh/Desktop/NOTEBOOKLM%20LITE/infrastructure/terraform/monitoring.tf): CloudWatch Dashboard and alarms for CPU, Memory, 5xx, and RDS connections.
- [`outputs.tf`](file:///c:/Users/parmesh/Desktop/NOTEBOOKLM%20LITE/infrastructure/terraform/outputs.tf): Exported ARNs, DNS names, and endpoints.

---

## J. Monitoring, Observability & Alarms

Configured CloudWatch Alarms:
1. `notebooklm-ecs-cpu-high`: Triggers when average CPU > 85% for 3 consecutive minutes.
2. `notebooklm-ecs-memory-high`: Triggers when average Memory > 85% for 3 consecutive minutes.
3. `notebooklm-unhealthy-hosts`: Triggers immediately when any Fargate task fails ALB target group health checks.
4. `notebooklm-high-5xx-errors`: Triggers when ALB registers > 10 HTTP 5xx responses in 2 minutes.
5. `notebooklm-rds-high-connections`: Triggers when database connections exceed 80.
6. **Prometheus Metrics**: Retained [`/api/v1/metrics`](file:///c:/Users/parmesh/Desktop/NOTEBOOKLM%20LITE/backend/app/api/v1/health.py) for custom scraping.

---

## K. Cost Estimation & Budget Control

### Estimated Monthly AWS Cost (Region: `ap-south-1` Mumbai)

| Service | Dev / Free Tier Eligible | High-Availability Production | Cost Optimization Notes |
| :--- | :--- | :--- | :--- |
| **Amazon S3** | $0.00 (5 GB free tier) | $0.35 (10 GB + API requests) | Lifecycle rules transition old versions to Glacier |
| **Amazon CloudFront** | $0.00 (1 TB free tier) | $0.00 (under 1 TB/mo) | Free tier covers standard bandwidth |
| **Amazon RDS PostgreSQL** | $0.00 (db.t4g.micro 750h/mo free) | $32.00 (db.t4g.small single-AZ) | Encrypted gp3 storage, automated snapshots |
| **AWS Fargate (ECS)** | $9.30 (1 task, 0.25 vCPU, 0.5 GB) | $36.00 (2 tasks, 0.5 vCPU, 1 GB) | Autoscales down to 1 task during low activity |
| **Application Load Balancer** | $20.50 | $22.00 | Standard base hourly rate ($0.0225/hr) |
| **NAT Gateway** | $0.00 (use public subnets in dev) | $32.85 ($0.045/hr) | In dev, use VPC endpoints or direct egress |
| **AWS Secrets Manager** | $0.80 (2 secrets) | $0.80 (2 secrets) | $0.40 per secret per month |
| **Amazon CloudWatch** | $0.00 (free tier) | $3.50 (logs + alarms) | 30-day log retention policy |
| **Qdrant Cloud** | $0.00 (existing cluster) | $0.00 (existing cluster) | Zero additional migration costs |
| **Google Gemini API** | Pay-as-you-go | Pay-as-you-go | Token-based; protected by sliding rate limiter |
| **Total Estimated Cost** | **~$10.90 – $30.60 / mo** | **~$95.00 – $127.50 / mo** | |

### Budget Alerts Recommendation
Configure an **AWS Budget Alert** at **$30.00/month** for development or **$100.00/month** for production with notifications triggered at 80% and 100% of forecast spend.

---

## L. Test Results Summary

| Test Area | Executed Tests | Status | Notes |
| :--- | :---: | :---: | :--- |
| **LangGraph Agent Workflow** | 12 | **PASS** | Simple query, multi-doc, comparison, summary, refusal, multitenant isolation |
| **RAG Evaluation Suite** | 15 | **PASS** | Grounding, abstention, page hints, category scores |
| **Production Readiness & Metrics** | 4 | **PASS** | Prometheus `/metrics`, `/health`, rate limiting, security headers |
| **API Contracts & Authorization** | 10 | **PASS** | Chat contract, notebook ownership, multi-tenant boundaries |
| **S3 Dual-Backend Storage** | Integration | **PASS** | Magic-byte validation, presigned URL generation, temporary local download resolution |
| **Docker Build & Non-Root User** | Container | **PASS** | Non-root `appuser` UID 10001, curl healthcheck verified |
| **Live AWS Cloud Infrastructure** | Cloud Provisioning | **NOT TESTED** | Terraform files generated; awaiting user approval to avoid unapproved billable charges |

---

## M. Actual AWS Deployment Status

* **Status**: **NOT TESTED** (Infrastructure specification complete, pending explicit user provisioning approval).
* **Reason**: Strict engineering rule compliance — *never provision billable AWS resources (ALB, NAT Gateways, RDS, ECS Fargate) without explicit user authorization*.
* **Readiness**: All Terraform templates, Dockerfiles, and GitHub Actions workflows are validated and ready to deploy with `terraform apply`.

---

## N. Rollback and Disaster Recovery Procedures

1. **ECS Backend Rollback**:
   To roll back an unhealthy deployment to the previous working task definition:
   ```bash
   aws ecs update-service \
     --cluster notebooklm-cluster-production \
     --service notebooklm-backend-service \
     --task-definition notebooklm-backend:<PREVIOUS_REVISION_NUMBER>
   ```
2. **Frontend Rollback**:
   Re-deploy the previous commit artifact or restore previous versioned S3 objects:
   ```bash
   aws s3 sync dist/ s3://<frontend-bucket>/ --delete
   aws cloudfront create-invalidation --distribution-id <DIST_ID> --paths "/*"
   ```
3. **Database Point-In-Time Recovery (PITR)**:
   RDS automated backups allow point-in-time recovery to any minute within the 7-day retention period:
   ```bash
   aws rds restore-db-instance-to-point-in-time \
     --source-db-instance-identifier notebooklm-db-production \
     --target-db-instance-identifier notebooklm-db-restored \
     --restore-time 2026-11-10T12:00:00Z
   ```
4. **S3 Document Disaster Recovery**:
   Versioning is enabled on the document bucket. Accidental deletions place a delete marker that can be removed to recover the underlying PDF.

---

## O. Known Limitations

1. **Qdrant Cloud Network Dependency**: Qdrant Cloud cluster operates in `us-west-1`. Cross-region network latency (~200ms) applies to vector queries originating from `ap-south-1`. This was preserved intentionally to avoid re-embedding existing corpora.
2. **PyMuPDF Memory Spikes**: Large documents (500+ pages) require ~150–250MB RAM during extraction. Concurrency is bounded to 5 simultaneous operations via `_INGESTION_SEMAPHORE` to fit within 1024MB Fargate tasks.

---

## P. Recommended Next Engineering Milestone

1. **Domain & SSL Setup**: Provision an AWS Certificate Manager (ACM) public certificate in `us-east-1` (for CloudFront) and `ap-south-1` (for ALB) to enable custom domain routing (e.g. `app.yourdomain.com`).
2. **AWS Provisioning Execution**: Execute `terraform plan` and `terraform apply` when the user approves cloud provisioning.
3. **Automated Continuous Evaluation**: Schedule the 70-question RAG benchmark as a nightly GitHub Actions workflow against the deployed staging environment.

