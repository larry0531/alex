# Alex - Complete System Architecture Diagram

## Full System Overview

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                         ALEX PLATFORM                                           │
│                          Agentic Learning Equities eXplainer                                    │
└─────────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│  USER LAYER                                                                                      │
│                                                                                                  │
│   ┌──────────────┐      ┌────────────────────┐      ┌──────────────────────────────────────┐    │
│   │   Browser     │─────▶│   CloudFront CDN   │─────▶│  S3 Static Site (NextJS Pages Router)│    │
│   │   (User)      │      │   (HTTPS + Cache)  │      │  /dashboard  /analysis  /accounts    │    │
│   └──────┬───────┘      └────────────────────┘      │  /advisor-team  /accounts/[id]        │    │
│          │                                           └──────────────────────────────────────┘    │
│          │              ┌────────────────────┐                                                    │
│          │              │  Clerk Auth (JWT)  │◀─── User sign-in / sign-up                        │
│          │              └────────────────────┘                                                    │
│          │                                                                                       │
└──────────┼───────────────────────────────────────────────────────────────────────────────────────┘
           │
           │  API calls (authenticated via Clerk JWT)
           ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│  API LAYER                                                                                       │
│                                                                                                  │
│   ┌────────────────────┐      ┌──────────────────────────┐      ┌──────────────────────┐        │
│   │  API Gateway       │─────▶│  Lambda (alex-api)       │─────▶│  Aurora Serverless v2 │        │
│   │  (REST + API Key)  │      │  FastAPI + Mangum        │      │  PostgreSQL (Data API)│        │
│   └────────────────────┘      │  ClerkHTTPBearer guard   │      └──────────────────────┘        │
│                               └──────────┬───────────────┘                                      │
│                                          │                                                       │
│                                          │  POST /api/analyze                                    │
│                                          ▼                                                       │
│                               ┌──────────────────────┐                                          │
│                               │  SQS Queue           │                                          │
│                               │  (Job orchestration)  │                                          │
│                               └──────────┬───────────┘                                          │
│                                          │                                                       │
└──────────────────────────────────────────┼───────────────────────────────────────────────────────┘
                                           │
                                           │  SQS triggers Lambda
                                           ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│  AGENT ORCHESTRA LAYER (OpenAI Agents SDK + LiteLLM + AWS Bedrock Nova Pro)                      │
│                                                                                                  │
│   ┌─────────────────────────────────────────────────────────────────────────────────────────┐    │
│   │                        PLANNER (Orchestrator Lambda)                                     │    │
│   │                        ─────────────────────────────                                     │    │
│   │  • Receives job_id from SQS                                                              │    │
│   │  • Updates market prices via Polygon.io                                                  │    │
│   │  • Calls Tagger synchronously for unclassified instruments                               │    │
│   │  • Orchestrates Reporter, Charter, Retirement via tool calls                             │    │
│   │  • Writes final summary to database                                                      │    │
│   │  • Retry: tenacity (5 attempts, exponential backoff on RateLimitError)                   │    │
│   │                                                                                          │    │
│   │         ┌──────────────┐                                                                 │    │
│   │         │  Polygon.io  │  Market price updates                                           │    │
│   │         └──────────────┘                                                                 │    │
│   └────┬────────────┬────────────────┬────────────────┬──────────────────────────────────────┘    │
│        │            │                │                │                                           │
│        │ sync       │ async tool     │ async tool     │ async tool                               │
│        ▼            ▼                ▼                ▼                                           │
│   ┌─────────┐ ┌───────────┐   ┌───────────┐   ┌──────────────┐                                 │
│   │ TAGGER  │ │ REPORTER  │   │ CHARTER   │   │ RETIREMENT   │                                 │
│   │ Lambda  │ │ Lambda    │   │ Lambda    │   │ Lambda       │                                 │
│   ├─────────┤ ├───────────┤   ├───────────┤   ├──────────────┤                                 │
│   │Classify │ │Portfolio  │   │Pie/Bar    │   │Monte Carlo   │                                 │
│   │ETFs &   │ │narrative  │   │chart JSON │   │simulations   │                                 │
│   │stocks   │ │report in  │   │for        │   │& retirement  │                                 │
│   │by type, │ │markdown   │   │Recharts   │   │projections   │                                 │
│   │region,  │ │           │   │           │   │              │                                 │
│   │sector   │ │           │   │           │   │              │                                 │
│   ├─────────┤ ├───────────┤   ├───────────┤   ├──────────────┤                                 │
│   │Struct.  │ │Tools +    │   │Direct JSON│   │Tools (no     │                                 │
│   │Output   │ │Context    │   │output     │   │context)      │                                 │
│   │(no      │ │           │   │(no tools) │   │              │                                 │
│   │tools)   │ │           │   │           │   │              │                                 │
│   └────┬────┘ └─────┬─────┘   └─────┬─────┘   └──────┬───────┘                                 │
│        │            │               │                │                                           │
│        │            │               │                │                                           │
│        ▼            ▼               ▼                ▼                                           │
│   ┌──────────────────────────────────────────────────────────┐                                   │
│   │              Aurora Serverless v2 (Jobs Table)            │                                   │
│   │  ┌──────────┬──────────────┬──────────────┬────────────┐ │                                   │
│   │  │ tagger   │report_payload│charts_payload│retirement_ │ │                                   │
│   │  │ updates  │ (markdown)   │ (JSON)       │payload     │ │                                   │
│   │  │ instru-  │              │              │(projections│ │                                   │
│   │  │ ments    │              │              │)           │ │                                   │
│   │  └──────────┴──────────────┴──────────────┴────────────┘ │                                   │
│   │  status: pending ──▶ running ──▶ completed / failed      │                                   │
│   └──────────────────────────────────────────────────────────┘                                   │
│                                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│  KNOWLEDGE / RESEARCH LAYER                                                                      │
│                                                                                                  │
│   ┌─────────────────────┐      ┌──────────────────┐      ┌──────────────────────┐               │
│   │  EventBridge         │─────▶│  Lambda           │─────▶│  App Runner           │               │
│   │  Scheduler           │      │  (alex-scheduler) │      │  (alex-researcher)    │               │
│   │  (every 2 hours)     │      └──────────────────┘      │                       │               │
│   └─────────────────────┘                                  │  Researcher Agent     │               │
│                                                            │  ┌─────────────────┐ │               │
│                                                            │  │ Playwright MCP  │ │               │
│                                                            │  │ (web browsing)  │ │               │
│                                                            │  └─────────────────┘ │               │
│                                                            └──────────┬───────────┘               │
│                                                                       │                          │
│                              stores research via                      │                          │
│                              API Gateway + ingest Lambda              │                          │
│                                                                       ▼                          │
│    ┌──────────────────┐      ┌──────────────────────┐      ┌──────────────────────┐             │
│    │  SageMaker        │◀─────│  Lambda               │◀─────│  API Gateway          │             │
│    │  Serverless       │      │  (alex-ingest)        │      │  (API Key Auth)       │             │
│    │  (all-MiniLM-L6)  │      │  Document Processing  │      └──────────────────────┘             │
│    │  384-dim embeddings│      └──────────┬───────────┘                                           │
│    └──────────────────┘                  │                                                        │
│                                          ▼                                                        │
│                               ┌──────────────────────┐                                           │
│                               │  S3 Vectors           │◀── Reporter's get_market_insights tool   │
│                               │  (Vector Storage)     │    queries here via SageMaker embeddings  │
│                               │  90% cheaper than     │                                           │
│                               │  OpenSearch            │                                           │
│                               └──────────────────────┘                                           │
│                                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│  AI / ML SERVICES                                                                                │
│                                                                                                  │
│   ┌──────────────────────────────────┐      ┌──────────────────────────────────┐                 │
│   │  AWS Bedrock (Nova Pro)           │      │  SageMaker Serverless             │                 │
│   │  ─────────────────────────        │      │  ─────────────────────            │                 │
│   │  • LLM for all 6 agents          │      │  • HuggingFace all-MiniLM-L6-v2  │                 │
│   │  • Connected via LiteLLM          │      │  • 384-dimensional embeddings    │                 │
│   │  • Inference profiles for         │      │  • Used by ingest + search       │                 │
│   │    cross-region access            │      │  • Serverless (pay per request)  │                 │
│   │  • AWS_REGION_NAME env var        │      │                                  │                 │
│   └──────────────────────────────────┘      └──────────────────────────────────┘                 │
│                                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│  OBSERVABILITY & ENTERPRISE                                                                      │
│                                                                                                  │
│   ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐   ┌──────────────────┐       │
│   │  LangFuse        │   │  CloudWatch      │   │  WAF             │   │  Secrets Manager  │       │
│   │  (Agent Traces)  │   │  (Dashboards &   │   │  (Web App        │   │  (Aurora creds)   │       │
│   │                  │   │   Alarms)        │   │   Firewall)      │   │                   │       │
│   └─────────────────┘   └─────────────────┘   └─────────────────┘   └──────────────────┘       │
│                                                                                                  │
│   ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐                               │
│   │  Logfire          │   │  ECR             │   │  IAM Roles       │                               │
│   │  (OpenAI Agents   │   │  (Docker images  │   │  (Least privilege │                               │
│   │   SDK tracing)    │   │   for Lambda +   │   │   per service)    │                               │
│   │                  │   │   App Runner)    │   │                   │                               │
│   └─────────────────┘   └─────────────────┘   └─────────────────┘                               │
│                                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│  INFRASTRUCTURE (Terraform - Independent Directories)                                            │
│                                                                                                  │
│   ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐    │
│   │ 2_sagemaker│ │ 3_ingestion│ │4_researcher│ │ 5_database │ │  6_agents  │ │ 7_frontend │    │
│   │            │ │            │ │            │ │            │ │            │ │            │    │
│   │ SageMaker  │ │ S3 Vectors │ │ App Runner │ │ Aurora v2  │ │ 5 Lambdas  │ │ CloudFront │    │
│   │ endpoint   │ │ Ingest λ   │ │ ECR        │ │ Data API   │ │ SQS Queue  │ │ S3 bucket  │    │
│   │            │ │ API GW     │ │ EventBridge│ │ Secrets    │ │ S3 (pkgs)  │ │ API GW     │    │
│   └────────────┘ └────────────┘ └────────────┘ └────────────┘ └────────────┘ └────────────┘    │
│                                                                                                  │
│   ┌────────────┐                                                                                 │
│   │8_enterprise│  Each directory has its own local state file and terraform.tfvars               │
│   │            │  Deploy incrementally: guide by guide                                           │
│   │ CloudWatch │  Destroy independently: terraform destroy in each dir                          │
│   │ Dashboards │                                                                                 │
│   └────────────┘                                                                                 │
│                                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘


## Request Flow: User Triggers Portfolio Analysis

  1. User clicks "Analyze" in the NextJS frontend
  2. Frontend calls POST /api/analyze (via CloudFront → API Gateway → Lambda)
  3. API Lambda creates a Job record (status: pending) in Aurora
  4. API Lambda sends job_id to SQS queue
  5. SQS triggers Planner Lambda
  6. Planner updates market prices from Polygon.io
  7. Planner calls Tagger (sync) to classify any unknown instruments
  8. Planner invokes Reporter, Charter, Retirement (parallel via tool calls)
     - Reporter queries S3 Vectors for market insights, writes markdown report
     - Charter generates Recharts-compatible JSON for pie/bar charts
     - Retirement runs Monte Carlo simulations for income projections
  9. Each sub-agent saves results to the Jobs table in Aurora
  10. Planner writes a final summary, sets job status to "completed"
  11. Frontend polls GET /api/jobs/{id} and displays results


## Research Flow: Autonomous Knowledge Building

  1. EventBridge fires every 2 hours
  2. Scheduler Lambda calls App Runner researcher endpoint
  3. Researcher agent browses financial sites via Playwright MCP
  4. Research documents sent to API Gateway → Ingest Lambda
  5. Ingest Lambda generates embeddings via SageMaker
  6. Embeddings stored in S3 Vectors
  7. Reporter agent later queries S3 Vectors for context during analysis


## Database Schema (Aurora Serverless v2)

  ┌──────────┐     ┌───────────┐     ┌───────────┐     ┌──────────────┐
  │  Users   │────▶│ Accounts  │────▶│ Positions │────▶│ Instruments  │
  │          │     │           │     │           │     │              │
  │ clerk_id │     │ user_id   │     │ account_id│     │ symbol       │
  │ name     │     │ name      │     │ instrument│     │ name         │
  │ retire_  │     │           │     │   _id     │     │ type         │
  │  years   │     │           │     │ quantity  │     │ regions      │
  │ income_  │     │           │     │           │     │ sectors      │
  │  target  │     │           │     │           │     │ asset_classes│
  └──────────┘     └───────────┘     └───────────┘     └──────────────┘
                                                              ▲
       ┌──────────┐                                           │
       │  Jobs    │                                    Tagger classifies
       │          │                                    instruments here
       │ user_id  │
       │ status   │
       │ report_  │
       │  payload │
       │ charts_  │
       │  payload │
       │retirement│
       │ _payload │
       │ summary_ │
       │  payload │
       └──────────┘
```
