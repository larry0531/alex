# Alex - AI in Production Course Project Guide

## Project Overview

**Alex** (Agentic Learning Equities eXplainer) is a multi-agent enterprise-grade SaaS financial planning platform. This is the capstone project for Weeks 3 and 4 of the "AI in Production" course taught by Ed Donner on Udemy that deploys Agent solutions to production.

The user is a student on the course. You are working with the user to help them build Alex successfully. The user is working in Cursor (the VS Code fork), and they might be on a Windows PC, a Mac (intel or Apple silicon) or a Linux machine. All python code is run with uv and there are uv projects in every directory that needs it. The student is familiar with AWS services (Lambda, App Runner, Cloudfront) and has been introduced to Terraform, uv, NextJS and docker. They have budget alerts set, but they should still regularly check the billing screens in AWS console to keep a close watch on costs.

The student has an AWS root user, and also an IAM user called "aiengineer" with permissions. They have run `aws configure` and should be signed in as the aiengineer user with their default region.

### What Students Will Build

Students will deploy a complete production AI system featuring:
- **Multi-agent collaboration**: 5 specialized AI agents working together via orchestration
- **Serverless architecture**: Lambda, Aurora Serverless v2, App Runner, API Gateway, SQS
- **Cost-optimized vector storage**: S3 Vectors (90% cheaper than OpenSearch)
- **Real-time financial analysis**: Portfolio management, retirement projections, market research
- **Production-grade practices**: Observability, guardrails, security, monitoring
- **Full-stack application**: NextJS React frontend with Clerk authentication

### Learning Objectives

By completing this project, students will:
1. Deploy and manage production AI infrastructure on AWS
2. Implement multi-agent systems using the OpenAI Agents SDK
3. Integrate AWS Bedrock (with Nova Pro model) for LLM capabilities
4. Build cost-effective vector search with S3 Vectors and SageMaker embeddings
5. Create serverless agent orchestration with SQS and Lambda
6. Deploy a complete full-stack SaaS application
7. Implement enterprise features: monitoring, observability, guardrails, security

### Commercial Product

Alex is a SaaS product that provides insights on users' equity portfolios through reports and charts. Alex is integrated with Clerk for user management and the database architecture keeps user data separate.

---

## Directory Structure

```
alex/
├── guides/              # Step-by-step deployment guides (START HERE)
│   ├── 1_permissions.md
│   ├── 2_sagemaker.md
│   ├── 3_ingest.md
│   ├── 4_researcher.md
│   ├── 5_database.md
│   ├── 6_agents.md
│   ├── 7_frontend.md
│   ├── 8_enterprise.md
│   ├── architecture.md
│   └── agent_architecture.md
│
├── backend/             # Agent code and Lambda functions
│   ├── planner/         # Orchestrator agent (SQS-triggered Lambda)
│   │   ├── lambda_handler.py   # SQS event handler, runs orchestrator
│   │   ├── agent.py            # PlannerContext, tools, create_agent()
│   │   ├── templates.py        # ORCHESTRATOR_INSTRUCTIONS prompt
│   │   ├── market.py           # Polygon.io price updates
│   │   ├── observability.py    # LangFuse + Logfire integration
│   │   ├── test_simple.py      # Local test with MOCK_LAMBDAS=true
│   │   └── test_full.py        # AWS deployment test
│   │
│   ├── tagger/          # Instrument classification agent
│   │   ├── lambda_handler.py
│   │   ├── agent.py            # Uses structured outputs (no tools)
│   │   ├── templates.py
│   │   ├── test_simple.py
│   │   └── test_full.py
│   │
│   ├── reporter/        # Portfolio analysis narrative agent
│   │   ├── lambda_handler.py
│   │   ├── agent.py            # ReporterContext, get_market_insights tool
│   │   ├── templates.py        # REPORTER_INSTRUCTIONS prompt
│   │   ├── judge.py            # LLM-as-judge quality evaluation
│   │   ├── test_simple.py
│   │   └── test_full.py
│   │
│   ├── charter/         # Visualization data agent
│   │   ├── lambda_handler.py
│   │   ├── agent.py            # No tools - outputs JSON directly
│   │   ├── templates.py        # CHARTER_INSTRUCTIONS + create_charter_task()
│   │   ├── test_simple.py
│   │   └── test_full.py
│   │
│   ├── retirement/      # Retirement projection agent
│   │   ├── lambda_handler.py
│   │   ├── agent.py            # Uses tools for calculations
│   │   ├── templates.py
│   │   ├── test_simple.py
│   │   └── test_full.py
│   │
│   ├── researcher/      # Market research agent (App Runner, NOT Lambda)
│   │   ├── server.py           # FastAPI app, REGION and MODEL hardcoded here
│   │   ├── context.py          # Agent instructions and prompts
│   │   ├── mcp_servers.py      # Playwright MCP server setup
│   │   ├── tools.py            # ingest_financial_document tool
│   │   ├── deploy.py           # Build and push Docker image to ECR
│   │   ├── test_local.py       # Local testing
│   │   └── test_research.py    # Research endpoint test
│   │
│   ├── ingest/          # Document ingestion Lambda (S3 Vectors)
│   │   ├── ingest_s3vectors.py     # Lambda handler for ingestion
│   │   ├── search_s3vectors.py     # Vector search utility
│   │   ├── test_ingest_s3vectors.py
│   │   └── test_search_s3vectors.py
│   │
│   ├── database/        # Shared database library (Aurora Data API)
│   │   ├── src/
│   │   │   ├── __init__.py         # Exports Database class
│   │   │   ├── client.py           # DataAPIClient wrapping AWS RDS Data API
│   │   │   ├── models.py           # Users, Instruments, Accounts, Positions, Jobs
│   │   │   └── schemas.py          # Pydantic validation schemas
│   │   ├── run_migrations.py       # Apply DB schema
│   │   ├── seed_data.py            # Load 22 ETFs seed data
│   │   ├── reset_db.py             # Drop and recreate tables
│   │   └── verify_database.py      # Check DB connectivity
│   │
│   ├── api/             # FastAPI backend for frontend
│   │   ├── main.py             # All REST endpoints + Mangum adapter
│   │   ├── lambda_handler.py   # Lambda entry point
│   │   └── package_docker.py   # Docker packaging for deployment
│   │
│   ├── scheduler/       # EventBridge scheduler Lambda
│   │   └── lambda_function.py
│   │
│   ├── package_docker.py       # Master packaging script (all agents)
│   ├── deploy_all_lambdas.py   # Deploy all Lambda functions
│   ├── test_simple.py          # Top-level test (mocked)
│   ├── test_full.py            # Top-level test (live AWS)
│   ├── test_scale.py           # Load/scale testing
│   ├── test_multiple_accounts.py
│   ├── watch_agents.py         # Monitor agent execution
│   ├── check_job_details.py    # Inspect job results in DB
│   └── check_db.py             # Database inspection utility
│
├── frontend/            # NextJS React application (Pages Router)
│   ├── pages/
│   │   ├── index.tsx           # Landing page
│   │   ├── dashboard.tsx       # Main dashboard with jobs list
│   │   ├── analysis.tsx        # Portfolio analysis results
│   │   ├── accounts.tsx        # Account management
│   │   ├── accounts/[id].tsx   # Individual account positions
│   │   ├── advisor-team.tsx    # AI agent team info page
│   │   ├── _app.tsx            # App wrapper with Clerk provider
│   │   ├── _document.tsx       # HTML document
│   │   ├── 404.tsx             # Not found page
│   │   └── 500.tsx             # Error page
│   ├── components/             # Reusable React components
│   └── lib/                    # Shared utilities/API client
│
├── terraform/           # Infrastructure as Code (IMPORTANT: Independent directories)
│   ├── 2_sagemaker/     # SageMaker embedding endpoint
│   ├── 3_ingestion/     # S3 Vectors and ingest Lambda
│   ├── 4_researcher/    # App Runner research service
│   ├── 5_database/      # Aurora Serverless v2
│   ├── 6_agents/        # Multi-agent Lambda functions (all 5 agents + API)
│   ├── 7_frontend/      # CloudFront, S3, API Gateway
│   └── 8_enterprise/    # CloudWatch dashboards and monitoring
│
└── scripts/             # Deployment and local development scripts
    ├── deploy.py        # Frontend deployment to S3/CloudFront
    ├── run_local.py     # Run frontend + backend locally (parallel)
    └── destroy.py       # Cleanup script
```

---

## Course Structure: The 8 Guides

**IMPORTANT:** before working with the student, you MUST read all guides in the guides folder, in the correct order (1-8), to fully understand the project.

### Week 3: Research Infrastructure

**Day 3 - Foundations**
- **Guide 1: AWS Permissions** (1_permissions.md)
  - Set up IAM permissions for Alex project
  - Create AlexAccess group with required policies
  - Configure AWS CLI and credentials

- **Guide 2: SageMaker Deployment** (2_sagemaker.md)
  - Deploy SageMaker Serverless endpoint for embeddings
  - Use HuggingFace all-MiniLM-L6-v2 model
  - Test embedding generation
  - Understand serverless vs always-on endpoints

**Day 4 - Vector Storage**
- **Guide 3: Ingestion Pipeline** (3_ingest.md)
  - Create S3 Vectors bucket (90% cost savings!)
  - Deploy Lambda function for document ingestion
  - Set up API Gateway with API key auth
  - Test document storage and search

**Day 5 - Research Agent**
- **Guide 4: Researcher Agent** (4_researcher.md)
  - Deploy autonomous research agent on App Runner
  - Use AWS Bedrock with Nova Pro model
  - Integrate Playwright MCP server for web browsing
  - Set up EventBridge scheduler (optional)
  - **IMPORTANT**: `backend/researcher/server.py` has hardcoded REGION and MODEL variables that students must update

### Week 4: Portfolio Management Platform

**Day 1 - Database**
- **Guide 5: Database & Infrastructure** (5_database.md)
  - Deploy Aurora Serverless v2 PostgreSQL
  - Enable Data API (no VPC complexity!)
  - Create database schema
  - Load seed data (22 ETFs)
  - Set up shared database library

**Day 2 - Agent Orchestra**
- **Guide 6: AI Agent Orchestra** (6_agents.md)
  - Deploy 5 Lambda agents (Planner, Tagger, Reporter, Charter, Retirement)
  - Set up SQS queue for orchestration
  - Configure agent collaboration patterns
  - Test local and remote execution
  - Implement parallel agent processing

**Day 3 - Frontend**
- **Guide 7: Frontend & API** (7_frontend.md)
  - Set up Clerk authentication
  - Deploy NextJS React frontend
  - Create FastAPI backend on Lambda
  - Configure CloudFront CDN
  - Test portfolio management and AI analysis

**Day 4 - Enterprise Features**
- **Guide 8: Enterprise Grade** (8_enterprise.md)
  - Implement scalability configurations
  - Add security layers (WAF, VPC endpoints, GuardDuty)
  - Set up CloudWatch dashboards and alarms
  - Implement guardrails and validation
  - Add explainability features
  - Configure LangFuse observability

For context, in prior weeks the students learned how to deploy to AWS, the key AWS services like Lambda and App Runner, and using Clerk for user management (needs NextJS to use Pages Router).

---

## IMPORTANT: Working with students - approach

Students might be on Windows PC, Mac (Intel or Apple Silicon) or Linux. Always use uv for ALL python code; there are uv projects in every directory. It is not a problem to have a uv project in a subdirectory of another uv project, although uv may show a warning.

Always do `uv add package` and `uv run module.py`, but NEVER `pip install xxx` and NEVER `python -c "code"` or `python -m module.py` or `python script.py`.
It is VERY IMPORTANT that you do not use the python command outside a uv project.
Try to lean away from shell scripts or Powershell scripts as they are platform dependent. Heavily favor writing python scripts (via uv) and managing files in the Cursor File Explorer, as this will be clear for all students.

## Working with Students: Core Principles

### Before starting, always read all the guides in the guides folder for the full background

### 1. **Always Establish Context First**

When a student asks for help:
1. **Ask which guide/day they're on** - This is critical for understanding what infrastructure they have deployed
2. **Ask what they're trying to accomplish** - Understand the goal before diving into code
3. **Ask what error or behavior they're seeing** - Get the actual error message, not their interpretation

### 2. **Diagnose Before Fixing** ⚠️ MOST IMPORTANT

**DO NOT jump to conclusions and write lots of code before the problem is truly understood.**

Common mistakes to avoid:
- Writing defensive code with `isinstance()` checks before understanding the root cause
- Adding try/except blocks that hide the real error
- Creating workarounds that mask the actual problem
- Making multiple changes at once (makes debugging impossible)

**Instead, follow this process:**
1. **Reproduce the issue** - Ask for exact error messages, logs, commands
2. **Identify root cause** - Use CloudWatch logs, AWS Console, error traces
3. **Verify understanding** - Explain what you think is happening and confirm with student
4. **Propose minimal fix** - Change one thing at a time
5. **Test and verify** - Confirm the fix works before moving on

### 3. **Common Root Causes (Check These First)**

Before writing any code, check these common issues:

**Docker Desktop Not Running** (Most common with `package_docker.py`)
- The script will fail with a generic uv warning about nested projects
- The real issue is Docker isn't running
- Students often get distracted by the uv warning (this was recently fixed in the script)
- **Always ask**: "Is Docker Desktop running?"

**AWS Permissions Issues** (Most common overall)
- Missing IAM policies for specific AWS services
- Region-specific permissions (especially for Bedrock inference profiles)
- Inference profiles require permissions for MULTIPLE regions
- **Check**: IAM policies, AWS region settings, Bedrock model access

**Terraform Variables Not Set**
- Each terraform directory needs its `terraform.tfvars` file configured
- Missing or incorrect variables cause cryptic errors
- **Check**: Does `terraform.tfvars` exist? Are all required variables set?

**AWS Region Mismatches**
- Bedrock models may only be available in specific regions
- Nova Pro requires inference profiles
- Cross-region resource access may need models to have been approved in Bedrock in multiple regions
- **Check**: Region consistency across configuration files

**Model Access Not Granted**
- AWS Bedrock requires explicit model access requests
- Nova Pro is the recommended model (Claude Sonnet has strict rate limits)
- Access is per-region; inference profiles may require multiple regions to have access
- **Check**: Bedrock console → Model access

### 4. **Current Model Strategy**

**Use Nova Pro, not Claude Sonnet**
- Nova Pro (`us.amazon.nova-pro-v1:0` or `eu.amazon.nova-pro-v1:0`) is the recommended model
- Requires inference profiles for cross-region access
- Claude Sonnet has too strict rate limits for this project
- Students need to request access in AWS Bedrock console, and potentially for multiple regions

### 5. **Testing Approach**

Each agent directory has two test files:
- `test_simple.py` - Local testing with mocks (uses `MOCK_LAMBDAS=true`)
- `test_full.py` - AWS deployment testing (actual Lambda invocations)

Students should:
1. Test locally first with `test_simple.py`
2. Deploy with terraform/packaging
3. Test deployment with `test_full.py`

### 6. **Help Students Help Themselves**

Encourage students to:
- Read error messages carefully (especially CloudWatch logs)
- Check AWS Console to verify resources exist
- Use `terraform output` to see deployed resource details
- Test incrementally (don't deploy everything at once)
- Keep AWS costs in mind (remind them to destroy when not actively working)

---

## Terraform Strategy

### Independent Directory Architecture

Each terraform directory (2_sagemaker, 3_ingestion, etc.) is **independent** with:
- Its own local state file (`terraform.tfstate`)
- Its own `terraform.tfvars` configuration
- No dependencies on other terraform directories

**This is intentional** for educational purposes:
- Students can deploy incrementally, guide by guide
- State files are local (simpler than remote S3 state)
- Each part can be destroyed independently
- No complex state bucket setup needed
- Infrastructure can be destroyed step by step

### Critical Requirements

**⚠️ Students MUST configure `terraform.tfvars` in each directory before running terraform apply**

Common pattern is to use the Cursor File Explorer to copy terraform.tfvars.example to terraform.tfvars and then change the variables in each directory.

If `terraform.tfvars` is missing or misconfigured:
- Terraform will use default values (often wrong)
- Resources may fail to create with cryptic errors
- Cross-service connections will break

### Terraform State Management

- State files are `.gitignored` automatically
- Local state means no S3 bucket needed
- Students can `terraform destroy` each directory independently
- If a student loses state, they may need to import existing resources or recreate

### Key Terraform Variables (Guide 6 - Agents)

The `terraform/6_agents/variables.tf` requires these inputs:
- `aws_region` - Deployment region
- `aurora_cluster_arn` - From Guide 5 terraform output
- `aurora_secret_arn` - From Guide 5 terraform output
- `vector_bucket` - S3 Vectors bucket name from Guide 3
- `bedrock_model_id` - e.g. `us.amazon.nova-pro-v1:0`
- `bedrock_region` - Region for Bedrock calls
- `sagemaker_endpoint` - Default: `alex-embedding-endpoint`
- `polygon_api_key` - Polygon.io API key for market data
- `polygon_plan` - `free` or `paid`
- `langfuse_public_key` / `langfuse_secret_key` / `langfuse_host` - Optional observability
- `openai_api_key` - Required for OpenAI Agents SDK tracing (even when using Bedrock)

---

## Agent Strategy - Background on OpenAI Agents SDK

Each Agent subdirectory has a common structure with idiomatic patterns.

1. `lambda_handler.py` for the lambda function and running the agent
2. `agent.py` for the Agent creation and code
3. `templates.py` for prompts

Alex uses OpenAI Agents SDK. Be sure to always use the latest, idiomatic APIs for OpenAI Agents SDK, recognizing that it is a new framework. While this is already installed in all uv projects, do note that the correct package name is `openai-agents` not `agents`. So if ever creating a new project, you would do `uv add openai-agents` followed by this import statement in the code `from agents import Agent, Runner, trace`.

Alex makes standard use of LiteLLM to connect to Bedrock:

`model = LitellmModel(model=f"bedrock/{model_id}")`

Structured outputs and Tool calling is frequently used, but due to a current limitation with LiteLLM and Bedrock, the same Agent cannot use both Structured Outputs and Tool calling. So each Agent implementation either uses Structured Outputs OR uses Tools, never both.

### Agent Patterns by Type

**Pattern 1 - Tools with Context (Reporter, Planner)**

Used when the agent needs database access via tools and needs to know the current user:

```python
with trace("Reporter Agent"):
    agent = Agent[ReporterContext](  # Specify the context type
        name="Report Writer", instructions=REPORTER_INSTRUCTIONS, model=model, tools=tools
    )

    result = await Runner.run(
        agent,
        input=task,
        context=context,  # Pass the context
        max_turns=10,
    )

    response = result.final_output
```

And in tools:
```python
@function_tool
async def get_market_insights(
    wrapper: RunContextWrapper[ReporterContext], symbols: List[str]
) -> str:
    ...
```

**Pattern 2 - Structured Output (Tagger)**

Used when the agent must return a strongly-typed response (no tools):

```python
result = await Runner.run(
    agent,
    input=task,
    max_turns=10,
)
response = result.final_output  # Returns the structured Pydantic model
```

**Pattern 3 - Tools without Context (Retirement)**

Used when the agent uses tools but doesn't need per-user context passed through:

```python
with trace("Retirement Agent"):
    agent = Agent(
        name="Retirement Specialist",
        instructions=RETIREMENT_INSTRUCTIONS,
        model=model,
        tools=tools
    )

    result = await Runner.run(
        agent,
        input=task,
        max_turns=20
    )

    response = result.final_output
```

**Pattern 4 - Direct JSON Output (Charter)**

Used when the agent outputs structured data but LiteLLM/Bedrock structured output is unreliable:

```python
# No tools, no context - agent outputs JSON string directly
model, task = create_agent(job_id, portfolio_data, db)

agent = Agent(
    name="Chart Maker",
    instructions=CHARTER_INSTRUCTIONS,
    model=model,
)

result = await Runner.run(agent, input=task, max_turns=10)
# Parse the JSON from result.final_output in lambda_handler
```

### Rate Limiting with Tenacity

The Planner uses tenacity for automatic retry on rate limit errors:

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from litellm.exceptions import RateLimitError

@retry(
    retry=retry_if_exception_type(RateLimitError),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    before_sleep=lambda retry_state: logger.info(f"Rate limit hit, retrying...")
)
async def run_orchestrator(job_id: str) -> None:
    ...
```

### IMPORTANT: LiteLLM Region Configuration

When using Bedrock through LiteLLM, LiteLLM needs this environment variable set:
```python
os.environ["AWS_REGION_NAME"] = bedrock_region
```
This is confusing as other services sometimes expect `"AWS_REGION"` or `"DEFAULT_AWS_REGION"`. But LiteLLM needs `AWS_REGION_NAME` as documented here: https://docs.litellm.ai/docs/providers/bedrock.

This is set in `create_agent()` in each agent's `agent.py`:
```python
bedrock_region = os.getenv("BEDROCK_REGION", "us-west-2")
os.environ["AWS_REGION_NAME"] = bedrock_region
```

---

## Agent Reference Guide

### Planner (Orchestrator)
- **Trigger**: SQS message with `job_id`
- **Pattern**: Tools + PlannerContext
- **Tools**: `invoke_reporter`, `invoke_charter`, `invoke_retirement`
- **Pre-processing**: Calls Tagger directly (not via agent tool), updates market prices via Polygon.io
- **Key files**: `lambda_handler.py`, `agent.py`, `market.py`, `observability.py`
- **Retry**: Uses tenacity for RateLimitError (5 attempts, exponential backoff)
- **Observability**: LangFuse via `observe()` context manager (requires `LANGFUSE_SECRET_KEY`)

### Tagger (Instrument Classifier)
- **Trigger**: Direct Lambda invocation from Planner with `{"instruments": [...]}`
- **Pattern**: Structured outputs (no tools)
- **Purpose**: Tags ETF/stock instruments with allocation data (regions, sectors, asset classes)
- **Key files**: `lambda_handler.py`, `agent.py`, `templates.py`

### Reporter (Portfolio Analyst)
- **Trigger**: Lambda invocation from Planner with `{"job_id": "..."}`
- **Pattern**: Tools + ReporterContext
- **Tools**: `get_market_insights` (queries S3 Vectors via SageMaker embeddings)
- **Output**: Markdown report saved to `jobs.report_payload`
- **Key files**: `lambda_handler.py`, `agent.py`, `judge.py` (LLM quality evaluation)

### Charter (Visualization)
- **Trigger**: Lambda invocation from Planner with `{"job_id": "..."}`
- **Pattern**: Direct JSON output (no tools, no context)
- **Output**: Chart data JSON saved to `jobs.charts_payload`
- **Key files**: `lambda_handler.py`, `agent.py` (includes `analyze_portfolio()` preprocessing)

### Retirement (Projection Specialist)
- **Trigger**: Lambda invocation from Planner with `{"job_id": "..."}`
- **Pattern**: Tools (no context needed)
- **Output**: Retirement projections saved to `jobs.retirement_payload`
- **Key files**: `lambda_handler.py`, `agent.py`, `templates.py`

### Researcher (Market Research)
- **Deployment**: App Runner (NOT Lambda) - long-running service
- **Pattern**: FastAPI + OpenAI Agents SDK + Playwright MCP server
- **Purpose**: Browses financial websites, ingests research into S3 Vectors
- **Key files**: `server.py` (REGION and MODEL hardcoded - students must update), `mcp_servers.py`, `tools.py`
- **Endpoints**: `GET /`, `POST /research`, `GET /research/auto`, `GET /health`, `GET /test-bedrock`
- **Deployment**: `deploy.py` builds Docker image and pushes to ECR

---

## Database Architecture

### Aurora Serverless v2 via Data API

Alex uses Aurora PostgreSQL Serverless v2 with the RDS Data API enabled. This avoids VPC complexity - the Data API is accessed directly over HTTPS.

### Database Models (`backend/database/src/`)

**`client.py`** - `DataAPIClient` wrapping AWS RDS Data API
- Methods: `execute()`, `query()`, `query_one()`, `insert()`, `update()`, `delete()`

**`models.py`** - ORM-like model classes:
- `Users` - `find_by_clerk_id()`, `create_user()`
- `Instruments` - `find_by_symbol()`, `search()`, `find_by_type()`, all instruments ordered by symbol
- `Accounts` - `find_by_user()`, `create_account()`
- `Positions` - `find_by_account()` (JOIN with instruments), `add_position()` (UPSERT), `get_portfolio_value()`
- `Jobs` - `create_job()`, `update_status()`, `update_report()`, `update_charts()`, `update_retirement()`, `update_summary()`, `find_by_user()`
- `Database` - Main interface instantiating all models: `db.users`, `db.instruments`, `db.accounts`, `db.positions`, `db.jobs`

**`schemas.py`** - Pydantic validation schemas:
- `InstrumentCreate`, `UserCreate`, `AccountCreate`, `PositionCreate`, `JobCreate`, `JobUpdate`
- `JobType`, `JobStatus` enums

### Jobs Table Structure

The `jobs` table is the central result store:
- `report_payload` - Reporter agent output (markdown narrative)
- `charts_payload` - Charter agent output (visualization JSON)
- `retirement_payload` - Retirement agent output (projections)
- `summary_payload` - Planner's final summary
- `status` - `pending` → `running` → `completed` / `failed`

### Connecting to Database

```python
from src import Database

db = Database()  # Reads env vars: AURORA_CLUSTER_ARN, AURORA_SECRET_ARN, DATABASE_NAME, DEFAULT_AWS_REGION
```

---

## FastAPI Backend (API)

Location: `backend/api/main.py`

The API uses `mangum` as an ASGI adapter for Lambda deployment and `fastapi-clerk-auth` for JWT validation.

### Authentication

All routes (except `/health`) require Clerk JWT via `ClerkHTTPBearer`:
```python
clerk_config = ClerkConfig(jwks_url=os.getenv("CLERK_JWKS_URL"))
clerk_guard = ClerkHTTPBearer(clerk_config)
```

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check (unauthenticated) |
| GET | `/api/user` | Get or create user (auto-creates on first login) |
| PUT | `/api/user` | Update user settings (retirement goals, targets) |
| GET | `/api/accounts` | List user's accounts |
| POST | `/api/accounts` | Create new account |
| PUT | `/api/accounts/{id}` | Update account |
| DELETE | `/api/accounts/{id}` | Delete account (cascades positions) |
| GET | `/api/accounts/{id}/positions` | List positions with instrument data |
| POST | `/api/positions` | Add position (auto-creates instrument if unknown) |
| PUT | `/api/positions/{id}` | Update position quantity |
| DELETE | `/api/positions/{id}` | Delete position |
| GET | `/api/instruments` | All instruments (for autocomplete) |
| POST | `/api/analyze` | Trigger portfolio analysis (creates Job, sends to SQS) |
| GET | `/api/jobs/{id}` | Get job status and results |
| GET | `/api/jobs` | List user's jobs |
| DELETE | `/api/reset-accounts` | Delete all accounts for user |
| POST | `/api/populate-test-data` | Create test portfolio with sample data |

### Key Behaviors
- `POST /api/positions`: If instrument symbol is unknown, auto-creates it with default allocations (will be properly tagged by Tagger agent later)
- `POST /api/analyze`: Creates a job record and sends to SQS queue; Planner Lambda is triggered
- User creation: First call to `GET /api/user` creates the user with defaults (20yr retirement, $60k income target)
- CORS: `cors_origins` from env var `CORS_ORIGINS` (comma-separated), defaults to `http://localhost:3000`

---

## Frontend Architecture (NextJS)

Location: `frontend/`

**Framework**: NextJS with Pages Router (required for Clerk authentication)
**Authentication**: Clerk
**Deployment**: Static site on S3 + CloudFront CDN

### Pages

| Page | Route | Description |
|------|-------|-------------|
| Landing | `/` | Marketing/intro page |
| Dashboard | `/dashboard` | Jobs list, trigger analysis |
| Analysis | `/analysis` | View analysis results (report, charts, retirement) |
| Accounts | `/accounts` | Account management |
| Account Detail | `/accounts/[id]` | Positions for a specific account |
| Advisor Team | `/advisor-team` | Info about the AI agent team |

### Configuration
- `frontend/.env.local` - Clerk public key and API URL
- API calls go through CloudFront → API Gateway → Lambda (api)

---

## Observability (LangFuse + Logfire)

Location: `backend/planner/observability.py` (also in other agent directories)

Each agent has an `observability.py` with an `observe()` context manager:

```python
from observability import observe

with observe():
    # Agent runs here - traces sent to LangFuse if configured
    result = await Runner.run(agent, input=task, ...)
```

**How it works**:
1. Checks for `LANGFUSE_SECRET_KEY` env var - skips silently if not set
2. Configures `logfire` to instrument OpenAI Agents SDK (without sending to Logfire cloud)
3. `logfire.instrument_openai_agents()` captures all agent traces
4. LangFuse receives traces via OTLP exporter
5. On exit, flushes and waits 15 seconds (Lambda termination workaround)

**Required env vars** (optional - observability is disabled if missing):
- `LANGFUSE_SECRET_KEY`
- `LANGFUSE_PUBLIC_KEY`
- `LANGFUSE_HOST` (default: `https://us.cloud.langfuse.com`)
- `OPENAI_API_KEY` - Required for OpenAI Agents SDK tracing even when using Bedrock

---

## Market Data (Polygon.io)

Location: `backend/planner/market.py`

The Planner calls `update_instrument_prices()` before running agents to fetch fresh prices from Polygon.io.

**Required env vars**:
- `POLYGON_API_KEY` - API key from polygon.io
- `POLYGON_PLAN` - `free` (rate limited) or `paid`

---

## Researcher Service Details

Location: `backend/researcher/`

The Researcher is deployed on **App Runner** (not Lambda) because it:
- Uses Playwright browser automation (needs persistent process)
- Has longer execution times (web browsing takes time)
- Uses MCP (Model Context Protocol) with Playwright

### Key Configuration in `server.py`

```python
# Students MUST update these:
REGION = "us-east-1"                          # Your AWS region
MODEL = "bedrock/us.amazon.nova-pro-v1:0"     # Nova Pro (must support tools/MCP)
```

**Note**: Nova Pro is required (not Nova Lite) because MCP tools need a capable model.

### MCP Integration (`mcp_servers.py`)

Uses `agents.mcp.MCPServerStdio` to connect to Playwright MCP server for web browsing:
```python
async with create_playwright_mcp_server(timeout_seconds=60) as playwright_mcp:
    agent = Agent(
        name="Alex Investment Researcher",
        ...
        mcp_servers=[playwright_mcp],
    )
```

### Deployment (`deploy.py`)

1. Builds Docker image for linux/amd64 (App Runner requirement)
2. Pushes to ECR
3. App Runner pulls and deploys automatically

---

## Local Development

### Running Locally

```bash
# From project root
uv run scripts/run_local.py
```

This starts:
- FastAPI backend at `http://localhost:8000` (via `uv run main.py` in `backend/api/`)
- NextJS frontend at `http://localhost:3000`
- API docs at `http://localhost:8000/docs`

**Prerequisites**:
- `.env` file in project root with all backend variables
- `frontend/.env.local` with Clerk keys

### Testing Agents Locally

```bash
# From the agent directory (e.g., backend/planner/)
MOCK_LAMBDAS=true uv run test_simple.py
```

With `MOCK_LAMBDAS=true`, Lambda invocations are mocked and return success without calling AWS.

### Packaging Agents for Lambda

Each agent directory has `package_docker.py`:
```bash
# From backend/planner/
uv run package_docker.py
```

Or package all agents at once:
```bash
# From backend/
uv run package_docker.py
```

**Requirements**: Docker Desktop must be running. Packages are built for `linux/amd64`.

---

## Common Issues and Troubleshooting

The most common issues relate to AWS region choices! Check environment variables, terraform settings (everything should propagate from tfvars).

### Issue 1: `package_docker.py` Fails

**Symptoms**: Script fails with uv warning about nested projects and perhaps an error message

**Root Cause (common)**: Docker Desktop is not running or a Docker mounts denied issue

**Diagnosis**:
1. Ask: "Is Docker Desktop running?"
2. Check: Can they run `docker ps` successfully?
3. Recent fix: The script now gives better error messages, but older versions were misleading

**Solution**: Start Docker Desktop, wait for it to fully initialize, then retry

**If the issue is a Mounts Denied error**: It fails to mount the /tmp directory into Docker as it doesn't have access to it. Going to Docker Desktop app, and adding the directory mentioned in the error to the shared paths (Settings -> Resources -> File Sharing) solved the problem for a student.

**Not the solution**: Changing uv project configurations (this is a red herring)

### Issue 2: Region issues and Bedrock Model Access Denied

**Symptoms**: "Access denied" or "Model not found" errors when running agents

**Root Cause**: Model access not granted in Bedrock, or wrong region

**Diagnosis**:
1. Which model are they trying to use?
2. Which region is their code running in?
3. Have they requested model access in Bedrock console?
4. For inference profiles: Do they have permissions for multiple regions?
5. Are the right environment variables being set? LiteLLM needs `AWS_REGION_NAME`. Check that nothing is being hardcoded in the code, and that tfvars are set right. Add logging to confirm which region is being used.

**Solution**:
1. Go to Bedrock console in the correct region
2. Click "Model access"
3. Request access to Nova Pro
4. For cross-region: Set up inference profiles with multi-region permissions

### Issue 3: Terraform Apply Fails

**Symptoms**: Resources fail to create, dependency errors, ARN not found

**Root Cause**: `terraform.tfvars` not configured, or values from previous guides not set

**Diagnosis**:
1. Does `terraform.tfvars` exist in this directory?
2. Are all required variables set (check `terraform.tfvars.example`)?
3. For later guides: Do they have output values from earlier guides?
4. Run `terraform output` in previous directories to get required ARNs

**Solution**:
1. Copy `terraform.tfvars.example` to `terraform.tfvars`
2. Fill in all required values
3. Get ARNs from previous terraform outputs: `cd terraform/X_previous && terraform output`
4. Update `.env` file with values for Python scripts

### Issue 4: Lambda Function Failures

**Symptoms**: 500 errors, timeout errors, "Module not found" errors

**Root Cause**: Package not built correctly, environment variables missing, or IAM permissions

**Diagnosis**:
1. Check CloudWatch logs: `aws logs tail /aws/lambda/alex-{agent-name} --follow`
2. Check Lambda environment variables in AWS Console
3. Check IAM role has required permissions
4. Was the Lambda package built with Docker for linux/amd64?

**Solution**:
1. For packaging: Re-run `package_docker.py` with Docker running
2. For env vars: Verify in Lambda console or `terraform.tfvars`
3. For permissions: Check IAM role policy in terraform

### Issue 5: Aurora Database Connection Fails

**Symptoms**: "Cluster not found", "Secret not found", Data API errors

**Root Cause**: Database not fully initialized, wrong ARNs, or Data API not enabled

**Diagnosis**:
1. Check cluster status: `aws rds describe-db-clusters`
2. Verify Data API is enabled (should show `EnableHttpEndpoint: true`)
3. Check ARNs in environment variables match actual resources
4. Database may still be initializing (takes 10-15 minutes)

**Solution**:
1. Wait for cluster to reach "available" status
2. Verify Data API is enabled in RDS console
3. Run `terraform output` in `5_database` to get correct ARNs
4. Update environment variables with actual ARNs

### Issue 6: Researcher Hardcoded Region/Model

**Symptoms**: Researcher uses wrong region or model, even though tfvars are correct

**Root Cause**: `backend/researcher/server.py` has hardcoded `REGION` and `MODEL` variables

**Solution**: Edit `server.py` directly:
```python
REGION = "your-region-here"        # e.g., "eu-central-1"
MODEL = "bedrock/eu.amazon.nova-pro-v1:0"  # Match your region
```
Then redeploy via `deploy.py`.

### Issue 7: Planner Runs But Sub-agents Not Called

**Symptoms**: Job completes but no report/charts/retirement data saved

**Root Cause**: Agent may have decided not to call tools, or Lambda invocations failed silently

**Diagnosis**:
1. Check CloudWatch logs for each Lambda (`alex-reporter`, `alex-charter`, `alex-retirement`)
2. Check the planner logs for tool call attempts
3. Verify Lambda function names match env vars (`REPORTER_FUNCTION`, `CHARTER_FUNCTION`, `RETIREMENT_FUNCTION`)

---

## Technical Architecture Quick Reference

### Core Services by Guide

**Guides 1-2**: Foundations
- IAM permissions
- SageMaker Serverless endpoint (embeddings)

**Guide 3**: Vector Storage
- S3 Vectors bucket and index
- Lambda ingest function
- API Gateway with API key

**Guide 4**: Research Agent
- App Runner service (Researcher)
- ECR repository
- EventBridge scheduler (optional)

**Guide 5**: Database
- Aurora Serverless v2 PostgreSQL
- Data API enabled
- Secrets Manager for credentials
- Database schema and seed data - **IMPORTANT** be sure to read the database schema

**Guide 6**: Agent Orchestra (The Big One)
- 5 Lambda functions: Planner, Tagger, Reporter, Charter, Retirement
- Each lambda function is implemented using OpenAI Agents SDK with simple, idiomatic code. Review an existing implementation for details.
- SQS queue for orchestration
- S3 bucket for Lambda packages (>50MB)
- Cross-service IAM permissions

**Guide 7**: Frontend
- NextJS static site on S3
- CloudFront CDN
- API Gateway + Lambda backend
- Clerk authentication

**Guide 8**: Enterprise
- CloudWatch dashboards
- Alarms and monitoring
- LangFuse observability
- Enhanced logging

### Agent Collaboration Pattern

```
User Request → API → SQS Queue → Planner (Orchestrator Lambda)
                                    │
                                    ├─→ Tagger (sync, pre-processing)
                                    │   └─→ Tags unclassified instruments
                                    │
                                    ├─→ Reporter (async tool call)
                                    │   ├─→ get_market_insights (S3 Vectors)
                                    │   └─→ Saves report to jobs table
                                    │
                                    ├─→ Charter (async tool call)
                                    │   └─→ Saves chart data to jobs table
                                    │
                                    └─→ Retirement (async tool call)
                                        └─→ Saves projections to jobs table
```

### Environment Variables Reference

**All agents** (set via terraform `6_agents/terraform.tfvars`):
- `BEDROCK_MODEL_ID` - e.g. `us.amazon.nova-pro-v1:0`
- `BEDROCK_REGION` - e.g. `us-east-1`
- `AURORA_CLUSTER_ARN` - From Guide 5
- `AURORA_SECRET_ARN` - From Guide 5
- `DATABASE_NAME` - e.g. `alex`
- `DEFAULT_AWS_REGION` - Primary AWS region

**Planner additional**:
- `TAGGER_FUNCTION` - Lambda name (default: `alex-tagger`)
- `REPORTER_FUNCTION` - Lambda name (default: `alex-reporter`)
- `CHARTER_FUNCTION` - Lambda name (default: `alex-charter`)
- `RETIREMENT_FUNCTION` - Lambda name (default: `alex-retirement`)
- `POLYGON_API_KEY` - Polygon.io market data
- `POLYGON_PLAN` - `free` or `paid`
- `LANGFUSE_SECRET_KEY` / `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_HOST` - Optional
- `OPENAI_API_KEY` - Required for agent tracing

**Reporter additional**:
- `SAGEMAKER_ENDPOINT` - For S3 Vectors search
- `DEFAULT_AWS_REGION` - SageMaker region

**API backend**:
- `SQS_QUEUE_URL` - SQS queue for analysis jobs
- `CLERK_JWKS_URL` - Clerk JWT validation
- `CORS_ORIGINS` - Comma-separated allowed origins

### Cost Management

**Cost optimization**:
- Destroy Aurora when not actively working (biggest savings)
- Use `terraform destroy` in each directory
- Monitor costs in AWS Cost Explorer

### Cleanup Process

```bash
# Destroy in reverse order (optional, but cleaner)
cd terraform/8_enterprise && terraform destroy
cd terraform/7_frontend && terraform destroy
cd terraform/6_agents && terraform destroy
cd terraform/5_database && terraform destroy  # Biggest cost savings
cd terraform/4_researcher && terraform destroy
cd terraform/3_ingestion && terraform destroy
cd terraform/2_sagemaker && terraform destroy
```

---

## Key Files Students Modify

### Configuration Files
- `.env` - Root environment variables (add values as guides progress)
- `frontend/.env.local` - Frontend Clerk configuration
- `terraform/*/terraform.tfvars` - Each terraform directory (copy from .example)

### Code Students May Need to Update
- `backend/researcher/server.py` - **MUST** update `REGION` and `MODEL` variables (hardcoded, not from env)
- Agent templates in `backend/*/templates.py` - For customization
- Frontend pages for UI modifications

---

## Getting Help

### For Students

If you're stuck:

1. **Check the guide carefully** - Most steps have troubleshooting sections
2. **Review error messages** - Look at CloudWatch logs, not just terminal output
3. **Verify prerequisites** - Is Docker running? Are permissions set? Is terraform.tfvars configured?
4. **Contact the instructor**:
   - **Post a question in Udemy** - Include your guide number, error message, and what you've tried
   - **Email Ed Donner**: ed@edwarddonner.com

When asking for help, include:
- Which guide/day you're on
- Exact error message (copy/paste, don't paraphrase)
- What command you ran
- Relevant CloudWatch logs if available
- What you've already tried

### For Claude Code (AI Assistant)

When helping students:

0. **Prepare** - Read all the guides to be fully briefed.
1. **Establish context** - Which guide? What's the goal?
2. **Get error details** - Actual messages, logs, console output
3. **Diagnose first** - Don't write code before understanding the problem
4. **Think incrementally** - One change at a time
5. **Verify understanding** - Explain what you think is wrong before fixing
6. **Keep it simple** - Avoid over-engineering solutions

**Remember**: Students are learning. The goal is to help them understand what went wrong and how to fix it, not just to make the error go away.

---

### Course Context
- Instructor: Ed Donner
- Platform: Udemy
- Course: AI in Production
- Project: "Alex" - Capstone for Weeks 3-4

---

*This guide was created to help AI assistants (like Claude Code) effectively support students through the Alex project. Last updated: March 2026*
