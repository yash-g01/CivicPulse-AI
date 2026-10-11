# CivicPulse AI - AWS Cloud Readiness & Deployment Guide

## Status: All 5 Cloud Blockers Resolved (Production Ready)

| # | Component | Cloud Blocker | Resolution Implemented | Status |
|---|---|---|---|---|
| **1** | **`filing_agent.py`** | `headless=False` or crashing on Linux without display | Configurable `HEADLESS_BROWSER=true` in `config.py` + added `--no-sandbox`, `--disable-setuid-sandbox`, `--disable-dev-shm-usage`, `--disable-gpu` flags to Chromium launch | ✅ **Resolved** |
| **2** | **`filing_agent.py`** | Ephemeral `/tmp` storage across containers / instances | Added automatic S3 fallback: if local files are missing, retrieves `before_s3_key`/`before_s3_keys` from S3 before browser upload | ✅ **Resolved** |
| **3** | **Worker Lifecycle** | Serverless / Lambda freeze cutting off browser & OTP loop | Clarified architecture: Backend requires persistent container or VM (**AWS EC2 `t3.medium`** or **AWS App Runner / ECS Fargate**). Dockerfile & Compose created. | ✅ **Resolved** |
| **4** | **`frontend/src/api.ts`** | Hardcoded `/api/v1` breaking on remote origins | Configured `VITE_API_BASE_URL` with fallback helper `getFullApiUrl()`, plus created `.env.example` & `.env.production` | ✅ **Resolved** |
| **5** | **`dynamodb.py` & `s3.py`** | Hardcoded credentials preventing IAM Instance Profiles | Dynamic Boto3 client initialization: if credentials are omitted or empty, Boto3 automatically falls back to AWS IAM Instance Profiles & ECS Task Roles | ✅ **Resolved** |

---

## Additional Cloud Hardening Implemented

1. **AWS ALB & ECS Healthcheck Endpoints**:
   - Added `GET /health` and `GET /` to `backend/app/main.py` for target group health checks.
2. **Configurable CORS**:
   - Added `CORS_ORIGINS` to `config.py` and `main.py` supporting comma-separated custom domains or `*`.
3. **Resilient AI Client Initialization**:
   - Refactored `triage_service.py` and `audit_service.py` with lazy `_get_groq_client()` to prevent startup failure when building images or before secret injection.
4. **Complete Dockerization**:
   - `backend/Dockerfile` using `python:3.11-slim` with system libraries and `playwright install --with-deps chromium`.
   - `docker-compose.yml` for unified local/cloud container startup.
5. **Multi-Image Evidence Proxy Fallback**:
   - Enhanced `GET /api/v1/evidence/{ticket_id}/{kind}` in `routes.py` to check both single `before_s3_key` and array `before_s3_keys`.

---

## Recommended AWS Production Architecture

```
                       ┌────────────────────────┐
                       │   Amazon CloudFront    │
                       └───────────┬────────────┘
                                   │
              ┌────────────────────┴────────────────────┐
              ▼                                         ▼
   ┌──────────────────────┐                  ┌──────────────────────┐
   │    Amazon S3 Bucket  │                  │   AWS EC2 / ECS      │
   │  (Static React Dist) │                  │ (FastAPI + Chromium) │
   └──────────────────────┘                  └──────────┬───────────┘
                                                        │
                                   ┌────────────────────┴────────────┐
                                   ▼                                 ▼
                         ┌───────────────────┐             ┌───────────────────┐
                         │  Amazon DynamoDB  │             │     Amazon S3     │
                         │ (State & Caching) │             │  (Evidence Store) │
                         └───────────────────┘             └───────────────────┘
```

---

## Step-by-Step AWS Deployment Walkthrough

### Part 1: Backend Deployment on AWS EC2 (Recommended: `t3.medium`)

1. **Launch Instance**:
   - **AMI**: Ubuntu Server 24.04 LTS (x86_64)
   - **Instance Type**: `t3.medium` (2 vCPU, 4GB RAM)
   - **IAM Role**: Attach an IAM Role with policies for DynamoDB (`CivicPulseTable`) and S3 (`civicpulse-evidence-store`).

2. **Security Group Inbound Rules**:
   - Port `22` (SSH from your IP)
   - Port `80` / `443` (HTTP/HTTPS from anywhere)
   - Port `8000` (FastAPI backend if connecting directly, or routed through Nginx/ALB)

3. **Install Docker on EC2**:
   ```bash
   sudo apt update && sudo apt install -y docker.io docker-compose-v2 git
   sudo usermod -aG docker ubuntu
   newgrp docker
   ```

4. **Clone & Configure**:
   ```bash
   git clone <your-repo-url> civicpulse-ai
   cd civicpulse-ai/backend
   cp .env.example .env
   # Add your GROQ_API_KEY in .env. AWS credentials can be left blank (handled by IAM Role).
   ```

5. **Run via Docker Compose or Systemd**:
   ```bash
   cd ..
   docker compose up -d --build
   ```

6. **Verify Health**:
   ```bash
   curl http://localhost:8000/health
   # Returns: {"status":"healthy","service":"CivicPulse AI API",...}
   ```

---

### Part 2: Frontend Deployment on Amazon S3 + CloudFront

1. **Build Static Distribution**:
   ```bash
   cd frontend
   # Set your production backend URL in .env.production (or leave blank if using CloudFront path routing)
   npm run build
   ```
   This generates the optimized bundle in `frontend/dist/`.

2. **Upload to S3**:
   ```bash
   aws s3 sync dist/ s3://<your-frontend-bucket-name> --delete
   ```

3. **CloudFront Distribution**:
   - **Default Root Object**: `index.html`
   - **Error Pages**: Custom Error Response -> HTTP 403/404 -> Response Page `/index.html` (HTTP 200) for client-side React routing.
   - **Optional Combined Routing (Zero CORS)**:
     - Origin 1 (Default `/*`): S3 Frontend Bucket
     - Origin 2 (`/api/*` and `/mock-pmc-portal*`): EC2 ALB / Backend Public IP (Forward headers and allow GET, POST, PUT, DELETE, OPTIONS).

---

### Part 3: IAM Policy Reference (Least Privilege)

Attach this policy to your EC2 IAM Role or ECS Task Role:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DynamoDBAccess",
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:Scan",
        "dynamodb:Query"
      ],
      "Resource": "arn:aws:dynamodb:*:*:table/CivicPulseTable*"
    },
    {
      "Sid": "S3EvidenceStoreAccess",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::civicpulse-evidence-store",
        "arn:aws:s3:::civicpulse-evidence-store/*"
      ]
    }
  ]
}
```